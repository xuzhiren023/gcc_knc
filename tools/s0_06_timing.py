"""Measure the stock shared GCC build for S0-06 under Cygwin."""
import os
from pathlib import Path
import subprocess
import time


shared = Path('/cygdrive/c/Users/xuzhi/Documents/gcc_knc/.work/_shared')
source = shared / 'gcc'
build = shared / 'gcc-build'
os.environ['PATH'] = '/usr/bin:/bin'
os.environ['TMPDIR'] = str(shared / 'tmp')
Path(os.environ['TMPDIR']).mkdir(exist_ok=True)
build.mkdir(exist_ok=True)


def run(label, command, cwd=build):
    start = time.monotonic()
    result = subprocess.run(command, cwd=cwd)
    print('MEASURE %s: exit=%d seconds=%.3f' %
          (label, result.returncode, time.monotonic() - start), flush=True)
    return result.returncode


def disk(label, path):
    size = sum(p.stat().st_size for p in path.rglob('*') if p.is_file())
    print('DISK %s: bytes=%d GiB=%.3f (logical file sizes)' %
          (label, size, size / 1024**3), flush=True)


run('host compiler', ['gcc', '--version'])
run('config.sub k1om', ['bash', str(source / 'config.sub'), 'k1om-mpss-linux'])
disk('checkout including .git', source)
code = run('configure', ['bash', str(source / 'configure'),
           '--target=x86_64-pc-cygwin', '--enable-languages=c,fortran',
           '--disable-bootstrap', '--disable-multilib', '--disable-lto'])
if code:
    disk('build', build)
    raise SystemExit(code)
code = run('full all-gcc', ['make', '-j8', 'all-gcc'])
if code:
    disk('build', build)
    raise SystemExit(code)
os.utime(source / 'gcc/config/i386/i386.cc', None)
code = run('i386.cc incremental', ['make', '-j8', 'all-gcc'])
if code:
    raise SystemExit(code)
md = source / 'gcc/config/i386/i386.md'
original = md.read_bytes()
try:
    md.write_bytes(original + b'\n;; S0-06 timing: regenerate after a one-file machine description change.\n')
    code = run('i386.md incremental', ['make', '-j8', 'all-gcc'])
finally:
    md.write_bytes(original)
disk('build', build)
raise SystemExit(code)
