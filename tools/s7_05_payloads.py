#!/usr/bin/env python3
"""Build/lint S7-05 card payloads; never execute them or install a runtime.

Old clients use donor GCC and donor libgcc at link time. New clients use
the fork C compiler and candidate libgcc. Both run against private directories
selected explicitly by the lead. C++ is built by the donor (fork is C/Fortran).
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared'
TC = SHARED / 'toolchain'
BUILD = SHARED / 'gcc-build'
RUNTIME = BUILD / 'k1om-mpss-linux/libgcc'
OUT = SHARED / 'S7-05'
SRC = ROOT / 'tests/t2/s7-05'


def run(args):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True, timeout=180)


def main():
    # Check the whole payload contract before producing any outputs.
    for name in ('compat.c', 'new.c', 'unwind.cc', 'plugin.cc', 'run.sh',
                 'compat.expected', 'new.expected', 'unwind.expected'):
        if not (SRC / name).is_file():
            raise RuntimeError('missing S7-05 payload input: ' + name)
    OUT.mkdir(exist_ok=True)
    os.environ['TMPDIR'] = str(SHARED / 'tmp')
    for label, source in (('donor', TC / 'sysroot/lib64/libgcc_s.so.1'),
                          ('candidate', RUNTIME / 'libgcc_s.so.1')):
        dest = OUT / label
        dest.mkdir(exist_ok=True)
        shutil.copyfile(source, dest / 'libgcc_s.so.1')
    # Donor libm.so names /lib64/libm.so.6; ld must resolve it in this sysroot.
    donor_flags = ['--sysroot=' + str(TC / 'sysroot'),
                   '-B' + str(TC / 'sysroot/lib64') + '/',
                   '-L' + str(TC / 'sysroot/lib64')]
    donor = [TC / 'cross/bin/k1om-mpss-linux-gcc', *donor_flags]
    new = [BUILD / 'gcc/xgcc', '-B' + str(RUNTIME) + '/',
           '-B' + str(BUILD / 'gcc') + '/']
    common = ['-O1', '-fno-builtin', '-fno-omit-frame-pointer',
              '-fno-optimize-sibling-calls', '-fexceptions', '-fasynchronous-unwind-tables',
              '-shared-libgcc', '-Wl,--no-as-needed']
    products = []
    for label, cc in (('old', donor), ('new', new)):
        target = OUT / (label + '-compat.mic')
        run([*cc, *common, SRC / 'compat.c', '-lm', '-ldl', '-o', target])
        products.append(target)
        shutil.copyfile(SRC / 'compat.expected', OUT / (target.name + '.expected'))
    target = OUT / 'new-helpers.mic'
    run([*new, *common, SRC / 'new.c', '-o', target])
    products.append(target)
    shutil.copyfile(SRC / 'new.expected', OUT / (target.name + '.expected'))
    cxx = [TC / 'cross/bin/k1om-mpss-linux-g++', *donor_flags, *common]
    # This old linker lacks --no-eh-frame-hdr. Remove the driver's positive
    # option from its link spec rather than passing an unsupported negation.
    specs = subprocess.check_output([str(cxx[0]), '-dumpspecs'], text=True)
    link = re.search(r'^\*link:\n(.*?)(?:\n\n|\Z)', specs, re.M | re.S)
    if not link or '--eh-frame-hdr' not in link[1]:
        raise RuntimeError('donor link spec lacks the expected EH-frame option')
    nohdr = OUT / 'no-eh-frame-hdr.specs'
    nohdr.write_text('*link:\n' + link[1].replace('--eh-frame-hdr','') + '\n\n')
    # Registration is explicit in plugin.cc and cannot fall back to a header.
    plugin = OUT / 'plugin.so'
    # Replacing *link also removes the driver's injected linker sysroot.
    run([*cxx, '-fPIC', '-shared', '-specs=' + str(nohdr),
         '-Wl,--sysroot=' + str(TC / 'sysroot'), SRC / 'plugin.cc',
         '-o', plugin])
    products.append(plugin)
    (OUT / 'plugin.so.expected').write_text('Loaded by old-unwind.mic; see old-unwind.mic.expected\n')
    target = OUT / 'old-unwind.mic'
    run([*cxx, '-rdynamic', SRC / 'unwind.cc', '-pthread', '-ldl', '-o', target])
    products.append(target)
    shutil.copyfile(SRC / 'unwind.expected', OUT / (target.name + '.expected'))
    shutil.copyfile(SRC / 'run.sh', OUT / 'run.sh')
    run([sys.executable, ROOT / 'tools/knc_lint', *products])
    for path in products:
        elf = subprocess.check_output([str(TC / 'cross/bin/k1om-mpss-linux-readelf'),
                                       '-W', '-h', '-l', '-d', '-V', '--dyn-syms', str(path)], text=True)
        (OUT / (path.name + '.elf.txt')).write_text(elf)
        if 'libgcc_s.so.1' not in elf or 'K1OM' not in elf:
            raise RuntimeError('missing K1OM/shared libgcc contract: ' + path.name)
        if '(RPATH)' in elf or '(RUNPATH)' in elf:
            raise RuntimeError('payload has implicit runtime path: ' + path.name)
        if path.name.endswith('-compat.mic'):
            for name, version in (('__gttf2','3.0'), ('__lttf2','3.0'),
                                  ('__netf2','3.0'), ('__divtc3','4.0.0'),
                                  ('__multc3','4.0.0'), ('__powitf2','4.0.0')):
                if not re.search(r'\bUND\s+' + name + '@GCC_' + re.escape(version) + r'\b', elf):
                    raise RuntimeError('missing compatibility import: ' + name)
        if path.name == 'new-helpers.mic':
            from s7_03_checks import ADDITIONS
            for name in ADDITIONS:
                if name.replace('@@','@') not in elf:
                    raise RuntimeError('missing new helper import: ' + name)
        if path.name == 'plugin.so':
            if re.search(r'^\s*GNU_EH_FRAME\s', elf, re.M):
                raise RuntimeError('plugin unexpectedly has an EH frame header')
            for name in ('__register_frame', '__deregister_frame'):
                if not re.search(r'\bUND\s+' + name + r'@GCC_', elf):
                    raise RuntimeError('plugin lacks frame registration: ' + name)
    print('PASS S7-05: built and linted; expected output and explicit-path runner staged at ' + str(OUT))
    print('NOT RUN NATIVELY: lead owns S7-06 card execution')


if __name__ == '__main__':
    if os.name == 'nt':
        env = os.environ.copy()
        env['PATH'] = os.pathsep.join(str(TC / p) for p in
                                    ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output([str(TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', __file__], env=env, text=True).strip()
        sys.exit(subprocess.call([str(TC / 'cygwin/bin/python3.12.exe'), script], env=env))
    main()
