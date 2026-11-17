#!/usr/bin/env python3
"""Standalone serial build of the lead-supplied, pinned MilkyWay checkout.

Source lists come from the pinned upstream CMake lists; configuration headers
and correctness patches are the lead-supplied standalone expansions. No
upstream optimization flags, BOINC wrapper, downloads or card execution.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

import corpus
import genset

SOURCE = corpus.SHARED / 'corpus-build/milkyway-nbody'
SUPPORT = corpus.SHARED / 'corpus-build/milkyway-nbody-support'
PARAMETERS = ('4.90652 1 0.386382 0.20556 1.74668 0.0420765 46.125 '
              '15.623 -215.279 114.242 181.825 353270 1.21041 2.87629').split()
ARGS = ['-f', 'params.lua', '-h', 'OCS_data_2025_north_194.hist',
        '--seed', '65477096', '-np', '14', '-p', *PARAMETERS]


def prepare(log):
    git = ['git', '-c', 'safe.directory=' + str(SOURCE), '-C', str(SOURCE)]
    head = subprocess.check_output([*git, 'rev-parse', 'HEAD'], text=True).strip()
    pin = corpus.M5_SOURCES['MilkyWay-Nbody']
    if head != pin['patched_commit']:
        raise ValueError('MilkyWay checkout is not the authorized pin')
    dirty = subprocess.check_output([*git, 'status', '--porcelain',
                                     '--untracked-files=no'], text=True)
    if dirty.strip():
        raise ValueError('MilkyWay pinned source has tracked changes')
    log.write('Read-only MilkyWay source: ' + head + '\n')


def source_list(component, variable):
    text = (SOURCE / component / 'CMakeLists.txt').read_text()
    text = re.sub(r'#[^\n]*', '', text)
    match = re.search(r'set\(\s*' + variable + r'\s+(.*?)\)', text, re.S)
    if not match:
        raise ValueError('missing pinned source list: ' + variable)
    names = match[1].replace('${NBODY_SRC_DIR}', 'src').split()
    if not names or any(not name.endswith(('.c', '.cc')) for name in names):
        raise ValueError('unsupported source list: ' + variable)
    return [SOURCE / component / name for name in names]


def build(out, cc, cxx, flags, log, native=False):
    out.mkdir(parents=True, exist_ok=True)
    config = SUPPORT / 'config'
    includes = [config] + [SOURCE / name for name in
                          ('nbody/include', 'milkyway/include', 'lua/include',
                           'popt/include', 'dSFMT', 'crlibm', 'crlibm/scs_lib')]
    sources = []
    for component, variables in (
            ('nbody', ('nbody_lib_src', 'nbody_lua_src')),
            ('milkyway', ('mw_lib_src', 'milkyway_lua_src')),
            ('lua', ('SRC_LIB',)), ('popt', ('libpopt_src',)),
            ('crlibm', ('crlibm_src', 'scs_lib_src'))):
        for variable in variables:
            sources.extend(source_list(component, variable))
    sources.extend(SOURCE / name for name in
                   ('nbody/src/main.c', 'dSFMT/dSFMT.c', 'lua/src/loadlib.c'))
    common = [*flags, '-ffp-contract=off', '-fno-strict-aliasing',
              '-DDOUBLEPREC=1', '-DDSFMT_MEXP=19937', '-DHAVE_CONFIG_H',
              '-D_GNU_SOURCE', *('-I' + str(p) for p in includes)]

    def compile_one(source):
        obj = out / (str(source.relative_to(SOURCE)).replace('/', '_') + '.o')
        diagnostic = obj.with_suffix('.log')
        cpp = source.suffix == '.cc'
        definitions = (['-DNBODY_LUA_TYPES_COMPILATION']
                       if source.name.startswith('nbody_lua') else [])
        # Target definitions from the pinned component CMakeLists.txt files.
        component = source.relative_to(SOURCE).parts[0]
        if component == 'milkyway':
            definitions.append('-DMILKYWAY_LUA_COMPILATION' if
                               source.name.startswith('milkyway_lua') else
                               '-DMILKYWAY_MATH_COMPILATION')
        elif component == 'crlibm':
            definitions.extend(['-DSCS_NB_WORDS=8', '-DSCS_NB_BITS=30'])
        command = [cxx if cpp else cc, *common, *definitions,
                   '-std=gnu++11' if cpp else '-std=gnu99', '-c', source, '-o', obj]
        with diagnostic.open('w') as output:
            result = subprocess.run(list(map(str, command)), stdout=output,
                                    stderr=subprocess.STDOUT)
        return obj, diagnostic, command, result.returncode

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(compile_one, sources))
    failed = []
    for obj, diagnostic, command, status in results:
        log.write('COMMAND ' + json.dumps(list(map(str, command))) + '\n')
        log.write(diagnostic.read_text())
        diagnostic.unlink()
        if status:
            failed.append(obj.name)
    log.flush()
    if failed:
        raise RuntimeError('MilkyWay compile failures: ' + ', '.join(failed))
    binary = out / ('workload.exe' if native else 'workload')
    corpus.execute([cxx, *flags, *(r[0] for r in results),
                    *([] if native else corpus.link_paths()),
                    '-lm', '-lpthread', '-o', binary], out, log)
    for obj, _, _, _ in results:
        obj.unlink()
    return binary


def inputs(out):
    files = []
    for name in ('params.lua', 'OCS_data_2025_north_194.hist'):
        target = out / name
        shutil.copyfile(SUPPORT / 'inputs' / name, target)
        files.append(target)
    return files


def normalize(text):
    values = re.findall(r'<search_likelihood>\s*([^<]+)\s*</search_likelihood>', text)
    if len(values) != 1 or not math.isfinite(float(values[0])):
        raise ValueError('missing or nonfinite stock MilkyWay likelihood')
    return json.dumps(dict(likelihood=float(values[0])))


def host_check(stage):
    out = stage / 'host/MilkyWay-Nbody'
    out.mkdir(parents=True, exist_ok=True)
    with (out / 'build.log').open('w') as log:
        prepare(log)
        binary = build(out, 'gcc', 'g++', ['-O2'], log, native=True)
    inputs(out)
    # Never resume a previous run's checkpoint.
    checkpoint = out / 'nbody_checkpoint'
    if checkpoint.exists():
        checkpoint.unlink()
    with (out / 'stdout').open('w') as stdout, (out / 'stderr').open('w') as stderr:
        subprocess.run([str(binary), *ARGS], cwd=out, stdout=stdout,
                       stderr=stderr, timeout=1800, check=True)
    actual = normalize((out / 'stdout').read_text() + (out / 'stderr').read_text())
    reference = stage / 'references/MilkyWay-Nbody.txt'
    reference.parent.mkdir(parents=True, exist_ok=True)
    reference.write_text(actual)
    return actual, actual


def build_card(compiler, flags, out, log):
    prepare(log)
    binary = build(out, corpus.compiler_path(compiler),
                   corpus.compiler_path(compiler, 'g++'), flags, log)
    application = out / 'milkyway-nbody'
    binary.rename(application)
    # The corpus launcher always executes ./workload without arguments.
    # Keep the pinned argument vector here and discard prior checkpoints so
    # every launch performs the same complete work.
    driver = out / 'driver.c'
    argv = ', '.join(json.dumps(s) for s in ['./milkyway-nbody', *ARGS])
    driver.write_text('#include <unistd.h>\n#include <errno.h>\n'
                      'int main(void) {\n'
                      '  char *args[] = {' + argv + ', 0};\n'
                      '  if (unlink("nbody_checkpoint") && errno != ENOENT) return 2;\n'
                      '  execv(args[0], args);\n  return 127;\n}\n')
    corpus.execute([corpus.compiler_path(compiler), *flags, driver,
                    *corpus.link_paths(), '-o', binary], out, log)
    for executable in (binary, application):
        corpus.execute([sys.executable, corpus.ROOT / 'tools/knc_lint', executable], out, log)
    return [binary, application, *inputs(out),
            *genset.runtimes(application, compiler, out, log)]
