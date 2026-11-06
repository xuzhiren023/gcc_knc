#!/usr/bin/env python3
"""Compile/lint the S6-10 ffs and mask reproducers and stage upstream run tests."""
import os
from pathlib import Path
import runpy
import shlex
import subprocess
import sys

import vect_suite as suite

CASES = ('pr109011-4', 'pr109011-5', 'vect-63', 'vect-outer-2b',
         'vect-outer-2d', 'vect-double-reduc-3', 'vect-double-reduc-7', 'vect-simd-17')


def main():
    env = os.environ.copy()
    env['PATH'] = os.pathsep.join(str(suite.TC / p) for p in
                                ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
    if os.name == 'nt':
        script = subprocess.check_output([str(suite.TC / 'cygwin/bin/cygpath.exe'),
                                          '-u', str(Path(__file__))], text=True).strip()
        return subprocess.call([str(suite.TC / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]], env=env)
    out = suite.SHARED / 'S6-10'
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
    red = '--red' in sys.argv
    for name in CASES:
        spec = suite.parse_directives((suite.CORPUS / (name + '.c')).read_text())
        flags = spec.options if spec.replaces_defaults else suite.DEFAULT + spec.options
        flags = [f for f in flags if not f.startswith('-fdump')]
        flags += ['-march=knc', '-w', '-iquote', str(suite.CORPUS),
                  '-fopt-info-vec-optimized']
        for reduced in ((True,) if red else (True, False)):
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
            if red:
                expected = 'extract_insn' if name.startswith('pr109011') else 'extract_constrain_insn'
                ok = result.returncode != 0 and 'internal compiler error' in result.stdout and expected in result.stdout
            else:
                ok = result.returncode == 0 and not violations
            print(('PASS ' if ok else 'FAIL ') + stem +
                  (': expected ICE; ' if red else ': compile/lint; ') + str(log))
            if violations:
                print(violations[:3])
            failed += not ok
            staged.unlink()
            if ok and artifact.suffix == '.mic':
                programs.append(artifact.name)
            else:
                artifact.unlink(missing_ok=True)
    if not red:
        cc += ['-march=knc', '--sysroot=' + str(suite.TC / 'sysroot')]
        source = suite.ROOT / 'tests/acceptance/s4_masks'
        driver = out / 'masks-driver.o'
        subprocess.run([*cc, '-O0', '-fwrapv', '-c', str(source / 'driver.c'),
                        '-o', str(driver)], env=env, check=True)
        for name, flags in (('o2v', ['-O2', '-ftree-vectorize']), ('o3', ['-O3'])):
            obj = out / 'masks-loops.o'
            artifact = out / ('s4_masks-' + name + '.mic')
            subprocess.run([*cc, *flags, '-fwrapv', '-c', str(source / 'loops.c'),
                            '-o', str(obj)], env=env, check=True)
            subprocess.run([*cc, str(driver), str(obj), '-lm', '-o', str(artifact)],
                           env=env, check=True)
            violations = list(lint(artifact, suite.TC, env))
            failed += bool(violations)
            print(('FAIL ' if violations else 'PASS ') + artifact.name + ': compile/lint')
            if violations:
                print(violations[:3])
            else:
                programs.append(artifact.name)
            obj.unlink()
        driver.unlink()
    print('Card binaries (not run): ' + ', '.join(programs))
    return int(bool(failed))


if __name__ == '__main__':
    sys.exit(main())
