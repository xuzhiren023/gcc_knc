"""Stage S12-12 on the host. Never launch card jobs from this program."""
import argparse
import re
import struct
import subprocess
from pathlib import Path

JOBS = ('g06', 'g04', 'g08', 'g05', 'g07', 'g10')


def read_result(text, job):
    rows = [line for line in text.splitlines() if line.startswith('RESULT ')]
    if len(rows) != 1 or rows[0] not in ('RESULT '+job+' PASS', 'RESULT '+job+' UNAVAILABLE'):
        raise ValueError('missing, ambiguous or failed result for '+job)
    return rows[0].split()[-1]


def decode_samples(data):
    """Decode only the PERF_SAMPLE_IP and PERF_RECORD_LOST layout we requested."""
    pos = samples = lost = 0
    while pos < len(data):
        if len(data)-pos < 8:
            raise ValueError('truncated perf header')
        kind, misc, size = struct.unpack_from('<IHH', data, pos)
        if size < 8 or pos+size > len(data):
            raise ValueError('invalid perf record size')
        if kind == 9:
            if size != 16:
                raise ValueError('unexpected IP sample layout')
            samples += 1
        elif kind == 2:
            if size != 24:
                raise ValueError('unexpected lost record layout')
            lost += struct.unpack_from('<Q', data, pos+16)[0]
        else:
            raise ValueError('unexpected perf record type '+str(kind))
        pos += size
    return samples, lost


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf8', newline='\n') as f:
        f.write(text)


def branch_source():
    lines = ['.text']
    for gap in (0, 64, 1024):
        for offset in (0, 16):
            name = 'branches_%d_%d' % (gap, offset)
            lines += ['.p2align 6', '.rept %d' % offset, 'nop', '.endr',
                      '.globl '+name, '.type '+name+',@function', name+':', 'xorl %eax,%eax']
            for i in range(64):
                label = '.L%s_%d' % (name, i)
                lines += ['testb $1,%d(%%rdi)' % i, 'jz '+label,
                          'incl %eax', label+':', 'jmp '+label+'_next']
                if gap:
                    lines += ['.balign %d' % gap]
                lines += [label+'_next:']
            lines += ['ret', '.size %s,.-%s' % (name, name)]
    lines += ['.section .note.GNU-stack,"",@progbits']
    return '\n'.join(lines)+'\n'


def scripts(out):
    for job in JOBS:
        # Host-side entry point. No direct ssh, reservation, or uncoordinated execution.
        text = '''#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
stage=$(dirname "$here")
root=${KNC_ROOT:-$(dirname "$(dirname "$(dirname "$stage")")")}
profile=${1:-full}
case "$profile" in full|3100|5100) ;; *) echo 'invalid profile' >&2; exit 2;; esac
mode=${2:-timed}
mkdir -p "$stage/results/JOB/$profile"
dest="$stage/results/JOB/$profile"
'''.replace('JOB', job)
        if job == 'g10':
            text += '''case "$mode" in timed) ;; *) exit 2;; esac
for workers in 1 all; do
 for cap in 0 1 8; do
  for touch in 0 1; do
   label="w$workers-cap$cap-touch$touch"
   python3 "$root/tools/card_run" --benchmark --profile "$profile" --threads 240 --timeout 90 "$here/diag.mic" "$cap" "$touch" "$workers" > "$dest/$label.log" 2>&1
   python3 "$stage/src/s12_12_stage.py" summarize G10 "$dest/$label.log"
  done
 done
done
'''
        elif job == 'g06':
            text += '''case "$mode" in
 inventory)
  python3 "$root/tools/card_run" --threads 1 --timeout 45 "$here/diag.mic" inventory > "$dest/inventory.log" 2>&1
  python3 "$stage/src/s12_12_stage.py" summarize G06 "$dest/inventory.log" ;;
 timed)
  python3 "$root/tools/card_run" --benchmark --profile "$profile" --threads 1 --timeout 90 --collect claude-pmu-samples.bin --collect-dir "$dest" "$here/diag.mic" > "$dest/timed.log" 2>&1
  python3 "$stage/src/s12_12_stage.py" summarize G06 "$dest/timed.log" --samples "$dest/claude-pmu-samples.bin" ;;
 *) exit 2;;
esac
'''
        else:
            text += '''[ "$profile" = full ] || { echo 'only G10 needs smaller-card profiles' >&2; exit 2; }
[ "$mode" = timed ] || exit 2
python3 "$root/tools/card_run" --benchmark --profile full --threads 1 --timeout 180 "$here/diag.mic" > "$dest/timed.log" 2>&1
python3 "$stage/src/s12_12_stage.py" summarize JOB "$dest/timed.log"
'''.replace('JOB', job.upper())
        write(out / job / 'run.sh', text)
    write(out / 'batch.sh', '''#!/bin/sh
# Lead only. Full diagnostic batch, optionally add allocator capacity profiles.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
case "${1:-full}" in full|profiles) ;; *) echo 'usage: batch.sh [full|profiles]' >&2; exit 2;; esac
sh "$here/g06/run.sh" full inventory
for job in g06 g04 g08 g05 g07 g10; do sh "$here/$job/run.sh" full timed; done
if [ "${1:-full}" = profiles ]; then
 for profile in 3100 5100; do sh "$here/g10/run.sh" "$profile" timed; done
fi
''')


def stage(jobs):
    import sys
    import corpus
    out = corpus.SHARED / 'S12-12'
    src = corpus.ROOT / 'tools/s12_12'
    for source in src.glob('*'):
        write(out / 'src' / source.name, source.read_text())
    write(out / 'src/s12_12_stage.py', Path(__file__).read_text())
    write(out / 'src/branches.S', branch_source())
    common = [str(corpus.compiler_path(corpus.KNC)), '-O2', '-march=knc', '-std=gnu11',
              '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-pthread']
    for job in jobs:
        folder = out / job
        folder.mkdir(parents=True, exist_ok=True)
        binary = folder / 'diag.mic'
        inputs = [out / 'src' / (job+'.c')]
        if job == 'g07':
            inputs += [out / 'src/branches.S']
        command = [*common, *inputs, *corpus.link_paths(), '-lm', '-ldl', '-lrt', '-o', binary]
        print('+', ' '.join(map(str, command)), flush=True)
        subprocess.run(list(map(str, command)), check=True)
        subprocess.run([sys.executable, str(corpus.ROOT / 'tools/knc_lint'), str(binary)], check=True)
    for job in JOBS:
        if not (out / job / 'diag.mic').is_file():
            raise ValueError('missing staged binary: '+job)
    scripts(out)
    for path in [out / 'batch.sh', *out.glob('g*/run.sh')]:
        subprocess.run(['sh', '-n', str(path)], check=True)
    write(out / 'README.md', (corpus.ROOT / 'docs/research/s12-12-experiments.md').read_text())
    print('STAGED six linked/linted programs; seven shell scripts syntax checked; no card jobs launched')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    build = sub.add_parser('stage')
    build.add_argument('--jobs', nargs='+', choices=JOBS, default=JOBS,
                       help='resume only failed/unbuilt jobs; do not repeat passing builds')
    s = sub.add_parser('summarize')
    s.add_argument('job', choices=[j.upper() for j in JOBS])
    s.add_argument('log', type=Path)
    s.add_argument('--samples', type=Path)
    args = p.parse_args()
    if args.command == 'stage':
        stage(args.jobs)
    else:
        status = read_result(args.log.read_text(), args.job)
        print(args.job, status, 'native correctness only; timings need environment review')
        if args.samples and status == 'PASS':
            samples, lost = decode_samples(args.samples.read_bytes())
            print('PMU samples=%d lost=%d; inspect sampled/baseline time ratio and ~12 expected samples' % (samples, lost))
            if not samples or lost:
                raise ValueError('sampling not qualified')


if __name__ == '__main__':
    main()
