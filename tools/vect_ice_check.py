#!/usr/bin/env python3
"""Verify the reduced S6-07 baseline ICE cases; no compiler fixes or card run."""
import os
from pathlib import Path
import subprocess
import sys

import vect_suite as suite


def main():
    requested = sys.argv[1:]
    env = os.environ.copy()
    env['PATH'] = os.pathsep.join(str(suite.TC / p) for p in ('cross/bin', 'cygwin/bin')) + os.pathsep + env.get('PATH', '')
    if os.name == 'nt':
        script = subprocess.check_output([str(suite.TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__))], text=True).strip()
        return subprocess.call([str(suite.TC / 'cygwin/bin/python3.12.exe'), script, *requested], env=env)
    build = suite.SHARED / 'gcc-build/gcc'
    out = suite.SHARED / 'S6-07'
    failures = 0
    for source in sorted((suite.ROOT / 'tests/regress/s6-07-vect').glob('*.c')):
        if requested and source.stem not in requested:
            continue
        spec = suite.parse_directives((suite.CORPUS / source.name).read_text())
        flags = spec.options if spec.replaces_defaults else suite.DEFAULT + spec.options
        flags = [f for f in flags if not f.startswith('-fdump')]
        artifact = out / 'reduced.o'
        command = [str(build / 'xgcc.exe'), '-B' + str(build) + '/', *flags,
                   '-march=knc', '-w', '-c', str(source), '-o', str(artifact)]
        result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, timeout=120)
        log = out / (source.stem + '-reduced.log')
        log.write_text(' '.join(command) + '\n' + result.stdout)
        expected = ('extract_insn' if source.stem.startswith('pr109011') else
                    'expand_vec_series_expr' if source.stem in ('pr114322', 'pr53185', 'pr53185-2', 'vect-123') else
                    None)
        ice = next((line for line in result.stdout.splitlines() if 'internal compiler error' in line), '')
        ok = bool(result.returncode and ice and (not expected or expected in ice))
        print(('REPRODUCED ' if ok else 'FAILED ') + source.name + ': ' + (ice or 'no ICE'))
        failures += not ok
        artifact.unlink(missing_ok=True)
    return int(bool(failures))


if __name__ == '__main__':
    sys.exit(main())
