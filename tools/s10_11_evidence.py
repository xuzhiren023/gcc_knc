#!/usr/bin/env python3
"""S10-11 assembly evidence and card staging; run through tools/run.py.

Uses the dispatched lane's installed prefix. Does not run anything on the card.
The cbrt diagnostic deliberately retains the failing build's library flags.
"""
import argparse
import difflib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import knc_vmath as build

BASELINE = 'fe1e143a'
CORES = {
    'vmath_sincos': 'cos_sin_e/cos_sin_e.c',
    'vmath_tan': 'tan_e/tan_e.c',
    'vmath_atan': 'atan_e/atan_e_v2.c',
}

# Generated card job, not a host test. The two builds share the same timed driver
# and inputs. Calls, spills and reconstruction overhead are included in the cost.
BENCHMARK = r'''
#define _GNU_SOURCE
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "knc_vmath.h"
typedef __knc_vmath_v8df vd;
extern vd global___knc_vmath_sin_8(vd);
extern vd global___knc_vmath_cos_8(vd);
extern vd global___knc_vmath_tan_8(vd);
extern vd global___knc_vmath_atan2_8(vd,vd);
static vd input[256], other[256], output[256];
static const char *names[]={"sin","cos","tan","atan2"};
static volatile double sink;
static uint64_t ticks(void) {
  unsigned lo,hi;
  __asm__ volatile("xorl %%eax,%%eax; cpuid; rdtsc"
                   : "=a"(lo),"=d"(hi) : : "rbx","rcx","memory");
  return ((uint64_t)hi<<32)|lo;
}
static __attribute__((noinline)) void batch(int f,int variant,unsigned repeats) {
  for(unsigned r=0;r<repeats;++r) for(unsigned b=0;b<256;++b) {
    vd x=input[b],y=other[b];
    if(variant) switch(f) {
      case 0:output[b]=__knc_vmath_sin_8(x);break;
      case 1:output[b]=__knc_vmath_cos_8(x);break;
      case 2:output[b]=__knc_vmath_tan_8(x);break;
      default:output[b]=__knc_vmath_atan2_8(x,y);break;
    } else switch(f) {
      case 0:output[b]=global___knc_vmath_sin_8(x);break;
      case 1:output[b]=global___knc_vmath_cos_8(x);break;
      case 2:output[b]=global___knc_vmath_tan_8(x);break;
      default:output[b]=global___knc_vmath_atan2_8(x,y);break;
    }
  }
}
int main(int argc,char **argv) {
  unsigned repeats=argc>1?(unsigned)strtoul(argv[1],0,10):32;
  if(!repeats || repeats>4096)return 2;
  cpu_set_t allowed,pin;
  if(sched_getaffinity(0,sizeof allowed,&allowed))return 2;
  int cpu=-1;for(int i=1;i<CPU_SETSIZE;++i)if(CPU_ISSET(i,&allowed)){cpu=i;break;}
  if(cpu<0)return 2;
  CPU_ZERO(&pin);CPU_SET(cpu,&pin);
  if(sched_setaffinity(0,sizeof pin,&pin))return 2;
  printf("S10-11 paired A/B cpu=%d blocks=256 repeats=%u; cycles are serialized TSC ticks\n",cpu,repeats);
  for(int set=0;set<2;++set) {
    for(unsigned b=0;b<256;++b)for(unsigned l=0;l<8;++l) {
      unsigned n=b*8+l;double x=((int)n-1024)*0x1p-11;
      if(set){uint64_t bits=((uint64_t)(1024+n%1022)<<52)|((uint64_t)n<<30);memcpy(&x,&bits,8);if(n&1)x=-x;}
      input[b][l]=x;other[b][l]=((int)((n*53)%2048)-1024)*0x1p-10+0x1p-12;
    }
    for(int f=0;f<4;++f)for(int round=0;round<7;++round) {
      uint64_t elapsed[2];
      for(int order=0;order<2;++order) {
        int variant=order^(round&1);
        batch(f,variant,1);
        uint64_t start=ticks();batch(f,variant,repeats);elapsed[variant]=ticks()-start;
        for(unsigned b=0;b<256;++b)sink=output[b][0];
      }
      printf("%s set=%s round=%d global_off_cycles_per_block=%.3f narrowed_cycles_per_block=%.3f ratio=%.6f\n",
             names[f],set?"large":"polynomial",round,
             (double)elapsed[0]/(256*repeats),(double)elapsed[1]/(256*repeats),
             (double)elapsed[1]/elapsed[0]);
      fflush(stdout);
    }
  }
  return 0;
}
'''


def fma_report(member, variant, lines):
    function = ''
    counts = {}
    for line in lines:
        match = re.search(r'\.type\s+([^,]+),\s*@function', line)
        if match:
            function = match[1]
            counts[function] = 0
        if re.search(r'\bv(?:fmadd|fmsub|fnmadd|fnmsub)', line):
            counts[function] += 1
            print('FMA SITE %s %s %s: %s' % (member, variant, function, line.strip()))
    print('FMA COUNT %s %s total=%d functions=%s' % (member, variant, sum(counts.values()),
          {key: value for key, value in counts.items() if value or key.startswith('compensated_')}))


def stage_benchmark(cc, cross, card, variants):
    # Rename defined globals in all baseline objects, including reducer calls.
    symbols = set()
    for obj in variants['global-off']:
        nm = run(cross / 'k1om-mpss-linux-nm', '-g', '--defined-only', obj,
                 capture_output=True, text=True).stdout
        symbols.update(line.split()[-1] for line in nm.splitlines() if line.split())
    rename = ['--redefine-sym=%s=global_%s' % (s, s) for s in sorted(symbols)]
    for obj in variants['global-off']:
        run(cross / 'k1om-mpss-linux-objcopy', *rename, obj)
    source, asm, obj = (card / ('contraction-bench' + ext) for ext in ('.c', '.s', '.o'))
    source.write_text(BENCHMARK)
    run(*cc, *build.TEST_FLAGS, '-S', source, '-o', asm)
    run(cross / 'k1om-mpss-linux-as', '--march=k1om', asm, '-o', obj)
    elf = card / 'contraction-bench.mic'
    run(*cc, obj, *variants['global-off'], *variants['narrowed'], '-lm', '-o', elf)
    run(sys.executable, build.ROOT / 'tools/knc_lint', elf)
    print('LEAD: python tools/card_run --benchmark --threads 1 --timeout 300 '
          '.work/_shared/S10-11/card/contraction-bench.mic 32')


def cbrt_review(card):
    lines = (card / 'cbrt-original.s').read_text().splitlines()
    function = ''
    for number, line in enumerate(lines, 1):
        match = re.search(r'\.type\s+([^,]+),\s*@function', line)
        if match:
            function = match[1]
        if 'cbrt' in function and (re.search(r'\bcall\b|vgather', line)
                                  or re.search(r'\bvmov(?:ap[sd]|dqa\d*).*\(', line)):
            print('CBRT ASSEMBLY %d %s: %s' % (number, function, line.strip()))
    print('CBRT REVIEW (a): entry -> private core -> cbrt_8, which is a leaf; '
          'no scalar cbrt/cbrtf or self-call and no cycle in this call graph.')
    print('CBRT REVIEW (b): full-width RIP-relative .LC loads have .align 64. '
          'third.0 is only .align 16 but is read with scalar fldl at index rem=exponent%3 (0..2). '
          'The private double core has vmovdqa64 (%rdi); its only callers are the two '
          'by-value cbrt entries, which pass rsp after andq $-64 and addq $-128. '
          'The float core copies caller input with scalar loads. '
          'Output buffers use scalar stores, then entry reloads at aligned rsp+64. '
          'cbrt_8 uses andq $-64 followed by subq $264, with vector offsets 8/72/136/200, '
          'all aligned; private-core rbp slots follow its realignment prologue. '
          'No unaligned full-width table or caller-buffer load identified.')
    print('CBRT REVIEW (c): no vgather instruction in these functions; third.0 uses '
          'a scalar loop over eight lanes, terminating by pointer comparison. '
          'Newton loop decrements eax from 3. No gather-mask loop. '
          'SIGSEGV cause remains pending diagnostic RIP/si_addr from lead; not a native pass.')


def run(*args, **kwargs):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def main():
    if os.name == 'nt':
        # Read Git history with the worktree's Windows Git before entering Cygwin.
        # Windows and Cygwin disagree about the owner of this Windows worktree.
        for member, relative in CORES.items():
            core = build.ALGORITHMS / relative
            baseline = build.SHARED / 'S10-11' / (member + '.baseline-core.c')
            baseline.write_text(subprocess.check_output(
                ['git', 'show', BASELINE + ':' + core.relative_to(build.ROOT).as_posix()], text=True))
        env = os.environ.copy()
        env['PATH'] = str(build.TC / 'cygwin/bin') + os.pathsep + env.get('PATH', '')
        script = subprocess.check_output(
            [str(build.TC / 'cygwin/bin/cygpath.exe'), '-u', str(Path(__file__).resolve())],
            env=env, text=True).strip()
        return subprocess.call([str(build.TC / 'cygwin/bin/python3.12.exe'), script, *sys.argv[1:]], env=env)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage-only', action='store_true', help='reuse completed assembly evidence')
    args = parser.parse_args()
    os.environ['PATH'] = ':'.join(map(str, (build.TC / 'cross/bin', build.TC / 'cygwin/bin'))) + ':' + os.environ['PATH']
    out = build.SHARED / 'S10-11'
    card = out / 'card'
    card.mkdir(parents=True, exist_ok=True)
    prefix, _ = build.prefix()
    cc = [prefix / 'bin/k1om-mpss-linux-gcc', '--sysroot=' + str(build.TC / 'sysroot'), '-march=knc']
    cross = build.TC / 'cross/bin'
    variants = {'global-off': [], 'narrowed': []}
    for member in (() if args.stage_only else ('vmath_sincos', 'vmath_reducer', 'vmath_tan', 'vmath_atan')):
        source = build.LIB / (member + '.c')
        baseline_source = source
        temporary = []
        if member in CORES:
            core = build.ALGORITHMS / CORES[member]
            old_core, old_wrapper = out / (member + '.baseline-core.c'), out / (member + '.baseline.c')
            if not old_core.exists():
                old_core.write_text(subprocess.check_output(
                    ['git', 'show', BASELINE + ':' + core.relative_to(build.ROOT).as_posix()], text=True))
            old_wrapper.write_text(source.read_text().replace(
                '../native/translation/math_algorithms/' + CORES[member], str(old_core)))
            baseline_source = old_wrapper
            temporary = [old_core, old_wrapper]
        assembly = {}
        for variant in ('unprotected', 'global-off', 'narrowed'):
            asm = out / (member + '.' + variant + '.s')
            flags = build.KNC_LIB_FLAGS + (['-ffp-contract=off'] if variant == 'global-off' else [])
            includes = ['-iquote', str((build.ALGORITHMS / CORES[member]).parent)] if member in CORES else []
            run(*cc, *build.LIB_FLAGS, *flags, *includes, '-fverbose-asm', '-S',
                source if variant == 'narrowed' else baseline_source, '-o', asm)
            assembly[variant] = asm.read_text().splitlines()
            fma_report(member, variant, assembly[variant])
            if variant in variants:
                obj = card / (member + '.' + variant + '.o')
                run(cross / 'k1om-mpss-linux-as', '--march=k1om', asm, '-o', obj)
                variants[variant].append(obj)
        print('ASSEMBLY DIFF unprotected -> narrowed: ' + member, flush=True)
        print('\n'.join(difflib.unified_diff(assembly['unprotected'], assembly['narrowed'], n=1)))
        for path in temporary:
            path.unlink()

    if not args.stage_only:
        stage_benchmark(cc, cross, card, variants)
    cbrt_review(card)

    # Keep the original failing diagnostic and its maps intact for the lead's job.
    elf = card / 'cbrt-diagnostic.mic'
    for name in ('qualify_f', 'qualify_d', 'qualify_v1'):
        shutil.copyfile(out / 'knc' / (name + '.mic'), card / (name + '.mic'))
    run(sys.executable, build.ROOT / 'tools/knc_lint', elf, card / 'qualify_v1.mic')
    for function in ('cbrt', 'cbrtf'):
        print('LEAD: python tools/card_run --threads 1 --timeout 60 '
              '.work/_shared/S10-11/card/cbrt-diagnostic.mic ' + function)
    for function in ('sin', 'cos', 'tan', 'atan2', 'cbrt', 'cbrtf'):
        print('LEAD: python tests/vmath/card_qualify.py --out S10-11 --only ' + function)
    return 0


if __name__ == '__main__':
    sys.exit(main())
