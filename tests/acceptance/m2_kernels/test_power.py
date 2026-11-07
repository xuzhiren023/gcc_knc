"""Compile and run the production parser/arithmetic on the host, never the card."""
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROJECT = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
SHARED = PROJECT / '.work/_shared'
BIN = SHARED / 'toolchain/cygwin/bin'

if os.name == 'nt':
    env = os.environ.copy()
    env['PATH'] = str(BIN) + os.pathsep + env.get('PATH', '')
    script = subprocess.check_output([str(BIN / 'cygpath.exe'), '-u', str(Path(__file__).resolve())],
                                     text=True, env=env).strip()
    sys.exit(subprocess.call([str(BIN / 'python3.12.exe'), script], env=env))

out = SHARED / 'S6-13'
out.mkdir(exist_ok=True)
exe = out / 'test-power.exe'
subprocess.run([str(BIN / 'gcc'), '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                '-pthread', str(HERE / 'test_power.c'), '-lm',
                '-o', str(exe)], check=True)
sys.exit(subprocess.call([str(exe), str(HERE / 'sample-power.txt')]))
