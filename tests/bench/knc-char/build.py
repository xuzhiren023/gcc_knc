"""Build/lint card corpus and exercise host arguments, through tools/run.py."""
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'
OUT = SHARED / 'S8-01'


def run(args):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True)


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'), '-u', __file__],
                                         env=env, text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]], env=env)
    os.environ['PATH'] = ':'.join(str(TC / p) for p in ('cross/bin', 'cygwin/bin')) + ':' + os.environ['PATH']
    os.environ['LC_ALL'] = 'C'
    global OUT
    args = sys.argv[1:]
    # --out NAME stages under .work/_shared/NAME (S8-17 C12); default S8-01.
    if '--out' in args:
        i = args.index('--out')
        OUT = SHARED / args[i+1]
        del args[i:i+2]
    if not args or args[0] != 'probes':
        from kernels import emit
        emit(OUT)
    # The gcc2 lane (KNC_GCC_SLOT=2) builds with its own tree (S8-10).
    ccdir = SHARED / ('gcc-build-2' if os.environ.get('KNC_GCC_SLOT') == '2' else 'gcc-build') / 'gcc'
    cc = [ccdir / 'xgcc', '-B' + str(ccdir) + '/', '--sysroot=' + str(TC / 'sysroot'),
          '-march=knc', '-O2', '-fno-tree-vectorize', '-ffp-contract=off',
          '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-I' + str(OUT)]
    # Stop after a failed phase; a retry must name only the remaining phase.
    action = args[0] if args else 'all'
    if action == 'probes':
        # S9-16 C13/C14: standalone programs staged under .work/_shared/S9-16.
        out = SHARED / 'S9-16'
        out.mkdir(parents=True, exist_ok=True)
        for name in ('c13', 'c14'):
            run([*cc, '-S', HERE / f'{name}.c', '-o', out / f'{name}.s'])
            run([*cc, out / f'{name}.s', '-pthread', '-o', out / f'{name}.mic'])
            run([sys.executable, ROOT / 'tools/knc_lint', out / f'{name}.s', out / f'{name}.mic'])
        print('PASS C13/C14 card build and lint (not executed)')
        return 0
    if action in ('all', 'build'):
        run([*cc, '-S', HERE / 'driver.c', '-o', OUT / 'driver.s'])
        run([*cc, OUT / 'driver.s', OUT / 'kernels.s', '-pthread', '-lrt', '-o', OUT / 'knc-char.mic'])
        print('PASS card build (not executed)')
    if action in ('all', 'lint'):
        run([sys.executable, ROOT / 'tools/knc_lint', OUT / 'driver.s', OUT / 'kernels.s', OUT / 'knc-char.mic'])
        print('PASS assembly and ELF lint')
    if action in ('all', 'host'):
        run(['gcc', '-O2', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-DCHAR_HOST',
             '-I' + str(OUT), HERE / 'driver.c', '-pthread', '-o', OUT / 'knc-char-host.exe'])
        run([sys.executable, HERE / 'check_args.py', OUT / 'knc-char-host.exe'])
        run([sys.executable, HERE / 'check_s8.py', OUT / 'knc-char-host.exe'])
        run([sys.executable, HERE / 'check_c12.py', OUT / 'knc-char-host.exe'])
    if action not in ('all', 'build', 'lint', 'host'):
        raise ValueError('expected all, build, lint, host or probes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
