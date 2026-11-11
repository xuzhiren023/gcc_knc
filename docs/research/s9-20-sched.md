# S9-20: instruction scheduling on the in-order KNC core (dumps and predictions; card numbers pending)

Sources `tests/bench/sched/sched.c` (two scalar kernels and the paired driver) and the M2 kernels
`tests/acceptance/m2_kernels/kernels.c`; tool `tools/s9_20_sched.py`; installed
`gcc-knc-16.2.0` (as S9-19). Full report: `.work/_shared/S9-20/report.txt`.

## 1. What `-O2 -march=knc` does today (`-Q --help=optimizers`, sched dumps)

- First pass (`-fschedule-insns`, before register allocation): **off** (i386 default; `-march=knc`
  does not change it). `-fsched-pressure` off.
- Second pass (`-fschedule-insns2`, after reload): **on**, with `-fsched-interblock` and
  `-fsched-spec`; `-fsched2-use-superblocks` off. `-mtune=knc`.
- `knc.md` **is used**: the sched2 dump of `x87poly_base` (`-fsched-verbose=4`) prints every
  scheduled insn with a `knc.md` unit reservation, e.g. `i 22 flags=cmp(cx,0x1) :knc-u|knc-v`;
  with `-fschedule-insns` the sched1 dump shows the same automaton, e.g.
  `i 133 r144=[r141*0x8+r291] :(knc-u+knc-fp)` (an x87 load: U pipe plus the FP unit).
- `--param knc-threads-per-core` defaults to 4.

## 2. Variants and hot-loop spills

`base` `-O2 -march=knc`; `nosched` `-fno-schedule-insns -fno-schedule-insns2`; `pre`
`-fschedule-insns`; `prepress` `-fschedule-insns -fsched-pressure`; `prepress1` the same with
`--param knc-threads-per-core=1`. M2 kernels with the M2 `gcc` build flags (`-ffp-contract=fast
-ftree-vectorize`); scalar kernels with vectorization off. `short` is left out (it is affine_f32
in short calls).

- `ichain`: a serial multiply chain `h = (h ^ a[i]) * K` through every element, plus an independent
  `g += b[i]*a[i+1]` chain; four elements per trip in source order (the KNC unroller doubles it).
- `x87poly`: two independent cubic Horner chains per trip (elements i, i+1) on x87, a store each,
  and one serial running sum. Quarter-integer data, so all values are exact and a spill cannot
  change a result.

Hot loops = instructions inside any backward branch's range (main and remainder loops together).
Instructions / stack loads / stack stores:

| kernel | base | nosched | pre | prepress | prepress1 |
|---|---|---|---|---|---|
| affine_f32 | 77/4/0 | 77/4/0 | 77/4/0 | 77/4/0 | 125/4/0 |
| affine_f64 | 84/4/1 | 84/4/1 | 83/4/1 | 83/4/1 | 126/4/0 |
| stencil1 | 319/0/1 | 319/0/1 | 321/0/1 | 321/0/1 | 320/0/1 |
| stencil2 | 109/2/1 | 109/2/1 | 106/1/0 | 106/1/0 | 106/1/0 |
| mat8 | 39/0/0 | 39/0/0 | 39/0/0 | 39/0/0 | 39/0/0 |
| mat16 | 85/0/0 | 85/0/0 | 85/0/0 | 85/0/0 | 85/0/0 |
| ichain | 142/5/0 | 142/5/0 | 141/7/0 | 139/4/0 | 140/6/0 |
| x87poly | 177/0/0 | 177/0/0 | **243/34/0** | 186/0/0 | 178/2/0 |

Plain `-fschedule-insns` on x87 code is the one bad case: it interleaves the two Horner chains,
the eight-register stack overflows, and the four coefficients are reloaded from the stack
(34 loads, plus `fxch` traffic). `-fsched-pressure` removes that. `prepress1` grows the affine
loops (10 FMAs instead of 4: more unroll and chains, from the param, not the scheduler).

## 3. Card runner (lead only)

`card_run --benchmark --timeout 3600 --file-list .work/_shared/S9-20/sched-files.txt
.work/_shared/S9-20/sched.sh` (optional argument: rounds, default 21). One binary `sched.mic` holds
every kernel in all five variants. Passes: M2 at L2 on every whole allowed core except the OS core
(at most 60) at 1 thread per core (16384 outputs per worker) and 4 (4096 per worker); then the
scalar kernels on one core, 1 pinned thread and 4 copies (one per sibling). Per kernel and round
the five variants run in a seeded shuffled order (ADR-0010 pairing): a checked untimed call on all
workers, then a ~100 ms batch from start barrier to end barrier. `SUMMARY ratio_median` is
ms(variant)/ms(base) within the round. Every worker's output is compared bytewise with the base
variant's at the start and in every round (`CHECK`, `MISMATCH`, `RESULT ok`). Host x86 build of
the scalar kernels: all variants give the same output
(`.work/_state/logs/s9_20_host-20261110-195744.log`); KNC outputs are checked by the runner.

## 4. Predictions from the assembly

| kernel | nosched vs base | pre / prepress vs base | prepress1 vs base |
|---|---|---|---|
| affine_f32, affine_f64 | no change (sched2 only moves address increments) | no change (same loop, same spills) | 1 tpc: more overlap, faster; 4 tpc: no change |
| stencil1 | no change | no change | no change |
| stencil2 | no change | fewer spills (one reload, one store fewer in the row loop): small gain at 1 tpc | as pre |
| mat8, mat16 | no change: the loop is a gather plus a dependent masked FMA chain through one register; sched2 only moves an `addq` between `vblendmps` and `vfmadd231ps` | no change | no change |
| ichain | no change (bound by the serial `imul` chain) | no change; pre has two more spill reloads | no change |
| x87poly | no change (sched2 keeps the two Horner chains one after the other; it only moves prefetches and address updates between FP ops) | pre: more overlap but 34 coefficient reloads and extra `fxch`, slower or no change; prepress: more overlap, no spills, faster at 1 tpc, little at 4 | as prepress |

On mat8's 10% loss after S6-06: with today's compiler the mat8 loop of `base` and `nosched` differ
by one moved `addq` (and the mask setup before the loop). A `nosched` gain for mat8 on the card
would point at that; no gain would mean the S6-06 loss is no longer the scheduler's.
