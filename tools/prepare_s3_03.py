"""S3-03 host logic test and KNC batch build; invoke through tools/run.py."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
TC = SHARED / 'toolchain'
OUT = SHARED / 'tmp/S3-03'


def main():
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                    ('cross/bin', 'cygwin/bin')) + os.pathsep + env['PATH']
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', str(Path(__file__).resolve())], text=True).strip()
        return subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script,
                                *sys.argv[1:]], env=env)
    os.environ['PATH'] = ':'.join(str(TC / p) for p in ('cross/bin', 'cygwin/bin')) + ':' + os.environ['PATH']
    os.environ['TMPDIR'] = str(SHARED / 'tmp')
    os.environ['LC_ALL'] = 'C'
    OUT.mkdir(exist_ok=True)

    def run(*args):
        print('+ ' + ' '.join(map(str, args)), flush=True)
        subprocess.run(list(map(str, args)), check=True)

    source = ROOT / 'tests/regress/knc-unaligned-probe.c'
    flags = ['-std=gnu99', '-O2', '-Wall', '-Wextra', '-Werror']
    if '--build-only' not in sys.argv:
        run(TC / 'cygwin/bin/gcc', *flags, '-DHOST_LOGIC', source, '-o', OUT / 'probe-host.exe')
        run(OUT / 'probe-host.exe', '--self-test')
    if '--t0-only' in sys.argv:
        return 0
    build = SHARED / 'gcc-build/gcc'
    cc = [build / 'xgcc', '-B' + str(build) + '/']
    native_flags = [*flags, '-march=knc', '-fno-tree-vectorize', '-Wa,--march=k1om']
    run(*cc, *native_flags, '-S', source, '-o', OUT / 'probe.s')
    run(*cc, '-march=knc', '-Wa,--march=k1om', OUT / 'probe.s', '-o', OUT / 'knc-unaligned-probe.mic')
    run(sys.executable, ROOT / 'tools/knc_lint', OUT / 'probe.s', OUT / 'knc-unaligned-probe.mic')
    (OUT / 'batch.txt').write_text('knc-unaligned-probe.mic\t["--native"]\t128\n')
    files = list(OUT.iterdir())
    run(TC / 'cygwin/bin/setfacl', '-b', '--', *files)
    for path in files:
        path.chmod(0o755 if path.suffix in ('.mic', '.exe') else 0o644)
    print('READY ' + str(OUT / 'batch.txt') + '; native observations NOT RUN', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
