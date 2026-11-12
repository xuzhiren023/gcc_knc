"""Host-only zlib PGO staging. Card commands are emitted for the lead, never run.

Run with shared Cygwin Python through tools/run.py: stage, then use TRAIN_STDOUT.
The use step requires the lead's real card profile; missing profiles are fatal.
"""
import argparse
from pathlib import Path
import shutil
import sys
import tarfile

import corpus
from s9_18_pgo import parse_gcda

OUT = corpus.SHARED / 'S11-17'
BUILD = OUT / 'build'
LIB = corpus.SHARED / 'corpus-build/sources/zlib-1.3.1'
UNITS = ('adler32', 'crc32', 'deflate', 'infback', 'inffast', 'inflate',
         'inftrees', 'trees', 'zutil', 'compress', 'uncompr')
EXPECTED = {'workload-' + n + '.gcda' for n in (*UNITS, 'roundtrip')}


def write(path, text):
    path.write_text(text, encoding='utf8')


def build(variant, flags):
    BUILD.mkdir(parents=True, exist_ok=True)
    dest = OUT / variant
    dest.mkdir(exist_ok=True)
    # Match corpus.build_program's complete zlib sources, defines and link flags.
    # Keep output name and directory identical for generate/use profile lookup.
    with (OUT / (variant + '-build.log')).open('w') as log:
        corpus.execute([corpus.compiler_path(corpus.KNC), '-O2', '-march=knc',
                        *flags, '-I' + str(LIB), '-DCORPUS_ZLIB',
                        *[LIB / (n + '.c') for n in UNITS],
                        corpus.SUPPORT / 'roundtrip.c', *corpus.link_paths(),
                        '-lm', '-o', BUILD / 'workload'], BUILD, log)
        corpus.execute([sys.executable, corpus.ROOT / 'tools/knc_lint',
                        BUILD / 'workload'], BUILD, log)
    shutil.copyfile(BUILD / 'workload', dest / 'workload')
    print(variant + ': compiled and linted; not run natively', flush=True)


def stage():
    OUT.mkdir(parents=True, exist_ok=True)
    for profile in BUILD.glob('*.gcda'):
        profile.unlink()
    build('base', [])
    build('train', ['-fprofile-generate', '-fprofile-update=atomic'])
    # Distinct training bytes, same input size and codec level as evaluation.
    state, data = 29, bytearray()
    text = b'PGO development training workload\n'
    for i in range(8 * 1024 * 1024):
        state = (1664525 * state + 1013904223) & 0xffffffff
        data.append(state >> 24 if i % 4096 < 2048 else text[i % len(text)])
    (OUT / 'train/input.bin').write_bytes(data)
    write(OUT / 'train/train.sh', '''#!/bin/sh
set -eu
cd "$(dirname "$0")"
mkdir gcda
export GCOV_PREFIX="$PWD/gcda" GCOV_PREFIX_STRIP=64
./workload
for f in gcda/*.gcda; do
    [ -f "$f" ] || exit 1
    echo "GCDA ${f#gcda/}"
    od -b -v "$f"
    echo END
done
''')
    files = [OUT / 'train' / n for n in ('workload', 'input.bin', 'train.sh')]
    write(OUT / 'train-files.txt', ''.join(corpus.windows_path(p) + '\n' for p in files))
    # Reuse the harness's resident timer and donor decoder without changing them.
    shutil.copyfile(corpus.SHARED / 'S11-18/launch', OUT / 'launch')
    shutil.copyfile(corpus.SHARED / 'S11-18/input.bin', OUT / 'input.bin')
    peer = corpus.SHARED / 'S11-18' / corpus.DONOR / '0/serial/zlib'
    with tarfile.open(OUT / 'peer.tar', 'w') as archive:
        archive.add(peer / 'workload', arcname='workload')
        for runtime in peer.glob('*.so*'):
            archive.add(runtime, arcname=runtime.name)
    write(OUT / 'lead.ps1', r'''# Lead only. Run from this ticket worktree, through tools/run.py.
param([switch]$Evaluate)
$ErrorActionPreference = 'Stop'
$stage = [IO.Path]::GetFullPath("$PSScriptRoot")
if (!$Evaluate) {
    python tools/card_run --timeout 600 --threads 1 --file-list "$stage/train-files.txt" "$stage/train/train.sh" > "$stage/train.stdout" 2> "$stage/train.stderr"
    if ($LASTEXITCODE) { throw 'Training failed; inspect train.stdout and train.stderr' }
    exit 0
}
if (!(Test-Path "$stage/pgo/workload")) { throw 'Run the host use step with train.stdout first' }
foreach ($profile in @('full', '3100', '5100')) {
    for ($pair = 0; $pair -lt 3; $pair++) {
        $order = if ($pair % 2) { @('pgo', 'base') } else { @('base', 'pgo') }
        foreach ($variant in $order) {
            $args = @('--benchmark', '--threads', '1', '--timeout', '600')
            if ($profile -ne 'full') { $args += @('--profile', $profile) }
            foreach ($file in @("$stage/$variant/workload", "$stage/input.bin", "$stage/peer.tar")) {
                $args += @('--file', $file)
            }
            python tools/card_run @args "$stage/launch" serial zlib > "$stage/$profile-$pair-$variant.stdout" 2> "$stage/$profile-$pair-$variant.stderr"
            if ($LASTEXITCODE) { throw "Evaluation failed: $profile $pair $variant" }
        }
    }
}
''')
    print('Lead commands staged in ' + str(OUT / 'lead.ps1'))


def use(capture):
    text = Path(capture).read_text(errors='replace')
    if 'CORPUS_CHECK pass' not in text or 'libgcov profiling error' in text:
        raise ValueError('training did not pass cleanly; inspect card capture')
    profiles = parse_gcda(text)
    if set(profiles) != EXPECTED:
        raise ValueError('profile set mismatch: missing=%s unexpected=%s' %
                         (sorted(EXPECTED - profiles.keys()), sorted(profiles.keys() - EXPECTED)))
    for name, data in profiles.items():
        if data[:4] not in (b'adcg', b'gcda'):
            raise ValueError('invalid profile: ' + name)
        (BUILD / name).write_bytes(data)
    print('Imported %d card profiles' % len(profiles), flush=True)
    build('pgo', ['-fprofile-use', '-Werror=missing-profile', '-Werror=coverage-mismatch'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=['stage', 'use'])
    parser.add_argument('capture', nargs='?')
    args = parser.parse_args()
    if args.step == 'stage':
        stage()
    elif args.capture:
        use(args.capture)
    else:
        parser.error('use requires the lead training stdout path')
