"""Stage the authorized development batch; only explicit `lead` starts card jobs."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

from s11_15_profile import ROOT, SHARED, OUT, host_path
from corpus import output_result

# Remaining keys authorized by the lead on 2026-11-14 at 01:39.
# Preserve the nine completed serial pairs; HPCG awaits S11-28 fixed work.
SERIAL = ('zlib', 'SQLite')
OPENMP = ('STREAM', 'NPB-CG', 'NPB-EP', 'NPB-MG', 'NPB-IS')
FROZEN = SHARED / 'S11-18'


def jobs():
    # The public build partition only; explicit allowlist before touching files.
    records = json.loads((FROZEN / 'builds.json').read_text())
    for variant, programs in (('serial', SERIAL), ('openmp', OPENMP)):
        for program in programs:
            matches = [r for r in records if r['program'] == program
                       and r['compiler'] == 'gcc-knc' and r['variant'] == variant]
            if len(matches) != 1:
                raise ValueError('missing/ambiguous frozen build: ' + program)
            row = matches[0]
            flags = ['-O2', '-march=knc'] + (['-fopenmp'] if variant == 'openmp' else [])
            if row['held_out'] or row['check'] != 'pass' or row['flags'] != flags:
                raise ValueError('ineligible frozen build: ' + program)
            yield row


def stage():
    selected = list(jobs())
    OUT.mkdir(exist_ok=True)
    env = dict(os.environ)
    cyg = SHARED / 'toolchain/cygwin/bin'
    cross = SHARED / 'toolchain/cross/bin'
    env['PATH'] = str(cyg) + os.pathsep + env['PATH']
    library = OUT / 'profile-batch.so'
    sysroot = SHARED / 'toolchain/sysroot'
    cc = SHARED / 'gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc.exe'
    subprocess.run([str(cc), '-O2', '-march=knc', '-fPIC', '-shared',
                    '-Wall', '-Wextra', '-Werror',
                    str(ROOT / 'tools/corpus/profile-sigprof.c'), '-lrt',
                    '-Wl,-rpath-link,' + str(sysroot / 'lib64'),
                    '-Wl,-rpath-link,' + str(sysroot / 'usr/lib64'),
                    '-o', str(library)], env=env, check=True)
    subprocess.run([sys.executable, str(ROOT / 'tools/knc_lint'), str(library)],
                   env=env, check=True)
    dynamic = subprocess.check_output([str(cross / 'k1om-mpss-linux-readelf.exe'),
                                      '-d', str(library)], env=env, text=True)
    if set(re.findall(r'\(NEEDED\).*\[(.*?)\]', dynamic)) - {'libc.so.6', 'librt.so.1'}:
        raise ValueError('unexpected sampler runtime dependency')
    shell = OUT / 'profile-batch.sh'
    shutil.copyfile(ROOT / 'tools/corpus/profile-batch.sh', shell)
    subprocess.run([str(cyg / 'bash.exe'), '-n', str(shell)], env=env, check=True)
    # Preserve the primary harness's cross-decoder check. This is not a donor profile.
    records = json.loads((FROZEN / 'builds.json').read_text())
    peers = [r for r in records if r['program'] == 'zlib'
             and r['compiler'] == 'gcc-5.1.1' and r['variant'] == 'serial'
             and r['check'] == 'pass' and not r['held_out']]
    if len(peers) != 1:
        raise ValueError('need the frozen zlib peer decoder')
    with tarfile.open(OUT / 'peer.tar', 'w') as archive:
        for value in peers[0]['files']:
            source = host_path(value)
            if source.suffix == '.json':
                continue
            info = archive.gettarinfo(str(source), arcname=source.name)
            info.mode = 0o755 if source.name == 'workload' else 0o644
            with source.open('rb') as data:
                archive.addfile(info, data)
    for row in selected:
        files = [host_path(p) for p in row['files'] if not p.endswith('.json')]
        files += [FROZEN / 'launch', library]
        if row['program'] == 'zlib':
            files += [FROZEN / 'input.bin', OUT / 'peer.tar']
        elif row['program'] == 'SQLite':
            files += [FROZEN / 'input.sql']
        elif row['program'] == 'HPCG':
            files += [FROZEN / 'hpcg.dat']
        if not all(p.is_file() for p in files) or len({p.name for p in files}) != len(files):
            raise ValueError('missing or colliding staged files: ' + row['program'])
        if sum(p.stat().st_size for p in files) + shell.stat().st_size >= 64 * 1024**2:
            raise ValueError('staging payload exceeds card_run limit')
        key = row['variant'] + '-' + row['program']
        (OUT / (key + '.files.txt')).write_text(''.join(str(p) + '\n' for p in files))
        print('STAGED ' + key + ' plain + sample; existing binary lint reused')
    write_lead_script()
    print('PASS sampler build/lint/dependencies, shell syntax, %d file lists; %d launches staged'
          % (len(selected), 2 * len(selected)))
    print('NOT RUN: native sampler qualification, OpenMP attribution or removable-time ranking')


def write_lead_script():
    quote = lambda p: "'" + str(p).replace("'", "''") + "'"
    project = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
    lead_script = "$ErrorActionPreference = 'Stop'\n"
    lead_script += '$entry = ' + quote(ROOT / 'tools/s11_15_batch.py') + '\n'
    lead_script += 'if (!(Test-Path -LiteralPath $entry)) { $entry = ' + quote(project / 'tools/s11_15_batch.py') + ' }\n'
    lead_script += '& (Get-Command python.exe).Source $entry lead\nexit $LASTEXITCODE\n'
    (OUT / 'lead.ps1').write_text(lead_script)


def restage():
    """Reuse the already built/linted DSO and inputs for the remaining keys."""
    selected = list(jobs())
    for row in selected:
        key = row['variant'] + '-' + row['program']
        paths = (OUT / (key + '.files.txt')).read_text().splitlines()
        if not paths or not all(Path(p).is_file() for p in paths):
            raise ValueError('missing previously staged input: ' + key)
        print('RESTAGED ' + key + ' plain + sample; prior host checks reused')
    if not (OUT / 'profile-batch.sh').is_file():
        raise ValueError('missing previously staged launcher')
    write_lead_script()
    print('PASS remaining batch: %d keys, %d launches; existing captures preserved'
          % (len(selected), 2 * len(selected)))
    print('NOT RUN: card jobs, native qualification or attribution')


def lead():
    if os.name != 'nt':
        raise RuntimeError('lead requires Windows Python')
    capture = OUT / 'batch-capture'
    capture.mkdir(exist_ok=True)
    # Fixed output paths are overwritten; never create per-attempt directories.
    for row in jobs():
        program, variant = row['program'], row['variant']
        key = variant + '-' + program
        plain_arrays = None
        plain_meta = None
        for mode in ('plain', 'sample'):
            stdout = capture / (key + '-' + mode + '.stdout')
            stderr = capture / (key + '-' + mode + '.stderr')
            transport = capture / 'card-result.json'
            command = [sys.executable, str(ROOT / 'tools/card_run'), '--benchmark',
                       '--threads', '240', '--timeout', '600', '--receipt', str(transport),
                       '--file-list', str(OUT / (key + '.files.txt')),
                       str(OUT / 'profile-batch.sh'), program,
                       'one' if variant == 'openmp' else 'serial', mode]
            try:
                with stdout.open('w') as out, stderr.open('w') as err:
                    rc = subprocess.run(command, stdout=out, stderr=err).returncode
            finally:
                transport.unlink(missing_ok=True)
            out_text, err_text = stdout.read_text(), stderr.read_text()
            result = output_result(dict(program=program, threads=60 if variant == 'openmp' else 1),
                                   out_text, err_text, rc)
            if result['check'] != 'pass':
                raise RuntimeError(key + ' ' + mode + ': ' + result.get('cause', 'failed') + '; ' + str(stderr))
            meta = result['affinity']
            if meta['cores'] != 60 or meta['granted_cpus'] != 240:
                raise RuntimeError('not the full 7120 profile')
            if mode == 'plain':
                plain_arrays, plain_meta = result.get('arrays'), meta
            else:
                if meta != plain_meta or result.get('arrays') != plain_arrays:
                    raise RuntimeError('plain/sample affinity or complete live-out mismatch: ' + key)
                if err_text.count('PROFILE_SAMPLER_COMPLETE\n') != 1 or 'PROFILE_BLOCKED' in out_text + err_text:
                    raise RuntimeError('incomplete sampled launch: ' + key)
            print('PROFILE_BATCH_PASS %s %s seconds=%.9f stdout=%s stderr=%s' %
                  (key, mode, result['time_seconds'], stdout, stderr), flush=True)
    print('PROFILE_BATCH_COMPLETE %d launches; host attribution/overhead qualification pending'
          % (2 * (len(SERIAL) + len(OPENMP))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'restage', 'lead'))
    args = parser.parse_args()
    {'stage': stage, 'restage': restage, 'lead': lead}[args.action]()
