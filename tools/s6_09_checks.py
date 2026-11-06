#!/usr/bin/env python3
"""Compile/lint the S6-09 series reproducers and stage upstream run tests."""
import os
from pathlib import Path
import runpy
import shlex
import subprocess
import sys

import vect_suite as suite

CASES = ('vect-123', 'pr114322', 'pr53185', 'pr53185-2', 'vect-simd-17',
         'vect-strided-epilogue-1', 'vect-strided-store')


def main():
    env = os.environ.copy()
    env['PATH'] = os.pathsep.join(str(suite.TC / p) for p in
                                ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
    if os.name == 'nt':
        script = subprocess.check_output([str(suite.TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', str(Path(__file__))], text=True).strip()
        return subprocess.call([str(suite.TC / 'cygwin/bin/python3.12.exe'), script], env=env)
    out = suite.SHARED / 'S6-09'
    out.mkdir(exist_ok=True)
    env['TMPDIR'] = str(suite.SHARED / 'tmp')
    build = suite.SHARED / 'gcc-build/gcc'
    cc = [str(build / 'xgcc.exe'), '-B' + str(build) + '/']
    lint = runpy.run_path(str(suite.ROOT / 'tools/knc_lint'))['lint']
    header = (suite.CORPUS / 'tree-vect.h').read_text().replace(
        '#elif defined(__i386__) || defined(__x86_64__)',
        '#elif defined(__k1om__)\n  /* Card selected by the lead. */\n'
        '#elif defined(__i386__) || defined(__x86_64__)')
    (out / 'tree-vect.h').write_text(header)
    failed, programs = 0, []
    for name in CASES:
        spec = suite.parse_directives((suite.CORPUS / (name + '.c')).read_text())
        flags = spec.options if spec.replaces_defaults else suite.DEFAULT + spec.options
        flags = [f for f in flags if not f.startswith('-fdump')]
        flags += ['-march=knc', '-w', '-iquote', str(suite.CORPUS),
                  '-fopt-info-vec-optimized']
        for reduced in (True, False):
            stem = name + ('-reduced' if reduced else '')
            source = (suite.ROOT / 'tests/regress/s6-07-vect' if reduced else suite.CORPUS) / (name + '.c')
            staged = out / (name + '.c')
            staged.write_text(source.read_text())
            artifact = out / (stem + ('.mic' if not reduced and spec.action == 'run' else '.o'))
            command = [*cc, *flags, str(staged), *([] if artifact.suffix == '.mic' else ['-c']),
                       '-lm', '-o', str(artifact)]
            result = subprocess.run(command, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, timeout=120)
            log = out / (stem + '.log')
            log.write_text(shlex.join(command) + '\n' + result.stdout)
            violations = list(lint(artifact, suite.TC, env)) if not result.returncode else []
            ok = result.returncode == 0 and not violations
            print(('PASS ' if ok else 'FAIL ') + stem + ': compile/lint; ' + str(log))
            if violations:
                print(violations[:3])
            failed += not ok
            staged.unlink()
            if ok and artifact.suffix == '.mic':
                programs.append(artifact.name)
            else:
                artifact.unlink(missing_ok=True)
    print('Ticket names seven sources although its count says eight.')
    print('Card binaries (not run): ' + ', '.join(programs))
    return int(bool(failed))


if __name__ == '__main__':
    sys.exit(main())
