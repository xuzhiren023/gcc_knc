#!/usr/bin/env python3
"""Frozen, unscored Q1-Q6 set. Stage on host; only the lead invokes lead."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import corpus

ROOT, SHARED = corpus.ROOT, corpus.SHARED
SUPPORT = ROOT / 'tools/genset'
SOURCE = SHARED / 'genset/src'
STAGE = SHARED / 'S12-02'
PROGRAMS = tuple('Q%d' % i for i in range(1, 7))
COMPILERS = (corpus.DONOR, corpus.KNC)
ATOL, RTOL = 1e-10, 1e-8


def make_plan():
    rows = []
    for run in range(3):
        for profile in ('full', '3100', '5100'):
            for program in PROGRAMS:
                order = COMPILERS if run % 2 == 0 else COMPILERS[::-1]
                for index, compiler in enumerate(order):
                    rows.append(dict(program=program, compiler=compiler, run=run,
                        profile=profile, threads=1, pair_id='%s/%s/%d' % (profile, program, run),
                        start_order=index, launch_order=len(rows), scored=False,
                        flags=['-O2'] + (['-march=knc'] if compiler == corpus.KNC else [])))
    return rows


def payload(stdout, stderr):
    # Keep all workload output, including lexer fields and rejection diagnostics.
    # Remove only records from the reused timing/affinity supervisor and timers.
    return '\n'.join(s for s in (stdout+'\n'+stderr).splitlines()
                     if not s.startswith(('CORPUS_', 'GENSET_KERNEL ')))


def matches(program, reference, actual):
    left, right = reference.split(), actual.split()
    if not left or len(left) != len(right):
        return False
    exact = program in ('Q2', 'Q4', 'Q6')
    for a, b in zip(left, right):
        if exact:
            if a != b:
                return False
            continue
        try:
            x, y = float(a), float(b)
        except ValueError:
            if a != b:
                return False
        else:
            if not (math.isfinite(x) and math.isfinite(y)):
                return False
            if abs(x-y) > ATOL + RTOL*abs(x):
                return False
    return True


def run(command, directory, log):
    command = list(map(str, command))
    log.write('+ ' + ' '.join(command) + '\n')
    log.flush()
    subprocess.run(command, cwd=directory, stdout=log, stderr=subprocess.STDOUT, check=True)


def includes(program):
    return {
        'Q1': SOURCE / 'raytracing-v4.0.2/src/InOneWeekend',
        'Q2': SOURCE / 'raytracing-v4.0.2/src/InOneWeekend',
        'Q3': SOURCE / 'burkardt-md',
        'Q4': SOURCE / 'lapack-3.12.0/BLAS/SRC',
        'Q5': SOURCE / 'smallpt-2008',
        'Q6': SOURCE / 're2c-3.1/extract/re2c-3.1/examples/c/submatch',
    }[program]


def build(program, directory, cc, cxx, fc, flags, log, native=False):
    directory.mkdir(parents=True, exist_ok=True)
    language = 'c' if program == 'Q6' else 'cpp'
    driver = SUPPORT / (program.lower()+'.'+language)
    objects = []
    if program == 'Q4':
        for name in ('dgemm', 'lsame', 'xerbla'):
            obj = directory / (name+'.o')
            run([fc, *flags, '-c', includes(program)/(name+'.f'), '-o', obj], directory, log)
            objects.append(obj)
    binary = directory / ('workload.exe' if native else 'workload')
    command = [cc if language == 'c' else cxx, *flags,
               '-std=c99' if language == 'c' else '-std=c++11',
               '-I'+str(includes(program)), '-I'+str(SUPPORT), driver, *objects]
    if program == 'Q4':
        library = subprocess.check_output([str(fc), '-print-file-name=libgfortran.a'], text=True).strip()
        command += ['-L'+str(Path(library).parent), '-lgfortran']
    if not native:
        command += corpus.link_paths()
    run([*command, '-lm', '-o', binary], directory, log)
    return binary


def md_reference():
    # Independent scalar oracle from the MD potential and velocity-Verlet equations.
    n, d, dt = 32, 3, 0.001
    p = [[0.125*j+0.0625*i for i in range(d)] for j in range(n)]
    v = [[0.001*(i+j) for i in range(d)] for j in range(n)]
    a = [[0.0]*d for _ in range(n)]
    out = ['Q3 32 3 3']
    for step in range(3):
        forces, potential = [], 0.0
        for j in range(n):
            force = [0.0]*d
            for other in range(n):
                if j == other:
                    continue
                delta = [p[j][i]-p[other][i] for i in range(d)]
                radius = math.sqrt(sum(x*x for x in delta))
                limited = min(radius, math.pi/2)
                potential += 0.5*math.sin(limited)**2
                for i in range(d):
                    force[i] -= delta[i]*math.sin(2*limited)/radius
            forces.append(force)
        kinetic = 0.5*sum(x*x for row in v for x in row)
        out.extend(map(str, (potential, kinetic)))
        out.extend(str(x) for row in forces for x in row)
        for j in range(n):
            for i in range(d):
                p[j][i] += v[j][i]*dt + 0.5*a[j][i]*dt*dt
                v[j][i] += 0.5*dt*(forces[j][i]+a[j][i])
                a[j][i] = forces[j][i]
        for matrix in (p, v, a):
            out.extend(str(x) for row in matrix for x in row)
    return '\n'.join(out)


def host_check():
    """Build O0 references and O2 drivers once; persist frozen reference outputs."""
    host = STAGE / 'host'
    host.mkdir(parents=True, exist_ok=True)
    refs = STAGE / 'oracles'
    refs.mkdir(exist_ok=True)
    checked = {}
    for program in PROGRAMS:
        outputs = []
        for opt in ('-O0', '-O2'):
            folder = host / program / opt[1:]
            folder.mkdir(parents=True, exist_ok=True)
            with (folder/'build.log').open('w') as log:
                binary = build(program, folder, 'gcc', 'g++', 'gfortran', [opt], log, native=True)
            completed = subprocess.run([str(binary)], cwd=folder, capture_output=True, text=True, timeout=60)
            (folder/'stdout').write_text(completed.stdout)
            (folder/'stderr').write_text(completed.stderr)
            if completed.returncode:
                raise RuntimeError('%s %s host driver exit %d; see %s' %
                                   (program,opt,completed.returncode,folder/'stderr'))
            outputs.append(payload(completed.stdout,completed.stderr))
        reference = md_reference() if program == 'Q3' else outputs[0]
        if not matches(program, reference, outputs[0]):
            raise RuntimeError(program+' O0 fails independent oracle')
        (refs/(program+'.txt')).write_text(reference)
        checked[program] = reference, outputs[1]
        print(program+' host drivers built; reference frozen', flush=True)
    return checked


def runtimes(binary, compiler, directory, log):
    # Resolve dependencies using the matching driver, with no provenance sidecars.
    readelf = SHARED/'toolchain/cross/bin/k1om-mpss-linux-readelf'
    system = {'libc.so.6','libm.so.6','libpthread.so.0','libdl.so.2','librt.so.1','ld-linux-k1om.so.2'}
    pending, seen, files = [binary], set(), [binary]
    while pending:
        item = pending.pop()
        text = subprocess.check_output([str(readelf),'-d',str(item)],text=True)
        for name in re.findall(r'\(NEEDED\).*\[(.*?)\]',text):
            if name in seen or name in system:
                continue
            seen.add(name)
            selected = subprocess.check_output([str(corpus.compiler_path(compiler,'g++')),
                                               '-print-file-name='+name],text=True).strip()
            source = Path(selected)
            if selected == name or not source.is_file():
                raise RuntimeError('runtime missing from '+compiler+': '+name)
            target = directory/name
            shutil.copyfile(source,target)
            pending.append(target)
            files.append(target)
    return files


def stage():
    STAGE.mkdir(parents=True,exist_ok=True)
    for program in PROGRAMS:
        if not (STAGE/'oracles'/(program+'.txt')).is_file():
            raise RuntimeError('run the host acceptance test first: missing '+program+' oracle')
    records = []
    for compiler in COMPILERS:
        for program in PROGRAMS:
            folder = STAGE/compiler/program
            folder.mkdir(parents=True,exist_ok=True)
            flags = ['-O2']+(['-march=knc'] if compiler==corpus.KNC else [])
            record = dict(program=program,compiler=compiler,flags=flags,check='error',log=str(folder/'build.log'))
            with (folder/'build.log').open('w') as log:
                try:
                    binary = build(program,folder,*(corpus.compiler_path(compiler,x)
                                   for x in ('gcc','g++','gfortran')),flags,log)
                    run([sys.executable,ROOT/'tools/knc_lint',binary],folder,log)
                    files = runtimes(binary,compiler,folder,log)
                    # Disassemble the actual linked binary for code inspection.
                    with (folder/'workload.dis').open('w') as dis:
                        subprocess.run([str(SHARED/'toolchain/cross/bin/k1om-mpss-linux-objdump'),
                                        '-d',str(binary)],stdout=dis,stderr=log,check=True)
                    record.update(check='ready',files=[corpus.windows_path(f) for f in files])
                except (OSError,subprocess.SubprocessError,RuntimeError) as exc:
                    record['cause'] = str(exc)
                    print(program,compiler,'BUILD FAILURE:',exc,flush=True)
            records.append(record)
            print(program,compiler,record['check'],flush=True)
    with (STAGE/'launcher.log').open('w') as log:
        run([corpus.compiler_path(corpus.DONOR),'-O2',ROOT/'tools/corpus/launch.c',
             *corpus.link_paths(),'-lrt','-pthread','-o',STAGE/'launch'],STAGE,log)
        run([sys.executable,ROOT/'tools/knc_lint',STAGE/'launch'],STAGE,log)
    (STAGE/'builds.json').write_text(json.dumps(records,indent=2))
    (STAGE/'plan.json').write_text(json.dumps(make_plan(),indent=2))
    shutil.copyfile(SUPPORT/'README.md',STAGE/'README.md')
    (STAGE/'lead.ps1').write_text(
        '# Lead only; requires this ticket worktree until merged.\n'
        '& python "'+corpus.windows_path(ROOT/'tools/run.py')+'" --name S12-02-card -- '
        'python "'+corpus.windows_path(ROOT/'tools/genset.py')+'" lead\n')
    print('STAGED %d builds; %d ready; remaining failures recorded in %s' %
          (len(records),sum(r['check']=='ready' for r in records),STAGE/'builds.json'))


def lead():
    """Explicit lead entry point; never called by stage or the host test."""
    if os.name != 'nt':
        raise RuntimeError('lead requires Windows Python for card transport')
    records = json.loads((STAGE/'builds.json').read_text())
    capture = STAGE/'capture'
    capture.mkdir(exist_ok=True)
    out, err = capture/'stdout',capture/'stderr'
    # The resident corpus launcher probes and pins one worker on each profile.
    with (STAGE/'results.jsonl').open('w') as result:
        for job in make_plan():
            build_record = next(b for b in records if all(b[k]==job[k] for k in ('program','compiler','flags')))
            if build_record['check']!='ready':
                row = dict(job,check='error',cause=build_record['cause'])
            else:
                rc = corpus.card_call(STAGE,build_record['files'],job['program'],'serial',out,err,
                                      job['profile'],timeout=60)
                stdout,stderr = out.read_text(errors='replace'),err.read_text(errors='replace')
                reference = (STAGE/'oracles'/(job['program']+'.txt')).read_text()
                checked = matches(job['program'],reference,payload(stdout,stderr))
                # Supply the existing launch parser's success marker only after
                # every materialized live output has passed our frozen oracle.
                validated = stdout+ ('\nCORPUS_CHECK pass\n' if checked else '')
                row = corpus.output_result(job,validated,stderr,rc)
                row['oracle_check'] = checked
                row['kernel_output'] = [s for s in stderr.splitlines() if s.startswith('GENSET_KERNEL ')]
                # Preserve each capture inline; fixed filenames avoid per-run folders.
                row.update(stdout=stdout,stderr=stderr)
            result.write(json.dumps(row,allow_nan=False)+'\n')
            result.flush()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('stage','lead'))
    args = parser.parse_args()
    (stage if args.command=='stage' else lead)()
