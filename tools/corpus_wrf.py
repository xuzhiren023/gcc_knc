#!/usr/bin/env python3
"""Prepare the frozen M5 WRF case on the host; never launch card jobs."""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import corpus


def local_path(value):
    """Resolve manifest paths under Windows or the project Cygwin."""
    if value.startswith('.work/_shared/'):
        return corpus.SHARED / value[len('.work/_shared/'):]
    if sys.platform == 'cygwin' and re.match(r'^[A-Za-z]:[/\\]', value):
        return Path('/cygdrive/' + value[0].lower() + '/' + value[3:].replace('\\', '/'))
    return Path(value)


def prepare_case(stage):
    """Copy static inputs once per case, retaining the shared classic files.

    The supplied plan also names old binaries and deleted classic inputs.
    Only its static files are copied; the three netCDF paths come from the
    corrected ticket pin. The result is a case file list, not a runnable job.
    """
    pin = corpus.M5_SOURCES['WRF']
    case = stage / 'wrf-case'
    case.mkdir(parents=True, exist_ok=True)
    files = {}
    for name in ('wrfinput_d01', 'wrfinput_d02', 'wrfbdy_d01'):
        record = pin['inputs'][name]
        source = local_path(record['source'])
        with source.open('rb') as stream:
            if stream.read(4) != b'CDF\x02':
                raise ValueError('expected NETCDF3_64BIT_OFFSET: ' + str(source))
        for key in ('script', 'note'):
            if not local_path(record['conversion'][key]).is_file():
                raise FileNotFoundError(record['conversion'][key])
        files[name] = corpus.windows_path(source)

    source = local_path(pin['inputs']['namelist.input']['source'])
    namelist = source.read_text()
    expected = dict(run_hours='25', end_day='7,7', end_hour='13,13',
                    run_days='0', run_minutes='0', run_seconds='0',
                    start_day='6,6', start_hour='12,12', time_step='60',
                    parent_time_step_ratio='1,3', nproc_x='2', nproc_y='4',
                    numtiles_x='5', numtiles_y='3')
    for key, value in expected.items():
        matches = re.findall(r'^\s*' + key + r'\s*=\s*([^!\n]+)', namelist, re.M)
        if len(matches) != 1 or re.sub(r'\s+', '', matches[0]).rstrip(',') != value:
            raise ValueError('frozen WRF namelist changed: ' + key)
    for key, value in pin['inputs']['namelist.input']['edits'].items():
        namelist, count = re.subn(r'(^\s*' + key + r'\s*=)[^\n]*',
                                  lambda m: m[1] + ' ' + value, namelist, flags=re.M)
        if count != 1:
            raise ValueError('ambiguous namelist edit: ' + key)
    destination = case / 'namelist.input'
    destination.write_text(namelist)
    files[destination.name] = corpus.windows_path(destination)

    plan = json.loads(local_path(pin['static_inputs_plan']).read_text())
    for name, record in plan['files'].items():
        if name in files or name in ('wrf.exe', 'real.exe') or name.startswith('lib'):
            continue
        if Path(name).name != name or '/' in name or '\\' in name:
            raise ValueError('unsafe WRF static filename: ' + name)
        source = local_path(record['path'])
        destination = case / name
        shutil.copyfile(source, destination)
        files[name] = corpus.windows_path(destination)
    if 'phiweather-io.txt' not in files:
        raise ValueError('missing namelist iofields input')
    result = dict(program='WRF', input=corpus.INPUTS['WRF'], source=pin,
                  files=files, check='pending-build', layout=pin['layout'],
                  steps=pin['steps'], output_time='2024-01-06_13:00:00',
                  fields=list(corpus.WRF_FIELDS),
                  reference='GCC 5.1.1 unperturbed and THM-1-ULP card runs required')
    corpus.write_json(stage / 'wrf-case.json', result)
    print('WRF fixed-step case prepared: %d files; builds and card checks pending' % len(files))
    return result


def check_openmp_runtime():
    """Fail before an expensive WRF build if its compiler runtime is absent."""
    missing = []
    for compiler in (corpus.DONOR, corpus.KNC):
        # Select this prefix's runtime with the same driver as stage_runtimes.
        driver = corpus.compiler_path(compiler)
        for name in ('libgomp.spec', 'libgomp.so'):
            value = subprocess.check_output([str(driver), '-print-file-name=' + name],
                                            text=True).strip()
            if value == name or not local_path(value).is_file():
                missing.append(compiler + ': ' + name)
            print(compiler + ' ' + name + ': ' + value)
    if missing:
        raise RuntimeError('WRF dm+sm needs compiler OpenMP runtime: ' + ', '.join(missing))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare-case', 'check-runtime'))
    parser.add_argument('--stage', type=Path, default=corpus.SHARED / 'S14-56')
    args = parser.parse_args()
    if args.action == 'prepare-case':
        prepare_case(args.stage.resolve())
    else:
        check_openmp_runtime()


if __name__ == '__main__':
    main()
