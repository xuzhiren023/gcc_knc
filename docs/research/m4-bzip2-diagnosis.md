# M4 bzip2 regression: diagnosis (held out, lead-authorized)

2026-11-16, Claude subagent for the lead, host only (ADR-0015 "Held-out access"); nothing on
the card. S13-01 (7120 full, six AB/BA pairs, serial): GCC-KNC 0.927x of GCC 5.1.1, means 67.60
vs 62.22 s, gap 5.38 s = 6.66 G cycles at 1.238 GHz; all launches passed.
## Workload and where time goes

`tools/corpus/roundtrip.c`: `BZ2_bzBuffToBuffCompress` of 8 MiB at level 9, workFactor 30, then
`BZ2_bzBuffToBuffDecompress`. The input (`tools/corpus.py:564-570`) is, per 4096 bytes, 1024 LCG
bytes then 3072 bytes of a periodic 27-byte text. Every 900 KB block is "too repetitive": host
bzip2 1.0.8 `-9 -vvvv` on the same bytes exhausts mainSort's budget (9 x nblock mainGtU loop
iterations) and falls back to fallbackSort in all 10 blocks (13 doubling rounds, to depth 4096).

Counts from an instrumented host (x86, gcc 14) copy of the same sources and input; the
algorithm is deterministic, so the counts hold for the card:

| item | count |
|---|---|
| mainGtU calls / past the 12-byte preamble | 1,854,575 / 529,714 |
| mainGtU inner-loop iterations (8 bytes + 8 quadrant words each) | 75,502,409 |
| fallbackQSort3 key compares / key sets / bucket scans | 167.2 M / 109.1 M / 71.2 M |
| host time shares (x86, not KNC) | mainSort 25.6%, fallbackSort 49.6%, MTF 6.5%, sendMTF 0.8%, decompress 15.5% |

## Cause (main): scalar values allocated to mask register k0 in mainGtU

GCC-KNC's mainGtU inner loop (`workload` 0x402241-0x4023f2) keeps `c1` in `k0`. Each of the
8 byte steps is `lea; movzbl (%rdx,%rcx),%eax; kmov %eax,%k0; lea; movzbl ...,%r11d;
kmov %k0,%ebx; cmp %r11b,%bl; jne; movw; movw; cmp; jne` (12 instructions). The donor's loop
(0x400cef-0x400e1a, `mainGtU.part.0`) is `lea; lea; mov (..),%bl; cmp %bl,(..); jne; movw;
cmpw (..); jne` (8). Per iteration: 107.3 vs 73.1 instructions, 16 of them `kmov`.

Why: `knc_processor_costs` (`gcc/config/i386/i386-knc.cc:158,160`, "CH kmov.rt: half cycle per
core") prices mask<->GPR moves at 1, below a GPR-GPR move (2) and a stack spill (store 2 + load
2); generic tuning prices them at 6. The allocator therefore treats k0 as a free spill slot
instead of using a callee-saved GPR. `kmov.rt` was measured equal to `scalar_add.rt`
(knc-characterization.md:106), so a kmov is one full issue, and the round trip replaces zero
instructions. Freeing `eax` through k0 also makes the scheduler reuse it as the next index, so
each `lea` sits directly before its load (address-generation interlock).

Proof that it is the cost table, not the source: the same `blocksort.c` compiled by the same
GCC-KNC with `-O2 -march=knc -mtune=generic` has no `kmov` in mainGtU (201 -> 184
instructions) and groups both `lea`s before the loads.

knc-twin 0.3.1, `card-7120-measured`, `from_binary.py` on the staged binaries; one mainGtU call
on the real block bytes (i1=1051, i2=1024: 3045 equal bytes, 379 iterations), quadrant zero;
functional check ok (budget decremented exactly 379). `unvalidated_scenario_estimate`.

| variant | instr/iter | cycles/iter, L1 | cycles/iter, cold memory | limiting constraints (cycles) |
|---|---|---|---|---|
| donor binary (`mainGtU.part.0`) | 73.1 | 114.1 | 131.1 | spacing 15936, dependency 6068, agi 3035 |
| GCC-KNC binary (`mainGtU`) | 107.3 | 180.5 | 197.4 | spacing 25844, dependency 9114, agi 6079 |
| GCC-KNC, kmov pair replaced by a GPR (edited records, what-if) | 91.3 | 156.5 | - | spacing 22810, dependency 6081, agi 6079 |
| GCC-KNC `-mtune=generic` compile (no kmov, leas grouped) | 91.3 | 148.4 | - | spacing 22810, dependency 6080, agi 3044 |

The `.s` compiles reproduce the binaries exactly (180.47 / 114.12), so the staged code is what
this compiler emits today. Roll-up: 66.3 extra cycles x 75.50 M iterations = 5.01 G cycles =
4.04 s, about 75% of the measured 5.38 s. The cold-memory scenario gives the same 66.3.

## Cause (second, GCC 16 general): compare operands not folded

Even without kmov (148.4 vs 114.1 cycles/iter), GCC 16 loads both operands of every compare
(`movzbl`/`movw` twice, `cmp reg,reg`) where GCC 5.1.1 folds one load into the `cmp`. GCC 16
merges the 28 early returns into blocks that recompute `c1 > c2` from registers (0x402165
`cmp %al,%cl; setb`, 0x4023fc, 0x402407); GCC 5.1.1 jumps to a `seta` that reuses the flags of
the compare (0x400df9). Two extra instructions per byte step, and three 0x66-prefixed
instructions per quadrant step instead of two. Same output with `-mtune=generic`, so not KNC
tuning. This is about 34 of the 66 cycles per iteration.

## fallbackSort, decompression, MTF

fallbackSort (inlined fallbackQSort3) is larger in GCC-KNC (917 vs 638 instructions): `ftab`
and `bhtab` clearing become memset/memcpy calls, and `fvswap` is vectorized with a masked
gather/scatter tail (`vpscatterdd` at 0x401bf5 and 0x401d75; scatter occupancy is an unmeasured twin
parameter, so both runs used a scratch overlay at 7 cycles/line, like gather). Twin on the
whole function, first 4096 input bytes (one random+text period, 13 rounds), output checked
against a Python sort of the cyclic rotations (ok): GCC-KNC 3.69 M cycles / 2.44 M instructions,
donor 3.89 M / 2.36 M. GCC-KNC is about 5% faster there: not a cause. That run is L1-resident;
the real 3.6 MB `eclass` is random-access and memory-bound, which shrinks code differences.
generateMTFValues' inner loop is 6 instructions in both. Decompression was not simulated.
The remaining ~25% of the gap is not attributed.

## Checked and ruled out

- Alignment / S12-31: mainGtU loop heads unaligned in both (0x402241, 0x400cef), no padding
  NOPs in the hot loops, cmp/jcc adjacent in both; the twin charges nothing for loop-head offset.
- imul (S12-21): none in hot loops; one `imul $-4` before the inverse-MTF shift in
  BZ2_decompress (0x40b0e0), once per symbol.
- Inlining: no partial inlining of mainGtU in GCC 16 (donor inlines checks 1-11 into
  mainSimpleSort); 1.32 M early-resolving calls, about 20 M cycles (<0.02 s).
- Same k0 spill in BZ2_decompress (`uc` across the MTF shift, 0x40972e, 0x40b0d3/0x40b139),
  once per symbol: small.

## How sure

High that the kmov allocation and the unfolded compares in mainGtU are the main cause
(direct listing, reproducible compile, twin with exact functional check, roll-up at about 75%
of the measured gap). The absolute cycle numbers are unvalidated for integer code; the
remaining ~25% is not attributed with confidence (see fallbackSort above).

## Smallest general fix (no program-specific tuning)

1. KNC port, one cost change: raise `mask_to_integer` and `integer_to_mask` in
   `knc_processor_costs` to at least a stack spill (store + load = 4; generic's 6 is the safe
   choice), so the allocator never prefers mask registers for scalar QI/HI/SI values. Expected:
   mainGtU 180 -> about 148-156 cycles/iter, about 1.5-2.0 s of the 5.4 s; also removes the
   decompress k0 spill. Check that vector mask code (`knc-masks.md`) keeps its allocation, and
   scan the M4 binaries for `kmov %k*,%e*` round trips before and after.
2. Follow-up (M5 ticket, investigation first): why GCC 16 recomputes the compare in the merged
   return block instead of reusing flags, which blocks load folding. Generic GCC behaviour,
   larger change; worth about 34 cycles/iter here and likely helps any compare-and-return chain.

## Exposure record

Read: `.work/_shared/m4-sealed/S13-01/results.jsonl` (the 12 bzip2 rows: times, checks),
`initial-full-capture/038.stdout` (one bzip2 capture), `build/{gcc-knc,gcc-5.1.1}/0/serial/bzip2/`
(`build.log`, `workload` disassembled), `gcc-knc/0/serial/bzip2/runtime-prefix.json`, one bzip2
row of `plan.json` (transport record) shown by a grep; file names only of `builds.json`,
`extension-plan.json`, `score.json`. Also `.work/_shared/S13-01/input.bin` (bytes; generator is
public in `tools/corpus.py`), `.work/S13-01/tools/corpus/{roundtrip.c,README.md,gate-readme.md}`.
No other program's rows or the score were read.
