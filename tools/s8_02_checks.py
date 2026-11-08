#!/usr/bin/env python3
"""S8-02 masked loop tails: T1 scans, guard-page card builds and acceptance builds.

    python tools/run.py --name S8-02-t1 -- python tools/s8_02_checks.py t1
    python tools/run.py --name S8-02-native -- python tools/s8_02_checks.py native
    python tools/run.py --name S8-02-acceptance -- python tools/s8_02_checks.py acceptance

t1 runs only the tail scans (tests/t1/knc-mask-tail-*.c, knc-mask-split.c).
native builds tests/regress/knc-tail-guard.c into .work/_shared/S8-02 as
knc-tail-guard.mic and knc-tail-guard-control{1,2,3}.mic (control 3: the
aligned length-16 kernel reads one element past its last line, since an
aligned masked over-read stays inside its own line and cannot reach a
guard), checks the new tail forms in the kernel assembly and lints; the
lead runs them on the card.
acceptance builds the s4_masks and s5_ops fixtures there as well.
"""
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'
BUILD = SHARED / 'gcc-build/gcc'
OUT = SHARED / 'S8-02'
TAIL_SOURCES = ('knc-mask-tail-O2.c', 'knc-mask-tail-O3.c', 'knc-mask-tail-len.c',
                'knc-mask-split.c')


def cc():
    return [str(BUILD / 'xgcc'), '-B' + str(BUILD) + '/', '-march=knc',
            '--sysroot=' + str(TC / 'sysroot')]


def run(args):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True)


def t1():
    from types import SimpleNamespace
    from check import Runner
    runner = Runner(SimpleNamespace(compiler='gcc16', cc=None))
    with runner._output:
        runner.t1_sources(runner.source_dir / name for name in TAIL_SOURCES)
    return int(runner.failed)


def native():
    """Build and lint only; card execution belongs to the lead."""
    from check import function_body
    source = ROOT / 'tests/regress/knc-tail-guard.c'
    OUT.mkdir(exist_ok=True)
    driver = OUT / 'tail-driver.o'
    run([*cc(), '-O0', '-fwrapv', '-Wall', '-Wextra', '-c', source, '-o', driver])
    for control in range(4):
        tag = '' if control == 0 else '-control%d' % control
        kernels = OUT / ('tail-loops%s.o' % tag)
        binary = OUT / ('knc-tail-guard%s.mic' % tag)
        run([*cc(), '-O2', '-ftree-vectorize', '-fwrapv', '-Wall', '-Wextra',
             '-DKNC_TAIL_LOOPS', '-DGUARD_CONTROL=%d' % control, '-save-temps=obj',
             '-c', source, '-o', kernels])
        run([*cc(), driver, kernels, '-o', binary])
        (OUT / ('tail-loops%s.i' % tag)).unlink(missing_ok=True)
        asm = OUT / ('tail-loops%s.s' % tag)
        text = asm.read_text()
        # The forms the ticket delivers; a stale compiler fails here.  The
        # runtime kernels need both paths: the gather/scatter and the
        # single-lane moves for a mask within C6's limit (round 1), never a
        # masked high half.
        lane = r'\bv(?:loadunpackl|packstorel)\w+\s[^\n]*\{%k'
        half = r'\bv(?:loadunpackh|packstoreh)\w+\s[^\n]*\{%k'
        for name, needed, forbidden in [
                ('add_f32', ('vgatherdps', 'vscatterdps', lane), ('fld', 'vpermd', half)),
                ('add_f64', ('vgatherdpd', 'vscatterdpd', lane), ('fld', 'vpermd', half)),
                ('add_al_f32', ('vmovaps',), ('fld',)),
                ('fix_f32_5', ('vgatherdps', 'vscatterdps'), ('fld',)),
                ('fix_al_f32_5', ('vmovaps',), ('fld',)),
                ('small_f32', ('vgatherdps', 'vscatterdps', lane), ('fld', half))]:
            body = function_body(text, name) or ''
            missing = [n for n in needed if not re.search(n, body)]
            present = [f for f in forbidden if re.search(f, body)]
            if missing or present:
                raise SystemExit('%s: %s lacks %s or has %s' % (asm.name, name, missing, present))
        run([sys.executable, ROOT / 'tools/knc_lint', asm, binary])
        print('BUILT and linted ' + str(binary) + '; native execution pending lead', flush=True)
    return 0


def acceptance():
    for fixture in ('s4_masks', 's5_ops'):
        source = ROOT / 'tests/acceptance' / fixture
        dest = OUT / fixture
        dest.mkdir(parents=True, exist_ok=True)
        driver = dest / 'driver.o'
        run([*cc(), '-O0', '-fwrapv', '-c', source / 'driver.c', '-o', driver])
        variants = [('o2v', ['-O2', '-ftree-vectorize']), ('o3', ['-O3'])]
        if fixture == 's5_ops':
            variants += [('fast', ['-O3', '-ffast-math']),
                         ('neg', ['-O2', '-ftree-vectorize', '-DNEGATIVE_CONTROL'])]
        else:
            variants += [('guard', ['-O2', '-ftree-vectorize', '-DGUARD_CONTROL']),
                         ('guard-al', ['-O2', '-ftree-vectorize', '-DGUARD_AL_CONTROL'])]
        for name, flags in variants:
            obj = dest / (name + '.o')
            run([*cc(), *flags, '-fwrapv', '-c', source / 'loops.c', '-o', obj])
            run([*cc(), *flags, '-fwrapv', driver, obj, '-lm', '-o', dest / (name + '.mic')])
            print('BUILT ' + fixture + '/' + name + '.mic; native execution pending lead', flush=True)
    return 0


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                      ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output(
            [str(TC / 'cygwin/bin/cygpath.exe'), '-u', __file__],
            env=env, text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'),
                                script, *sys.argv[1:]], env=env)
    os.environ['PATH'] = ':'.join(str(TC / p) for p in
                                  ('cross/bin', 'cygwin/bin')) + ':' + os.environ['PATH']
    os.environ['LC_ALL'] = 'C'
    action = sys.argv[1]
    if action == 't1':
        return t1()
    if action == 'native':
        return native()
    if action == 'acceptance':
        return acceptance()
    raise ValueError('expected t1, native or acceptance')


if __name__ == '__main__':
    sys.exit(main())
