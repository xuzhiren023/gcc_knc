"""Host-only zlib PGO staging. Card commands are emitted for the lead, never run.

Run with shared Cygwin Python through tools/run.py: stage, then use TRAIN_STDOUT.
The use step requires the lead's real card profile; missing profiles are fatal.
"""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

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
    stage_peer()
    stage_lead()


def stage_peer():
    peer = corpus.SHARED / 'S11-18' / corpus.DONOR / '0/serial/zlib'
    def peer_mode(member):
        # execl in corpus/launch.c requires the extracted donor to be executable.
        member.mode = 0o755 if member.name == 'workload' else 0o644
        return member
    with tarfile.open(OUT / 'peer.tar', 'w', format=tarfile.USTAR_FORMAT) as archive:
        archive.add(peer / 'workload', arcname='workload', filter=peer_mode)
        for runtime in peer.glob('*.so*'):
            archive.add(runtime, arcname=runtime.name, filter=peer_mode)


def stage_lead():
    write(OUT / 'lead.ps1', r'''# Lead only. Run from this ticket worktree, through tools/run.py.
param([switch]$Evaluate, [ValidateSet('pilot', 'confirm')][string]$Phase = 'pilot')
$ErrorActionPreference = 'Continue'  # Windows PowerShell 5.1 treats native stderr as errors.
$stage = [IO.Path]::GetFullPath("$PSScriptRoot")
if (!$Evaluate) {
    python tools/card_run --timeout 600 --threads 1 --file-list "$stage/train-files.txt" "$stage/train/train.sh" > "$stage/train.stdout" 2> "$stage/train.stderr"
    if ($LASTEXITCODE) { throw 'Training failed; inspect train.stdout and train.stderr' }
    exit 0
}
if (!(Test-Path "$stage/pgo/workload")) { throw 'Run the host use step with train.stdout first' }
foreach ($profile in @('full', '3100', '5100')) {
    $pairs = if ($Phase -eq 'pilot') { 5 } else { 10 }
    for ($pair = 0; $pair -lt $pairs; $pair++) {
        $order = if ($pair % 2) { @('pgo', 'base') } else { @('base', 'pgo') }
        foreach ($variant in $order) {
            $args = @('--benchmark', '--threads', '1', '--timeout', '600')
            if ($profile -ne 'full') { $args += @('--profile', $profile) }
            foreach ($file in @("$stage/$variant/workload", "$stage/input.bin", "$stage/peer.tar")) {
                $args += @('--file', $file)
            }
            python tools/card_run @args "$stage/launch" serial zlib > "$stage/$Phase-$profile-$pair-$variant.stdout" 2> "$stage/$Phase-$profile-$pair-$variant.stderr"
            if ($LASTEXITCODE) { throw "Evaluation failed: $profile $pair $variant" }
        }
    }
}
''')
    print('Lead commands staged in ' + str(OUT / 'lead.ps1'))


def check_launch():
    """Host packaging checks only; never execute a KNC binary or contact card."""
    with tarfile.open(OUT / 'peer.tar') as archive:
        members = archive.getmembers()
        if any(m.pax_headers or not m.isfile() or '/' in m.name for m in members):
            raise ValueError('peer archive must contain plain USTAR files')
        if archive.getmember('workload').mode != 0o755:
            raise ValueError('peer decoder is not executable')
    # Match the launcher's actual shell command, including tar option syntax.
    # The failed pilot already exercised mkdir and tar on the card successfully.
    with tempfile.TemporaryDirectory(dir=OUT) as temp:
        directory = Path(temp)
        shutil.copyfile(OUT / 'peer.tar', directory / 'peer.tar')
        subprocess.run(['sh', '-ec', 'mkdir -p peer && tar -xf peer.tar -C peer; '
                        'test -x peer/workload'], cwd=directory, check=True)
        readelf = corpus.SHARED / 'toolchain/cross/bin/k1om-mpss-linux-readelf'
        sysroot = corpus.SHARED / 'toolchain/sysroot'
        binaries = [OUT / 'launch', OUT / 'base/workload', OUT / 'pgo/workload',
                    directory / 'peer/workload']
        binaries.extend(p for p in (directory / 'peer').glob('*.so*'))
        for binary in binaries:
            headers = subprocess.check_output([str(readelf), '-l', str(binary)], text=True)
            interpreter = re.findall(r'Requesting program interpreter: (.*?)\]', headers)
            for name in interpreter:
                if not (sysroot / name.lstrip('/')).exists():
                    raise ValueError('interpreter missing from card sysroot: ' + name)
            dynamic = subprocess.check_output([str(readelf), '-d', str(binary)], text=True)
            needed = re.findall(r'\(NEEDED\).*\[(.*?)\]', dynamic)
            for name in needed:
                if not any((folder / name).exists() for folder in
                           (binary.parent, sysroot / 'lib64', sysroot / 'usr/lib64')):
                    raise ValueError('unresolved dependency for %s: %s' % (binary.name, name))
            print('%s: interpreter=%s needed=%s' %
                  (binary.name, interpreter, needed), flush=True)
    if (OUT / 'input.bin').read_bytes() != (corpus.SHARED / 'S11-18/input.bin').read_bytes():
        raise ValueError('evaluation input changed')
    if (OUT / 'input.bin').read_bytes() == (OUT / 'train/input.bin').read_bytes():
        raise ValueError('training and evaluation inputs must differ')
    print('Host launch check passed: shell mkdir/tar, executable peer, ELF dependencies; '
          'frozen evaluation input distinct from training. No native execution.')


def use(capture):
    raw = Path(capture).read_bytes()
    text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
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
    for dump in BUILD.glob('*.profile'):
        dump.unlink()
    build('pgo', ['-fprofile-use', '-Werror=missing-profile', '-Werror=coverage-mismatch',
                  '-fdump-ipa-profile-details'])
    dumps = list(BUILD.glob('*.profile'))
    if len(dumps) != len(EXPECTED):
        raise ValueError('expected twelve profile-use dumps, got %d' % len(dumps))
    positive = 0
    for dump in sorted(dumps):
        counts = [int(n) for n in re.findall(r'Read edge from \d+ to \d+, count:\s*(\d+)',
                                            dump.read_text())]
        nonzero = sum(n > 0 for n in counts)
        positive += nonzero
        print('%s: read_edges=%d positive_edges=%d max_count=%d' %
              (dump.name, len(counts), nonzero, max(counts, default=0)), flush=True)
    if not positive:
        raise ValueError('profile-use build has no positive measured edge counts')
    stage_lead()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=['stage', 'use', 'restage', 'check'])
    parser.add_argument('capture', nargs='?')
    args = parser.parse_args()
    if args.step == 'stage':
        stage()
    elif args.step == 'restage':
        # Preserve the trained/use binaries and profiles: only repair packaging.
        stage_peer()
        stage_lead()
    elif args.step == 'check':
        check_launch()
    elif args.capture:
        use(args.capture)
    else:
        parser.error('use requires the lead training stdout path')
