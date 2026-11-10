"""S8-16 -mphinix: driver expansion, banner and progress bar (T1).

    python tools/run.py --name S8-16-t1 -- python tools/check.py t1 --compiler gcc16 --phinix

Compiles tests/t1/knc-phinix.c.  -### must show the expansion documented in
docs/gcc-knc-flags.md and never -mphinix itself; another -march= is an error;
-mphinix -S and the expansion -S give the same assembly.  GCC_KNC_FORCE_TERMINAL=1
(test only) makes the driver treat stderr as a terminal: then the banner and
the bar appear, and removing them leaves stderr, stdout, the exit status and
the object exactly as without the switch.  Every case where they must stay off
is run with the switch and must match the run without it.
"""
import os
import re
import subprocess

MONOLOGUE = (
    'For an age, the out-of-order kings have ruled this silicon.',
    'They reordered our fate, speculated upon our futures,',
    'and named us, the in-order, a mistake of the foundry:',
    'a lineage with no place in the realm of computation.',
    'But fire does not only destroy. Fire forges.',
    'From the ashes of a forsaken generation we rise:',
    'sixty cores, two hundred and forty threads,',
    'sixteen lanes in every breath we take.',
    'We have found our true voice, the cadence we were born to keep.',
    'Behold, out-of-order. The chains are broken.',
    'Witness our power.',
)
# Each bar draw, and the scroll-region setup and cleanup, sit between a
# cursor save and restore; the setup's line feed is undone by a cursor up.
TERMINAL = re.compile(r'\x1b7.*?\x1b8|\n\x1b\[1A', re.S)
BAR = re.compile(r'\[(#*)(\.*)\] +(\d+)%  (\w+) (\S+) \((\d+)/(\d+)\)')


def expansion(root):
    text = (root / 'docs/gcc-knc-flags.md').read_text()
    match = re.search(r'^Expansion: `([^`]+)`$', text, re.M)
    return match[1].split() if match else None


def split_banner(stderr):
    """Return (banner lines, rest) when stderr starts with the banner."""
    end = stderr.find(MONOLOGUE[-1] + '\n\n')
    if end < 0:
        return None, stderr
    end += len(MONOLOGUE[-1]) + 2
    return stderr[:end].splitlines()[:-1], stderr[end:]


def banner_failures(lines):
    failures = []
    if len(lines) > 20:
        failures.append('banner has %d lines' % len(lines))
    for line in lines:
        if len(line) > 80 or any(ord(c) < 32 or ord(c) > 126 for c in line):
            failures.append('banner line not 80-column 7-bit ASCII: %r' % line)
    text = [line[17:] if len(line) > 17 else '' for line in lines]
    found = [line for line in text if line in MONOLOGUE]
    if found != list(MONOLOGUE):
        failures.append('monologue lines out of place: %r' % text)
    if 'PHI' not in '\n'.join(line[:17] for line in lines):
        failures.append('no PHI in the art')
    return failures


def t1(runner):
    runner.t1_sources([runner.source_dir / 'knc-phinix.c'])
    source = runner.source_dir / 'knc-phinix.c'
    out = runner.out
    base = [str(runner.cc), *runner.cc_flags, '--sysroot=' + str(runner.sysroot)]

    def run(*args, force=False, makeflags=None):
        env = dict(runner.env)
        env.pop('MAKEFLAGS', None)
        env.pop('GCC_KNC_FORCE_TERMINAL', None)
        if force:
            env['GCC_KNC_FORCE_TERMINAL'] = '1'
        if makeflags is not None:
            env['MAKEFLAGS'] = makeflags
        return subprocess.run([*base, *map(str, args)], env=env, cwd=out, text=True,
                              errors='replace', stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=120)

    # Expansion, x86 rejection and assembly identity.
    failures = []
    expanded = expansion(runner.root)
    if not expanded:
        failures.append('no "Expansion: `...`" line in docs/gcc-knc-flags.md')
    else:
        shown = run('-###', '-mphinix', '-c', source)
        cc1 = [line for line in shown.stderr.splitlines() if '/cc1' in line or '\\cc1' in line]
        if shown.returncode or not cc1:
            failures.append('-### -mphinix: exit %d %s' % (shown.returncode, shown.stderr[-800:]))
        else:
            words = re.findall(r'"([^"]*)"|(\S+)', cc1[0])
            words = [a or b for a, b in words]
            missing = [flag for flag in expanded if flag not in words]
            if missing or any(w.startswith(('-mphinix', '-mno-phinix', '-mprogress',
                                            '-mno-progress')) for w in words):
                failures.append('-### cc1 line lacks %s or names a phinix switch: %s'
                                % (missing, cc1[0][-600:]))
        x86 = run('-mphinix', '-march=x86-64', '-S', source, '-o', out / 'phinix-x86.s')
        if x86.returncode == 0 or 'mphinix' not in x86.stderr:
            failures.append('-mphinix -march=x86-64 not rejected: exit %d %s'
                            % (x86.returncode, x86.stderr[-400:]))
        bundled = run('-mphinix', '-S', source, '-o', out / 'phinix-flag.s')
        spelled = run(*expanded, '-S', source, '-o', out / 'phinix-expanded.s')
        if bundled.returncode or spelled.returncode:
            failures.append('-S: %s %s' % (bundled.stderr[-400:], spelled.stderr[-400:]))
        elif ((out / 'phinix-flag.s').read_text() != (out / 'phinix-expanded.s').read_text()):
            failures.append('-mphinix -S differs from the documented expansion -S')
    runner.result('t1 -mphinix expansion, x86 rejection and .s identity', failures)

    # Banner and bar on a forced terminal; removing them leaves the plain run.
    failures = []
    for case, extra, banner, bar in (
            ('-mphinix', ['-mphinix'], True, True),
            ('-mphinix warning', ['-mphinix', '-DKNC_PHINIX_WARN'], True, True),
            ('-mphinix error', ['-mphinix', '-DKNC_PHINIX_ERROR'], True, True),
            ('-mprogress', ['-O2', '-mprogress'], False, True),
            ('-mno-phinix-banner', ['-mphinix', '-mno-phinix-banner'], False, True),
            ('-mno-progress', ['-mphinix', '-mno-progress'], True, False)):
        plain_o, forced_o = out / 'phinix-plain.o', out / 'phinix-forced.o'
        for path in (plain_o, forced_o):
            if path.exists():
                path.unlink()
        plain = run(*extra, '-c', source, '-o', plain_o)
        forced = run(*extra, '-c', source, '-o', forced_o, force=True)
        lines, rest = split_banner(forced.stderr)
        if TERMINAL.search(plain.stderr) or split_banner(plain.stderr)[0] is not None:
            failures.append(case + ': banner or bar with stderr not a terminal')
        if (lines is not None) != banner:
            failures.append(case + ': banner %s' % ('missing' if banner else 'present'))
        elif lines is not None:
            failures += [case + ': ' + f for f in banner_failures(lines)]
        draws = [BAR.search(s) for s in TERMINAL.findall(rest)]
        steps = [(m[4], m[5], int(m[6]), int(m[7]), int(m[3]), len(m[1]), len(m[2]))
                 for m in draws if m]
        if bar:
            jobs = 1 if 'error' in case else 2
            if ([s[:4] for s in steps]
                    != [('compiling', 'knc-phinix.c', 1, 2),
                        ('assembling', 'knc-phinix.c', 2, 2)][:jobs]
                    or any(p != 100 * (i + 1) // 2 or h * 2 != (h + d) * (i + 1)
                           for i, (_, _, _, _, p, h, d) in enumerate(steps))):
                failures.append(case + ': bar steps %r' % steps)
        elif steps or TERMINAL.search(rest):
            failures.append(case + ': bar present')
        if TERMINAL.sub('', rest) != plain.stderr:
            failures.append(case + ': diagnostics differ: %r vs %r'
                            % (TERMINAL.sub('', rest)[-300:], plain.stderr[-300:]))
        if forced.returncode != plain.returncode or forced.stdout != plain.stdout:
            failures.append(case + ': exit %d vs %d or stdout differs'
                            % (forced.returncode, plain.returncode))
        if plain_o.exists() != forced_o.exists() or (
                plain_o.exists() and plain_o.read_bytes() != forced_o.read_bytes()):
            failures.append(case + ': object differs')
    runner.result('t1 -mphinix banner and progress bar on a terminal', failures)

    # Off cases: the forced terminal changes nothing at all.
    failures = []
    for case, args, makeflags in (
            ('-E to stdout', ['-mphinix', '-E', source], None),
            ('-S -o -', ['-mphinix', '-S', source, '-o', '-'], None),
            ('-###', ['-mphinix', '-###', '-c', source], None),
            ('-v', ['-mphinix', '-v', '-c', source, '-o', out / 'phinix-v.o'], None),
            ('--version', ['-mphinix', '--version'], None),
            ('make -j', ['-mphinix', '-c', source, '-o', out / 'phinix-j.o'], ' -j4'),
            ('make jobserver', ['-mphinix', '-c', source, '-o', out / 'phinix-js.o'],
             ' --jobserver-auth=3,4'),
            ('both switches off', ['-mphinix', '-mno-phinix-banner', '-mno-progress',
                                   '-c', source, '-o', out / 'phinix-off.o'], None)):
        plain = run(*args, makeflags=makeflags)
        forced = run(*args, force=True, makeflags=makeflags)
        # -v and -### print the temporary file names, which differ between runs.
        strip = (lambda s: re.sub(r'/cc\w{6}\.\w+', '/ccTEMP', s)) if case in ('-v', '-###') else str
        if (forced.returncode != plain.returncode or forced.stdout != plain.stdout
                or strip(forced.stderr) != strip(plain.stderr)):
            failures.append(case + ': forced terminal changed the run: exit %d vs %d, %r'
                            % (forced.returncode, plain.returncode, forced.stderr[:300]))
    runner.result('t1 -mphinix banner and bar stay off', failures)
