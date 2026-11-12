"""Build/lint the native artifact only; never launch a card job or build GCC."""
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
TC = SHARED / 'toolchain'


def main():
    env = os.environ.copy()
    env['PATH'] = os.pathsep.join(str(TC / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
    if os.name == 'nt':
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__))], text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script], env=env)
    sys.path.insert(0, str(ROOT / 'tools'))
    import storage
    build = Path(storage.gcc_build_dir(PROJECT)) / 'gcc'
    out = SHARED / 'S11-05'
    out.mkdir(exist_ok=True)
    binary = out / 'membw.mic'
    env['TMPDIR'] = str(SHARED / 'tmp')
    command = [str(build / 'xgcc'), '-B' + str(build) + '/',
               '--sysroot=' + str(TC / 'sysroot'), '-march=knc', '-O2',
               '-fno-tree-vectorize', '-fno-prefetch-loop-arrays',
               '-ffp-contract=off', '-std=gnu11', '-Wall', '-Wextra',
               '-pthread', str(HERE / 'membw.c'), '-lrt', '-o', str(binary)]
    print(' '.join(command), flush=True)
    subprocess.run(command, env=env, check=True, timeout=300)
    lint = runpy.run_path(str(ROOT / 'tools/knc_lint'))['lint']
    violations = list(lint(binary, TC, env))
    if violations:
        for item in violations[:10]:
            print(item)
        return 1
    for name in ('sweep.sh',):
        shutil.copyfile(HERE / name, out / name)
    print('PASS native build/lint: ' + str(binary) + '; native execution pending lead')
    return 0


if __name__ == '__main__':
    sys.exit(main())
