"""S11-17 positive controls: host staging only; the lead executes card scripts.

The installed host GCC is 14, whereas KNC is 16: their gcda versions differ.
Use real card profiles rather than translating counters or inventing profiles.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys

import corpus
from s9_18_pgo import parse_gcda

OUT = corpus.SHARED / 'S11-17/controls'
KINDS = ('branch', 'indirect', 'division', 'inline', 'switch')
FLAGS = ['-O2', '-march=knc', '-std=gnu11', '-Wall', '-Wextra', '-Werror']
SOURCE = r'''
#include <stddef.h>
#define CAT_(a,b) a##b
#define CAT(a,b) CAT_(a,b)
#define LOCAL(n) CAT(NAME,n)
static __attribute__((noipa)) unsigned LOCAL(_cold)(unsigned x) { return x * 13u + 5u; }
static __attribute__((noipa)) unsigned LOCAL(_branch_hot)(unsigned x) { return x * 3u + 1u; }
#if KIND == 1
static unsigned LOCAL(_first)(unsigned x) { return x * 3u + 1u; }
static unsigned LOCAL(_second)(unsigned x) { return x * 13u + 5u; }
static unsigned (*volatile LOCAL(_targets)[])(unsigned) = {LOCAL(_first), LOCAL(_second)};
#endif
#if KIND == 3
unsigned LOCAL(_hot)(unsigned x) {
@HOT@
    return x;
}
#endif
#if KIND == 4
#define CASE(N) static __attribute__((noipa)) unsigned LOCAL(CAT(_case,N))(unsigned x) { return x * (3u + N) + N; }
CASE(0) CASE(1) CASE(2) CASE(3) CASE(4) CASE(5) CASE(6) CASE(7)
#endif
unsigned NAME(const unsigned *a, const unsigned *b, unsigned n) {
    unsigned s = 0;
    for (unsigned i = 0; i < n; ++i) {
#if KIND == 0
        if (a[i] == 0) s += LOCAL(_branch_hot)(b[i]);
        else s += LOCAL(_cold)(b[i]);
#elif KIND == 1
        s += LOCAL(_targets)[a[i] != 0](b[i]);
#elif KIND == 2
        s += b[i] / a[i];
#elif KIND == 3
        if (a[i] == 0) s += LOCAL(_hot)(b[i]);
        else s += LOCAL(_cold)(b[i]);
#elif KIND == 4
        switch (a[i]) {
#define ARM(N) case N: s += LOCAL(CAT(_case,N))(b[i]); break;
        ARM(0) ARM(1) ARM(2) ARM(3) ARM(4) ARM(5) ARM(6) ARM(7)
        default: s += LOCAL(_cold)(b[i]); break;
        }
#endif
    }
    return s;
}
'''.replace('@HOT@', '\n'.join('    x = (x ^ (x >> %d)) * %du;' %
                              (3 + i % 13, 1664525 + 2 * i) for i in range(24)))

DRIVER = r'''
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
typedef unsigned (*fn)(const unsigned *, const unsigned *, unsigned);
@DECLS@
static fn variants[] = {@FUNCS@};
static const char *names[] = {@NAMES@};
static unsigned a[65536], b[65536];
static double now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC_RAW, &t)) exit(2);
    return t.tv_sec + 1e-9 * t.tv_nsec;
}
static unsigned reference(unsigned x, unsigned y) {
#if KIND == 2
    return y / x;
#elif KIND == 3
    if (x) return y * 13u + 5u;
@REFHOT@
    return y;
#elif KIND == 4
    return x < 8 ? y * (3u + x) + x : y * 13u + 5u;
#else
    return x ? y * 13u + 5u : y * 3u + 1u;
#endif
}
static unsigned batch(fn f, unsigned reps, double *seconds) {
    unsigned s = 0;
    double start = now();
    for (unsigned r = 0; r < reps; ++r) s += f(a, b, 65536);
    *seconds = now() - start;
    return s;
}
int main(int argc, char **argv) {
    int train = argc == 3 && !strcmp(argv[1], "train");
    int mix = train ? atoi(argv[2]) : 0;
    unsigned ref = 0, state = train ? 29u : 11u;
    cpu_set_t allowed, pin;
    if (sched_getaffinity(0, sizeof allowed, &allowed)) return 2;
    int cpu;
    for (cpu = 0; cpu < CPU_SETSIZE && !CPU_ISSET(cpu, &allowed); ++cpu) {}
    if (cpu == CPU_SETSIZE) return 2;
    CPU_ZERO(&pin); CPU_SET(cpu, &pin);
    if (sched_setaffinity(0, sizeof pin, &pin)) return 2;
    for (unsigned i = 0; i < 65536; ++i) {
        state = state * 1664525u + 1013904223u;
        unsigned rare = (state >> 16) % 100 == 0;
        unsigned other = mix ? !rare : rare;
#if KIND == 2
        a[i] = other ? 11u : 7u;
#elif KIND == 4
        a[i] = other ? 1u + (state >> 24) % 7u : 0u;
#else
        a[i] = other;
#endif
        b[i] = state;
        ref += reference(a[i], b[i]);
    }
    double elapsed;
    unsigned nv = sizeof variants / sizeof variants[0];
    for (unsigned v = 0; v < nv; ++v)
        if (batch(variants[v], 1, &elapsed) != ref) return 3;
    if (train) {
        if (batch(variants[0], 32, &elapsed) != ref * 32u) return 3;
        puts("CONTROL_CHECK pass"); return 0;
    }
    int pairs = argc == 2 && !strcmp(argv[1], "confirm") ? 10 : 5;
    unsigned reps = 1;
    while (batch(variants[0], reps, &elapsed), elapsed < .05 && reps < (1u << 24)) reps *= 2;
    reps = (unsigned)(reps * .2 / elapsed) + 1;
    for (int p = 0; p < pairs; ++p) {
        /* Separate adjacent C/T pairs for matched and inverted; alternate CT/TC. */
        for (unsigned treatment = 1; treatment < nv; ++treatment) {
            for (int slot = 0; slot < 2; ++slot) {
                unsigned v = (slot == (p % 2)) ? 0 : treatment;
                if (batch(variants[v], reps, &elapsed) != ref * reps) return 3;
                printf("CONTROL_TIME @KERNEL@ pair=%d treatment=%s variant=%s seconds=%.9f check=pass\n",
                       p, names[treatment], names[v], elapsed);
            }
        }
    }
    puts("CONTROL_CHECK pass"); return 0;
}
'''.replace('@REFHOT@', '\n'.join('    y = (y ^ (y >> %d)) * %du;' %
                                 (3 + i % 13, 1664525 + 2 * i) for i in range(24)))


def run(args, cwd=OUT):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=cwd, check=True)


def write(path, text):
    # Card /bin/sh requires LF even when staging with Windows Python.
    with path.open('w', encoding='utf8', newline='\n') as output:
        output.write(text)


def compile_kernel(kernel, variant, flags):
    folder = OUT / kernel / variant
    folder.mkdir(parents=True, exist_ok=True)
    write(folder / 'control.c', SOURCE)
    name = kernel + '_' + variant
    common = [corpus.compiler_path(corpus.KNC), *FLAGS, '-Wno-unused-function',
              '-DKIND=' + str(KINDS.index(kernel)), '-DNAME=' + name, *flags, 'control.c']
    run([*common, '-c', '-o', name + '.o'], folder)
    if '-fprofile-generate' not in flags:
        run([*common, '-S', '-o', name + '.s'], folder)
    return folder / (name + '.o')


def link(kernel, variants, objs, output, profile=False):
    names = [kernel + '_' + v for v in variants]
    source = DRIVER.replace('@KERNEL@', kernel).replace('@DECLS@', '\n'.join(
        'extern unsigned %s(const unsigned *, const unsigned *, unsigned);' % n for n in names))
    source = source.replace('@FUNCS@', ', '.join(names)).replace('@NAMES@', ', '.join('"%s"' % v for v in variants))
    driver = OUT / kernel / (output.name + '-driver.c')
    write(driver, source)
    obj = driver.with_suffix('.o')
    run([corpus.compiler_path(corpus.KNC), *FLAGS, '-DKIND=' + str(KINDS.index(kernel)), '-c', driver, '-o', obj])
    run([corpus.compiler_path(corpus.KNC), *FLAGS, *(['-fprofile-generate'] if profile else []),
         obj, *objs, *corpus.link_paths(), '-lrt', '-o', output])
    run([sys.executable, corpus.ROOT / 'tools/knc_lint', output])


def stage(kernels=KINDS):
    OUT.mkdir(parents=True, exist_ok=True)
    binaries, commands = [], []
    for kernel in kernels:
        compile_kernel(kernel, 'base', [])
        for variant, mix in [('pgo', 0), ('pgox', 1)]:
            folder = OUT / kernel / variant
            if folder.exists():
                for profile in folder.glob('*.gcda'):
                    profile.unlink()
            obj = compile_kernel(kernel, variant, ['-fprofile-generate', '-fprofile-update=atomic'])
            binary = OUT / (kernel + '-' + variant + '-train')
            link(kernel, [variant], [obj], binary, profile=True)
    for kernel in KINDS:
        for variant, mix in [('pgo', 0), ('pgox', 1)]:
            binary = OUT / (kernel + '-' + variant + '-train')
            if not binary.is_file():
                raise ValueError('unstaged training binary: ' + str(binary))
            binaries.append(binary)
            commands.append('./%s train %d &\npids="$pids $!"' % (binary.name, mix))
    script = OUT / 'controls-train.sh'
    write(script, '#!/bin/sh\nset -eu\ncd "$(dirname "$0")"\nmkdir gcda\n'
          'export GCOV_PREFIX="$PWD/gcda" GCOV_PREFIX_STRIP=64\npids=""\n' + '\n'.join(commands) +
          '\nstatus=0\nfor pid in $pids; do\n wait "$pid" || status=1\ndone\n'
          '[ "$status" = 0 ] || exit 1\n'
          'for f in gcda/*.gcda; do\n echo "GCDA ${f#gcda/}"\n od -b -v "$f"\n echo END\ndone\n')
    binaries.append(script)
    write(OUT / 'train-files.txt', ''.join(corpus.windows_path(p) + '\n' for p in binaries))
    stage_lead()


def use(capture):
    raw = Path(capture).read_bytes()
    text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
    if text.count('CONTROL_CHECK pass') != 10 or 'profiling error' in text:
        raise ValueError('ten clean training checks required')
    profiles = parse_gcda(text)
    expected = {k + '_' + v + '.gcda' for k in KINDS for v in ('pgo', 'pgox')}
    if set(profiles) != expected:
        raise ValueError('missing/unexpected profiles: ' + str(set(profiles) ^ expected))
    for kernel in KINDS:
        objs = [OUT / kernel / 'base' / (kernel + '_base.o')]
        for variant in ('pgo', 'pgox'):
            name = kernel + '_' + variant
            folder = OUT / kernel / variant
            (folder / (name + '.gcda')).write_bytes(profiles[name + '.gcda'])
            objs.append(compile_kernel(kernel, variant, ['-fprofile-use', '-Werror=missing-profile',
                         '-Werror=coverage-mismatch', '-fdump-ipa-profile-details']))
            dumps = list(folder.glob('*.profile'))
            counts = [int(n) for d in dumps for n in re.findall(r'Read edge from \d+ to \d+, count:\s*(\d+)', d.read_text())]
            if not any(counts):
                raise ValueError('no positive profile counts: ' + name)
            print('%s: positive_edges=%d maximum=%d' % (name, sum(c > 0 for c in counts), max(counts)))
        link(kernel, ['base', 'pgo', 'pgox'], objs, OUT / (kernel + '-time'))
    write(OUT / 'controls-time.sh', '#!/bin/sh\nset -eu\ncd "$(dirname "$0")"\n' +
          '\n'.join('./%s-time "$1"' % k for k in KINDS) + '\n')
    write(OUT / 'time-files.txt', ''.join(corpus.windows_path(OUT / (k + '-time')) + '\n' for k in KINDS) +
          corpus.windows_path(OUT / 'controls-time.sh') + '\n')


def stage_lead():
    write(OUT / 'controls-lead.ps1', r'''# Lead only, from S11-17 worktree, through tools/run.py.
param([ValidateSet('train','pilot','confirm')][string]$Phase = 'train')
$ErrorActionPreference = 'Continue'
$stage = [IO.Path]::GetFullPath($PSScriptRoot)
if ($Phase -eq 'train') {
    python tools/card_run --timeout 180 --threads 1 --file-list "$stage/train-files.txt" "$stage/controls-train.sh" > "$stage/train.stdout" 2> "$stage/train.stderr"
    if ($LASTEXITCODE) { throw 'Control training failed' }
    exit 0
}
foreach ($profile in @('full','3100','5100')) {
    $args = @('--benchmark','--timeout','240','--threads','1','--file-list',"$stage/time-files.txt")
    if ($profile -ne 'full') { $args += @('--profile',$profile) }
    python tools/card_run @args "$stage/controls-time.sh" $Phase > "$stage/$Phase-$profile.stdout" 2> "$stage/$Phase-$profile.stderr"
    if ($LASTEXITCODE) { throw "Control evaluation failed: $Phase $profile" }
}
''')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=['stage', 'use'])
    parser.add_argument('capture', nargs='?')
    parser.add_argument('--kernel', choices=KINDS, help='restage only a changed candidate')
    args = parser.parse_args()
    if args.step == 'stage':
        stage([args.kernel] if args.kernel else KINDS)
    elif args.capture:
        use(args.capture)
    else:
        parser.error('use requires card training stdout')
