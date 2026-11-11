#!/usr/bin/env python3
"""Qualify libknc_vmath (S10-02, S10-07, ADR-0014 point 4) on the card, or the host build on the host.

    python tests/vmath/card_qualify.py --host              host build: negative and compare sets
    python tests/vmath/card_qualify.py [--set S] [--dry-run]   card (lead only), through tools/card_run
    ... --out T          the build in .work/_shared/T (tools/knc_vmath.py --out T)
    ... --only NAME      only the jobs of one function

Build first with tools/knc_vmath.py. Sets: negative (controls that must FAIL), compare (the set the
host also runs; summaries and check lines must match the host's), full (the qualification). Each
job's output is kept in .work/_shared/S10-02/<host|card>/<job>.txt. qualify_d's "check" lanes are
recomputed exactly here (Python decimal, 60 digits): that is the high-precision reference, and the
max_ulp reported for exp, log and pow is the exact maximum over those lanes. The other lanes'
screened error is at most the dump threshold, so their true error is at most that plus the largest
screen error seen on the rechecked lanes outside the special grid (printed as undumped_bound,
which must stay within the limit too). The grid is checked exactly in full (S10-06).

The v1a functions (S10-07) run tests/vmath/qualify_v1.c. On the host its oracle is MPFR, so the
host's max_ulp is exact over every lane. On the card it screens with the long double libm, and the
host program rechecks the card's "check" lines exactly (--recheck): every lane screened above the
job's --dump, the special grid, and a sample of one block in 1024 that measures the screen's own
error for undumped_bound. The card and the host therefore do not print the same lines, and these
jobs are not compared with the host's. --host --screen runs the card's flow on the host; Cygwin's
long double sin, cos and tan are wrong for large arguments, so those jobs fail there as they must.
"""
import argparse
from decimal import Context, Decimal, localcontext
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
OUT = SHARED / 'S10-02'
CYGWIN = PROJECT / '.work/_shared/toolchain/cygwin/bin'

# Expected limits from the PhiWeather receipts (contrib/knc-vecmath/receipts, ADR-0011 point 4):
# targets, not evidence. The pass limit is 1 ULP for every function (ADR-0014 point 4).
RECEIPTS = {
    'expf': (0.5016, 'knc-g5-expf.json finiteNonidenticalMaximumIntervalBoundUlpsApprox'),
    'logf': (0.7754, 'knc-g5-logf.json maximumConservativeTrueErrorUlps'),
    'powf': (0.5051, 'knc-g5-powf.json maximumInheritedTrueErrorUlps'),
    'exp': (0.5054, 'knc-g5-exp-i64.json maximumConservativeTrueErrorUlps'),
    'log': (0.5102, 'knc-g5-log-i64.json maximumConservativeTrueErrorUlps'),
    'pow': (0.5068, 'knc-g5-pow-i64.json maximumCertifiedTrueErrorUlps'),
    'sinf': (0.5000, 'knc-g5-sinf.json maximumInheritedTrueErrorUlps'),
    'cosf': (0.5000, 'knc-g5-cosf.json maximumInheritedTrueErrorUlps'),
    'tanf': (0.5000, 'knc-g5-tan2-v5.json worstErrorUlps'),
    'log10f': (0.8189, 'knc-g5-narrow14-v2.json worstErrorUlps'),
    'atanf': (0.5000, 'knc-g5-atan3-finite-div-v7.json worstErrorUlps'),
    'atan2f': (0.5000, 'knc-g5-atan3-finite-div-v7.json worstErrorUlps'),
    'sinhf': (0.5000, 'knc-g5-hyperbolic6-v6.json worstErrorUlps'),
    'coshf': (0.5000, 'knc-g5-hyperbolic6-v6.json worstErrorUlps'),
    'tanhf': (0.5000, 'knc-g5-hyperbolic6-v6.json worstErrorUlps'),
    'sin': (0.7712, 'knc-g5-sin-i64.json maximumCertifiedTrueErrorUlps'),
    'cos': (0.7589, 'knc-g5-cos-i64.json maximumCertifiedTrueErrorUlps'),
    'tan': (0.7574, 'knc-g5-tan2-v5.json worstErrorUlps'),
    'log10': (0.5308, 'knc-g5-log10-i64.json maximumCertifiedTrueErrorUlps'),
    'atan2': (0.9181, 'knc-g5-atan3-finite-div-v7.json worstErrorUlps'),
    'sinh': (0.5310, 'knc-g5-hyperbolic6-v6.json worstErrorUlps'),
    'cosh': (0.5332, 'knc-g5-hyperbolic6-v6.json worstErrorUlps'),
    'tanh': (0.5000, 'knc-g5-hyperbolic6-v6.json worstErrorUlps'),
}
LIMIT = 1.0

# (job, program, arguments, expected result). powf is not in the compare set: the accepted harness
# draws its pairs per worker thread, so its inputs depend on the thread count.
JOBS = {
    'negative': [
        ('neg-expf', 'qualify_f', ['expf', '--negative', '--block-stride', '65536'], 'FAIL'),
        ('negmask-logf', 'qualify_f', ['logf', '--negative-mask', '--block-stride', '65536'], 'FAIL'),
        ('neg-exp', 'qualify_d', ['exp', '--negative', '--blocks', '4096'], 'FAIL'),
        ('negmask-pow', 'qualify_d', ['pow', '--negative-mask', '--blocks', '65536'], 'FAIL'),
    ],
    'compare': [
        ('cmp-expf', 'qualify_f', ['expf', '--block-stride', '65536'], 'PASS'),
        ('cmp-logf', 'qualify_f', ['logf', '--block-stride', '65536'], 'PASS'),
        ('cmp-exp', 'qualify_d', ['exp', '--blocks', '65536'], 'PASS'),
        ('cmp-log', 'qualify_d', ['log', '--blocks', '65536'], 'PASS'),
        ('cmp-pow', 'qualify_d', ['pow', '--blocks', '65536', '--dump', '0.45'], 'PASS'),
    ],
    # expf and logf: every 16th block of the 2^32 inputs (2^28 inputs); stride 1 is exhaustive.
    'full': [
        ('expf', 'qualify_f', ['expf', '--block-stride', '16'], 'PASS'),
        ('logf', 'qualify_f', ['logf', '--block-stride', '16'], 'PASS'),
        ('powf', 'qualify_f', ['powf', '--pow-count', str(1 << 28)], 'PASS'),
        ('exp', 'qualify_d', ['exp', '--blocks', str(1 << 24)], 'PASS'),
        ('log', 'qualify_d', ['log', '--blocks', str(1 << 24)], 'PASS'),
        # pow: every lane screened above 0.45 ULP is checked exactly, which keeps undumped_bound
        # (0.45 + the screen's error, 0.534 on the card) under 1 ULP (S10-06); about 3.0M lanes.
        ('pow', 'qualify_d', ['pow', '--blocks', str(1 << 25), '--dump', '0.45', '--max-dump', '4000000'],
         'PASS'),
    ],
}

# The v1a functions (S10-07), each with the screened error above which the card dumps a lane for
# the exact recheck. The floats are computed in double and rounded once, so few lanes pass 0.5.
# Of the doubles' lanes about 2% pass 0.5 for sin, cos and tan and 1% for atan2; 0.7 keeps their
# dump small and leaves 0.3 ULP for the screen's own error.
V1A = [('sinf', '0.5'), ('cosf', '0.5'), ('tanf', '0.5'), ('log10f', '0.7'), ('atanf', '0.5'),
       ('atan2f', '0.5'), ('sinhf', '0.5'), ('coshf', '0.5'), ('tanhf', '0.5'),
       ('sin', '0.7'), ('cos', '0.7'), ('tan', '0.7'), ('log10', '0.5'), ('atan2', '0.7'),
       ('sinh', '0.5'), ('cosh', '0.5'), ('tanh', '0.5')]
JOBS['negative'] += [
    ('neg-sin', 'qualify_v1', ['sin', '--negative', '--blocks', '4096'], 'FAIL'),
    ('negmask-atan2f', 'qualify_v1', ['atan2f', '--negative-mask', '--blocks', '4096'], 'FAIL')]
# One argument: 2^16 or 2^24 sweep blocks and as many dense blocks; atan2: that many pair blocks.
JOBS['compare'] += [('cmp-' + f, 'qualify_v1', [f, '--blocks', '65536', '--dump', dump], 'PASS')
                    for f, dump in V1A]
JOBS['full'] += [(f, 'qualify_v1', [f, '--blocks', str(1 << 24), '--dump', dump, '--max-dump', '4000000'],
                  'PASS') for f, dump in V1A]

CTX = Context(prec=60, Emax=10 ** 8, Emin=-10 ** 8, traps=[])
DBL_OVERFLOW = (2 - Decimal(2) ** -53) * Decimal(2) ** 1023  # smallest value that rounds to inf


def as_double(bits):
    return struct.unpack('<d', struct.pack('<Q', bits))[0]


def exact(function, x, y):
    """Exact value as a Decimal, or None where only IEEE special-case rules apply."""
    with localcontext(CTX):
        if function == 'exp':
            return Decimal(x).exp() if math.isfinite(x) else None
        if function == 'log':
            return Decimal(x).ln() if math.isfinite(x) and x > 0 else None
        if not (math.isfinite(x) and math.isfinite(y)) or x == 0 or y == 0:
            return None
        if x < 0 and not y.is_integer():
            return None
        value = (Decimal(y) * Decimal(abs(x)).ln()).exp()
        return -value if x < 0 and abs(y) < 2 ** 53 and int(y) % 2 else value


def ulp_error(value, out):
    """Error of out against value in ULPs of value; None if only an exact match would do."""
    with localcontext(CTX):
        magnitude = abs(value)
        if magnitude >= DBL_OVERFLOW:
            return 0.0 if math.isinf(out) and (out > 0) == (value > 0) else None
        if not math.isfinite(out):
            return None
        k = max(math.frexp(float(magnitude))[1] - 1 if float(magnitude) else -1074, -1022)
        if Decimal(2) ** k > magnitude and k > -1022:
            k -= 1
        return float(abs(Decimal(out) - value) / Decimal(2) ** (k - 52))


def recheck(function, lines):
    """Exact errors of the dumped lanes: (max, worst line, special, screen error)."""
    worst, worst_line, special, screen = 0.0, '', 0, 0.0
    for line in lines:
        _, xs, ys, outs, screened, *grid = line.split()
        x, y, out = as_double(int(xs, 16)), as_double(int(ys, 16)), as_double(int(outs, 16))
        value = exact(function, x, y)
        error = None if value is None else ulp_error(value, out)
        if error is None:
            special += float(screened) < 0  # the screen's exact-match verdict on a special-case lane stands
            continue
        # Grid lanes are all checked exactly, so they do not estimate the screen's error.
        if float(screened) >= 0 and not grid:
            screen = max(screen, abs(float(screened) - error))
        if error > worst:
            worst, worst_line = error, line
    return worst, worst_line, special, screen


def summary(text):
    lines = [l for l in text.splitlines() if l.startswith('qualify')]
    return dict(re.findall(r'(\S+)=(\S+)', lines[-1])) if lines else {}


def assess(job, program, args, expect, text):
    fields = summary(text)
    if not fields:
        return 'INFRA', 'no summary line', fields
    function = args[0]
    checks = [l for l in text.splitlines() if l.startswith('check ')]
    detail = '%s max_ulp=%s result=%s' % (fields.get('mode', 'screen'), fields.get('max_ulp'),
                                         fields.get('result'))
    result = fields['result']
    if program == 'qualify_v1' and fields['mode'] == 'screen':
        exact = summary(run_host('qualify_v1', [function, '--recheck'], '\n'.join(checks) + '\n'))
        if not exact:
            return 'INFRA', 'no recheck summary', fields
        others_ok = fields['mask_errors'] == '0' and \
            int(fields['dumped']) == len(checks) == int(exact['checked'])
        bound = float(fields['dump']) + float(exact['screen_error'])
        result = 'PASS' if exact['result'] == 'PASS' and bound <= LIMIT and others_ok else 'FAIL'
        fields['max_ulp'] = exact['max_ulp']
        detail = ('exact max_ulp=%s over %d checked lanes, special=%s, screen error<=%s, '
                  'undumped_bound=%.4f, worst: x=%s y=%s out=%s'
                  % (exact['max_ulp'], len(checks), exact['special_errors'], exact['screen_error'],
                     bound, exact['worst_x'], exact['worst_y'], exact['worst_out']))
    if program == 'qualify_d':
        worst, line, special, screen = recheck(function, checks)
        others_ok = all(fields[k] == '0' for k in ('status_errors', 'mask_errors')) and \
            int(fields['dumped']) == len(checks)
        bound = float(fields['dump']) + screen
        result = 'PASS' if worst <= LIMIT and bound <= LIMIT and not special and others_ok else 'FAIL'
        fields['max_ulp'] = '%.6f' % max(worst, 0)
        detail = ('exact max_ulp=%.6f over %d checked lanes, special=%d, screen error<=%.4f, '
                  'undumped_bound=%.4f, worst: %s' % (worst, len(checks), special, screen,
                                                      bound, line))
    return result, detail, fields


def run_host(program, args, stdin=None):
    env = dict(os.environ, PATH=str(CYGWIN) + os.pathsep + os.environ.get('PATH', ''))
    return subprocess.run([str(OUT / 'host' / (program + '.exe'))] + args, input=stdin,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                          universal_newlines=True).stdout


def run_job(target, job, program, args, timeout):
    if target == 'host':
        text = run_host(program, args)
    else:
        cmd = [sys.executable, str(ROOT / 'tools/card_run'), '--timeout', str(timeout),
               str(OUT / target / (program + '.mic'))] + args
        text = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              universal_newlines=True).stdout
    (OUT / target / (job + '.txt')).write_text(text)
    return text


def compare_with_host(job, text):
    host = OUT / 'host' / (job + '.txt')
    if not host.exists():
        return 'no host output'
    drop = lambda s: {k: v for k, v in summary(s).items() if k != 'workers'}
    checks = lambda s: sorted(l for l in s.splitlines() if l.startswith('check '))
    host_text = host.read_text()
    same = drop(host_text) == drop(text) and checks(host_text) == checks(text)
    return 'same as host' if same else 'DIFFERS from host'


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--host', action='store_true', help='run the host build (negative and compare sets)')
    parser.add_argument('--set', choices=['negative', 'compare', 'full', 'all'], default='all')
    parser.add_argument('--timeout', type=int, default=14400, help='card_run timeout per job, seconds')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--out', default=OUT.name, help='build folder under .work/_shared')
    parser.add_argument('--only', help='only the jobs of this function')
    parser.add_argument('--screen', action='store_true',
                        help='with --host: run qualify_v1 as the card does, screen then recheck')
    args = parser.parse_args()
    OUT = SHARED / args.out
    target = 'host' if args.host else 'card'
    sets = ['negative', 'compare'] if args.host else (['negative', 'compare', 'full'] if args.set == 'all' else [args.set])
    (OUT / target).mkdir(parents=True, exist_ok=True)
    failures, table = 0, []
    for name in sets:
        for job, program, jargs, expect in JOBS[name]:
            if args.only and jargs[0] != args.only:
                continue
            if args.screen and target == 'host' and program == 'qualify_v1':
                jargs = jargs + ['--screen']
            if args.dry_run:
                print('%s: %s %s' % (job, program, ' '.join(jargs)))
                continue
            text = run_job(target, job, program, jargs, args.timeout)
            result, detail, fields = assess(job, program, jargs, expect, text)
            note = compare_with_host(job, text) if target == 'card' and name == 'compare' \
                and program != 'qualify_v1' else ''
            ok = result == expect and 'DIFFERS' not in note
            failures += not ok
            print('%-13s %s (expected %s) %s %s' % (job, result, expect, detail, note), flush=True)
            if name == 'full' or (target == 'host' and name == 'compare'):
                table.append((jargs[0], fields.get('max_ulp', '?'), fields.get('inputs', '?'), result))
    if table:
        print('\nfunction  max_ulp   inputs       result  receipt  (limit %.1f ULP)' % LIMIT)
        for function, ulp, inputs, result in table:
            print('%-9s %-9s %-12s %-7s %.4f  %s' % ((function, ulp, inputs, result) + RECEIPTS[function]))
    if not args.dry_run:
        print('ALL AS EXPECTED' if not failures else '%d job(s) NOT as expected' % failures)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
