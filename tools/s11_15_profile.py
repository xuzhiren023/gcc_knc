"""Stage one existing-perf pilot; never run a card job or rebuild the corpus."""
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT.parent / '_shared' if ROOT.parent.name == '.work' else ROOT / '.work/_shared'
OUT = SHARED / 'S11-15'


def host_path(value):
    if value.startswith('/cygdrive/'):
        return Path(value[10] + ':' + value[11:])
    return Path(value)


def main():
    rows = json.loads((SHARED / 'S11-18/builds.json').read_text())
    matches = [r for r in rows if r['program'] == 'PB-gemm'
               and r['compiler'] == 'gcc-knc' and r['variant'] == 'serial'
               and r['flags'] == ['-O2', '-march=knc'] and r['check'] == 'pass']
    if len(matches) != 1:
        raise RuntimeError('need exactly one successful frozen PB-gemm build')
    OUT.mkdir(exist_ok=True)
    staged = []
    for value in matches[0]['files']:
        source = host_path(value)
        if source.suffix == '.json':
            continue
        dest = OUT / ('gemm' if source.name == 'workload' else source.name)
        shutil.copyfile(source, dest)
        staged.append(dest)
    for source in (SHARED / 'S11-18/launch', ROOT / 'tools/corpus/profile-pilot.sh'):
        dest = OUT / source.name
        shutil.copyfile(source, dest)
        staged.append(dest)
    env = dict(os.environ)
    cyg = SHARED / 'toolchain/cygwin/bin'
    env['PATH'] = str(cyg) + os.pathsep + env['PATH']
    # One syntax check and symbol inspection; S11-18 already linted these binaries.
    subprocess.run([str(cyg / 'bash.exe'), '-n', str(OUT / 'profile-pilot.sh')],
                   env=env, check=True)
    objdump = SHARED / 'toolchain/cross/bin/k1om-mpss-linux-objdump.exe'
    result = subprocess.run([str(objdump), '-t', str(OUT / 'gemm')], env=env,
                            check=True, stdout=subprocess.PIPE, text=True)
    if ' main' not in result.stdout:
        raise RuntimeError('PB-gemm has no main symbol for attribution')
    (OUT / 'symbols.txt').write_text(result.stdout)
    with (OUT / 'gemm.asm').open('w') as output:
        subprocess.run([str(objdump), '-d', str(OUT / 'gemm')], env=env,
                       check=True, stdout=output)
    # Absolute paths make the file list valid from the worktree and after merge.
    (OUT / 'files.txt').write_text(''.join(str(p) + '\n' for p in staged if p.name != 'profile-pilot.sh'))
    quote = lambda p: "'" + str(p).replace("'", "''") + "'"
    project = ROOT.parent.parent if ROOT.parent.name == '.work' else ROOT
    lead = """param([ValidateSet('cpu-clock:u','cycles:u')][string]$Event = 'cpu-clock:u')
$ErrorActionPreference = 'Stop'
"""
    lead += '$entry = ' + quote(ROOT / 'tools/card_run') + '\n'
    lead += 'if (!(Test-Path -LiteralPath $entry)) { $entry = ' + quote(project / 'tools/card_run') + ' }\n'
    lead += '& (Get-Command python.exe).Source $entry --benchmark --threads 240 --timeout 600 --file-list '
    lead += quote(OUT / 'files.txt') + ' ' + quote(OUT / 'profile-pilot.sh') + ' $Event\nexit $LASTEXITCODE\n'
    (OUT / 'lead.ps1').write_text(lead)
    print('STAGED PB-gemm strict -O2, unchanged S11-18 binary and launcher; existing lint reused')
    print('PASS shell syntax; executable symbols and disassembly saved under ' + str(OUT))
    print('NOT RUN: card sampling, attribution, overhead, primary correctness and baseline')


if __name__ == '__main__':
    main()
