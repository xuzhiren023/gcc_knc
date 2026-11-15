# S12-31: why HPCG is slower with GCC-KNC than with GCC 5.1.1

2026-11-15. **Status, phase 2 green:** both changes are in GCC `s12/S12-31` at `299aaf16b72` and the
two T1 tests pass ("Phase 2: green"). The paired HPCG A/B and two controls are staged for the lead;
nothing here has run on the card with the new compiler, so the gain is still the diagnostic's
prediction (about 8% on SpMV and MG, HPCG about 6% above GCC 5.1.1), not a result.

**Status after the second card diagnostic:** the compare
and its jump must issue as one pair, which an x87 instruction between them prevents: that is worth
8% on SpMV and 8% on MG in the pilot's own code, several times the loss. Part of the loss (about 1-2%)
belongs to the process (where the C++ default puts HPCG's coarse arrays), not to generated code.

**Status after the first card diagnostic:** the padding hypothesis below is right in
direction but small: it explains about one eighth of the loss. The same run proves a much larger gain
that is ours to take: the second scheduling pass puts the FP accumulate between `cmp` and `jg`, and
without that the real HPCG kernels are 8.3% (SpMV) and 6.6% (SymGS) faster than the donor's. The other
seven eighths of the pilot's loss is not in the kernels' instructions (same bytes, same data, no loss);
a second staged diagnostic finds where it is. No GCC change yet. Results and decisions are in "First
diagnostic: result" onwards; the sections before it are the phase-1 analysis as written before the run.

## Which kernel loses

S11-28 serial pilot, HPCG's own timers, all 12 launches (`.work/_shared/S11-28/results.jsonl`), seconds:

| Timer | GCC 5.1.1 | GCC-KNC | KNC / donor |
|---|---|---|---|
| DDOT | 2.535-2.540 | 0.962-0.964 | 0.38 |
| WAXPBY | 2.987-2.995 | 0.554-0.561 | 0.19 |
| SpMV | 32.27-32.34 | 32.93-33.08 | 1.021 |
| MG | 201.10-201.61 | 208.86-209.50 | 1.039 |
| Total | 238.91-239.45 | 243.40-244.07 | 1.019 |

The vectorized kernels win; the loss is all in the sparse sweeps (`ComputeSPMV_ref`, and
`ComputeSYMGS_ref`, which is nearly all of MG). Restriction and prolongation are scalar in both and tiny.

## What differs in the code

Same flags as the pilot (`-O2`, plus `-march=knc`), from the installed prefix and the donor, and checked
against the disassembly of the two S11-28 `workload` binaries.

1. The inner loops are the same seven instructions in the same order (index load, `fldl`, `fmull`,
   counter, `cmp`, `faddp`/`fsubrp`, `jg`). Only `addq $1` (ours) against `incq` (donor) differs.
   No spill, no `imul`, no gather, no prefetch, no call in either. S12-07's card run already shows
   `add` against `inc` is neutral: its `nopf` SpMV (our loop, `addq`) and the donor's ran in
   0.025422 s and 0.025423 s.
2. **Loop-head alignment differs, and the padding is executed once per matrix row.**
   `-march=knc` has `-falign-loops=16` (`-Q --help=optimizers`), so loops get `.p2align 4` with no
   limit on the skip (up to 15 bytes). The donor emits `.p2align 4,,7`. The inner loop is entered by
   falling through from the row setup, so the padding runs on every row. The MPSS assembler
   (binutils 2.22.52) fills 9 to 15 bytes with one long NOP carrying `66` and `2e` prefixes, and those
   are slow prefixes on this core: two clocks each (R02 p.56, verified in the source; production or
   pre-production hardware not stated there).

| Padding run per row (S11-28 binaries) | GCC 5.1.1 | GCC-KNC |
|---|---|---|
| SpMV | 2 bytes, `66 90`, 1 slow prefix | 10 bytes at 0x40a026, `66 2e 0f 1f 84..`, 2 slow prefixes |
| SymGS forward sweep | 1 byte `90`, none | 1 byte `90`, none |
| SymGS backward sweep | 1 byte `90`, none | 14 bytes at 0x40a252, five `66` and one `2e`: 6 slow prefixes |

   The size of the loss follows the padding: SymGS (6 extra slow prefixes per two sweeps) loses about
   twice what SpMV (1 extra) loses. (After the card run: the ratio is right, the size is not; see below.)
3. Smaller differences, not expected to matter: our SpMV loop body crosses a 64-byte line (0x40a040);
   the forward SymGS sweep loads two row pointers after the empty-row test instead of before.

Ruled out: heap layout. HPCG allocates all index rows, then all value rows, so both builds read dense
streams with the same number of cache lines whatever the heap phase. (The two builds do differ in
`globalToLocalMap`, `std::map` at the donor's C++98 default and `std::unordered_map` at ours, but it is
not used in the timed kernels.)

## Existing card evidence (inference, not a qualified timing)

S12-07's `sparse-paired` (window 2, cache-resident, 27-entry rows on the short-row path) has the same
pattern. Median seconds, and slow prefixes in the padding run per row (from its disassembly):

| Kernel | donor | knc | nopf |
|---|---|---|---|
| SpMV packed | 0.025423, 0 | 0.025998, 1 | 0.025422, 0 |
| SymGS packed | 0.029288, 1 | 0.030655, 5 | 0.028886, 0 |

Per row executed (65536 in each case): knc minus nopf is 8.8 ns for SpMV and 27.0 ns for SymGS; both
carry the same row-length guard, so the four extra slow prefixes cost about 18 ns, roughly 4.5 ns or
five core clocks each. The donor's one prefix costs SymGS 6.1 ns against nopf. S12-07 read this as a
prefetch-guard effect; the padding explains the SpMV/SymGS difference that the guard cannot. That run's
resource record did not establish exclusive timing, so this is supporting evidence only.

## Staged diagnostic (lead runs it)

`.work/_shared/S12-31/build/s12-31-bench`, built by `tools/s12_31_stage.py` from
`tools/s12_31_bench.cpp`. Lints clean (`knc_lint`). One process, pins itself to the first granted CPU.

```
python tools/card_run --benchmark --profile full --threads 1 --timeout 600 .work/_shared/S12-31/build/s12-31-bench > .work/_shared/S12-31/native.log
```

About 3 minutes and 0.8 GB. Success is exit 0 and a last line `PASS S12-31 diagnostic complete`.

Part 1, the real kernels: HPCG 3.1's own `ComputeSPMV_ref.cpp` and `ComputeSYMGS_ref.cpp` on a 104-cubed
matrix allocated in HPCG's order, five alternating samples, every output compared byte for byte with
the donor's. Each kernel starts at the same address modulo 64 as in the S11-28 binary.

| Variant | Build | Slow prefixes in NOPs (SpMV; SymGS) |
|---|---|---|
| `donor` | GCC 5.1.1 `-O2` | 1; 1 |
| `donor_pf` | same object, NOPs re-encoded without prefixes | 0; 0 |
| `knc` | GCC-KNC `-O2 -march=knc` | 2; 6+6 |
| `knc_pf` | same object, NOPs re-encoded without prefixes | 0; 0 |
| `knc_noalign` | `-fno-align-loops` | 0 executed; 0 |
| `knc_skip7` | `-falign-loops=16:8:8` (the donor's rule) | 1; 1+1 |
| `knc_nosched` | `-fno-schedule-insns2` (S12-07's signal: `cmp` stays next to `jg`) | 2; 6+6 |
| `knc_nosched_noalign` | both | 0 executed; 0 |

`knc_pf` against `knc` is the proof: same code, same layout, only the NOP bytes differ. Expected if the
cause is right: `knc` reproduces the pilot's ratios (about 0.98 SpMV, 0.955 SymGS against `donor`) and
`knc_pf` is at or above the donor. If `knc` does not reproduce the loss here, the cause is outside these
two kernels and the next step is a card profile.

Part 2, a cost table for the fix: one SpMV-shaped row loop (27 products, data in L1) with 0 to 15 bytes
of padding run before the loop, filled three ways (`gas_K` the assembler's NOPs, `one_K` single-byte
NOPs, `pf_K` prefix-free long NOPs); the loop top at other offsets with no padding (`mis_N`, N modulo
64); and two body controls (`inc_0`, `adj_0` with `cmp` next to `jg`). Output is ns per row and the
difference from `gas_0`. The staging tool checks every loop top and padding length in the linked binary.

## First diagnostic: result (card window 3, 2026-11-15 02:57Z, exclusive, exit 0, PASS)

`.work/_shared/S12-31/native.log`. One core, 104-cubed, five alternating samples, every output byte for
byte the donor's. Median seconds (SpMV: two passes; SymGS: one call), and donor time over this time:

| Variant | SpMV | | SymGS | |
|---|---|---|---|---|
| `donor` | 1.24699 | 1.0000 | 1.46385 | 1.0000 |
| `donor_pf` | 1.24695 | 1.0000 | 1.46083 | 1.0021 |
| `knc` | 1.25013 | 0.9975 | 1.47174 | 0.9946 |
| `knc_pf` | 1.24636 | 1.0005 | 1.46447 | 0.9996 |
| `knc_noalign` | 1.23990 | 1.0057 | 1.46103 | 1.0019 |
| `knc_skip7` | 1.24623 | 1.0006 | 1.46205 | 1.0012 |
| `knc_nosched` | 1.15170 | 1.0827 | 1.37308 | 1.0661 |
| `knc_nosched_noalign` | 1.14149 | 1.0924 | 1.35943 | 1.0768 |

Samples of one variant spread about 0.3% (SpMV) and 0.6% (SymGS), so differences under about 0.3% are
not resolved.

Microbench (27 products per row, data in L1; `gas_0` is 393.46 ns per row), ns per row over `gas_0`:

| Padding bytes run per row | 1-8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|
| assembler's NOP (slow prefixes) | 0.7-2.5 (0-1) | 2.3 (1) | 4.1 (2) | 5.6 (3) | 7.6 (4) | 9.0 (5) | 10.5 (6) | 12.0 (7) |
| prefix-free NOPs, same length | 0.6-2.3 | 2.3 | 3.4 | 2.6 | 2.9 | 3.0 | 2.7 | 2.4 |

Loop top at other offsets with no padding (`mis_4` to `mis_60`): within 0.45 ns, except `mis_56` +1.7.
`inc_0`: -0.2. `adj_0` (FP add first, then counter, `cmp`, `jg`): **-44.0 ns per row, 11.2% faster.**

A fault in that binary: its `one_K` series was not single-byte NOPs. The assembler turns
`.p2align 4,0x90` into the same long NOPs, so `one_K` repeated `gas_K` (the two agree within noise,
which is a second sample of the same bytes and nothing more). Fixed in the staging tool.

## What the result means

1. **Padding: confirmed, and small.** Same code and layout, only the NOP bytes changed (`knc_pf` against
   `knc`): 0.30% on SpMV and 0.50% on SymGS, which puts GCC-KNC level with the donor (1.0005, 0.9996).
   The donor's skip limit does the same (`knc_skip7` 1.0006, 1.0012). The cost table agrees: each slow
   prefix after the second costs about 1.5 ns, so the 10-byte NOP costs SpMV about 1.8 ns per row more
   than the donor's 2 bytes (measured 1.4) and the 14-byte NOP costs SymGS about 9.2 (measured 7.0).
   Line crossing and `add` against `inc` cost nothing.
2. **It is not the pilot's loss.** In the pilot (52 SpMV calls, 51 MG applications in the timed set) the
   donor needs 0.6213 s per SpMV pass and GCC-KNC 0.6343 s: 11.6 ns per row. Here the donor needs
   0.6235 s and GCC-KNC 0.6251 s: 1.4 ns per row. MG loses 154 ms per application in the pilot; the
   kernel differences measured here add up to about 20 ms. So the diagnostic reproduces the donor's
   speed and about one eighth of the gap. The kernels are the pilot's: `knc_spmv`/`knc_symgs` and
   `donor_spmv`/`donor_symgs` disassemble identically to `ComputeSPMV_ref`/`ComputeSYMGS_ref` in the two
   S11-28 binaries (only the assert call targets and string addresses differ), at the same address
   modulo 64. **The other seven eighths is therefore not in these instructions as such.** It needs
   something the diagnostic did not have: the pilot process (HPCG's own allocation history: the GCC-KNC
   build uses `std::unordered_map` for the row map and the donor `std::map`; by glibc's rules, not yet
   observed, freeing the map's bucket arrays moves later `mmap` placements and raises the threshold so
   that the coarse-level arrays come from the heap), or the pilot's code addresses beyond modulo 64 (the
   pilot's SpMV row loop is at 0x40a010-0x40a050, the diagnostic's copy elsewhere). Neither is shown to
   matter yet, and I have no mechanism for either: all fine-level arrays are placed alike in both builds
   by that reasoning. My earlier "ruled out: heap layout" was an argument about cache lines, not a
   measurement. The pilot's serial timers are tick-counted CPU time
   (`mytimer.cpp` without `-DWALL`), fine over 240 s; launch-to-exit times agree in direction.
3. **A gain larger than the loss is proven on the real kernels.** With `-fno-schedule-insns2` the only
   change inside the three inner loops is the order: `fmull; faddp; add; cmp; jg` instead of the
   scheduled `fmull; add; cmp; faddp; jg` (checked in the `.s` files; outside the loops only prologue
   stores and a few row-setup instructions move). That is 8.5% faster than today's GCC-KNC on SpMV and
   7.2% on SymGS, memory-bound at 104-cubed, and 11.2% in L1. S12-07 saw the same signal cache-resident;
   it now holds on HPCG's kernels. If the pilot-only loss stays as it is, HPCG's total would go from
   about 243.7 s to about 225 s against the donor's 239.2 s (about 6% faster than GCC 5.1.1). That is a
   prediction from kernel ratios, not a result.

Not S12-30's subject (no gather or prefetch is involved) and not S12-21's (`imul` cost, density): neither
kernel multiplies integers, and S12-21 does not touch the order of compare and jump. No duplication.

## Phase 2 (GCC lane): two general changes

A. **Scheduling: do not separate a compare from its conditional jump with an FP instruction** (keyed on
   that code property; every counted loop with an x87 or vector accumulate has it). The tuning table in
   `docs/research/knc-costs.md` records that compare-and-branch grouping is switched off for KNC in the
   scheduler hook (S6-06). Which rule to write depends on which property of `adj_0` carries the gain,
   and the second diagnostic's microbench separates them: `mid_0` (counter, FP add, `cmp`, `jg`),
   `mov_adj_0` and `mov_split_0` (an integer `mov` before `cmp`, or between `cmp` and `jg`). If `mid_0`
   equals `adj_0`, keeping `cmp` next to its jump is the whole rule; if only `adj_0` is fast, the rule is
   about the FP add following its multiply. T1 red test on the inner-loop order of a sparse dot-product
   loop; strict FP is untouched (order of instructions, not of operations).
B. **Loop padding: bound the skip as the donor does** (`.p2align 4,,7`), so no long slow-prefix NOP is
   run on a fallthrough entry. Worth 0.3-0.5% here; it cannot lose against the donor's rule.
   `-fno-align-loops` was 0.5% better still on SpMV only and is not proposed (unmeasured elsewhere).
   `-falign-jumps=16:11:8` can still place a 9 or 10-byte NOP on a fallthrough path; cap it the same way.

Then T0-T2, ICE sweeps, x86 identity (lead), and the paired HPCG A/B (S11-28 fixed work, two pairs per
profile) with two controls.

## Second diagnostic (staged; lead runs it)

Purpose: find the pilot-only seven eighths, and settle rule A. Built by the same `tools/s12_31_stage.py`;
all four programs lint clean; host logic check passes (the pilot pages execute and give the same bytes
as the build's own kernels). Not run on the card.

`s12-31-layout-<build>` is HPCG 3.1 itself (every source but `main.cpp`), set up in `main.cpp`'s order
up to the first timed call, so the process has the pilot's allocation history; then HPCG's own `CG`
(2 iterations per sample, 3 alternating samples) with the two kernels swapped behind
`ComputeSPMV_ref`/`ComputeSYMGS_ref`, wall-clock timed (CG's SpMV, MG, all SpMV, all SymGS). It prints
where every array is. Builds: `knc` (as the pilot: `-O2 -march=knc`), `donor` (`-O2`), `knc98`
(`-O2 -march=knc -std=gnu++98`, which picks `std::map` like the donor). Each is linked away from
0x400000 and runs five kernel variants:

| Variant | Code |
|---|---|
| `own` | this build's own kernels, where its linker put them |
| `donor_at` | the donor pilot binary's text page, copied to its pilot address (0x406000) |
| `knc_at` | the GCC-KNC pilot binary's two text pages at their pilot addresses (0x409000) |
| `knc_at_pf` | the same with the kernels' slow-prefix NOPs re-encoded |
| `knc_at_adj` | the same with the FP accumulate moved ahead of the counter in the three inner loops |

The pages are bytes of the two S11-28 binaries, which were linted when built; nothing new is encoded
except the two same-length edits named above, both checked by disassembly at staging.

```
python tools/card_run --benchmark --profile full --threads 1 --timeout 600 --file .work/_shared/S12-31/build/runtime-knc/libstdc++.so.6 --file .work/_shared/S12-31/build/runtime-knc/libgcc_s.so.1 .work/_shared/S12-31/build/s12-31-layout-knc > .work/_shared/S12-31/native-layout-knc.log
python tools/card_run --benchmark --profile full --threads 1 --timeout 600 --file .work/_shared/S12-31/build/runtime-donor/libstdc++.so.6 --file .work/_shared/S12-31/build/runtime-donor/libgcc_s.so.1 .work/_shared/S12-31/build/s12-31-layout-donor > .work/_shared/S12-31/native-layout-donor.log
python tools/card_run --benchmark --profile full --threads 1 --timeout 600 .work/_shared/S12-31/build/s12-31-bench 8 5 100000 > .work/_shared/S12-31/native-mb.log
python tools/card_run --benchmark --profile full --threads 1 --timeout 600 --file .work/_shared/S12-31/build/runtime-knc98/libstdc++.so.6 --file .work/_shared/S12-31/build/runtime-knc98/libgcc_s.so.1 .work/_shared/S12-31/build/s12-31-layout-knc98 > .work/_shared/S12-31/native-layout-knc98.log
```

In that order of value. Each layout run: one core, about 3 minutes, about 1 GB; success is exit 0 and a
last line `PASS S12-31 layout diagnostic complete`. The microbench run takes under a minute (its HPCG
part runs on a toy matrix and is to be ignored); last line `PASS S12-31 diagnostic complete`. The
layout programs find `libstdc++.so.6` beside themselves (`$ORIGIN`), where `--file` puts it; each
writes HPCG's small `hpcg*.txt` log into the run directory.

How to read it. The pilot's gap is 2.1% (SpMV) and 3.9% (MG).

| Outcome | Meaning |
|---|---|
| In `knc`, every variant (also `donor_at`) is slower than the same variant in `donor` by about the gap | The loss belongs to the process, not to the kernels' code: data placement from how the program is built. `knc98` level with `donor` then names the row-map type. No kernel code-generation defect beyond A and B. |
| `knc_at` slower than `donor_at` by about the gap inside each process, `own` in `knc` not | The loss belongs to where the pilot linked the code. `knc_at_pf` and `knc_at_adj` show whether B or A removes it there. |
| `knc_at` within 0.5% of `donor_at` everywhere and the processes level | Not reproduced outside the full benchmark run; the remaining step is the ticket's profile of the real binaries. |
| `knc_at_adj` against `knc_at` | Rule A's gain in the pilot's own code, in place (expected near 8% SpMV, 7% SymGS). |

## Second diagnostic: result (card window 5, 2026-11-15 09:17-09:23Z, exclusive, exit 0, PASS)

`.work/_shared/S12-31/native-mb.log`, `native-layout-knc.log`, `native-layout-donor.log`. The fourth
program (`knc98`) was not run. Every output byte for byte the reference.

Microbench (`gas_0` 394.92 ns per 27-product row), ns per row against `gas_0`, and the issue groups
after `fldl` that the model below gives:

| Variant | Order after `fldl` | ns per row | Groups |
|---|---|---|---|
| `gas_0` (today's order) | `fmull; add; cmp; faddp; jg` | 0 | 5 |
| `adj_0` | `fmull; faddp; add; cmp; jg` | -44.8 | 4 |
| `mid_0` | `fmull; add; faddp; cmp; jg` | -45.6 | 4 |
| `mov_adj_0` | `fmull; faddp; add; mov; cmp; jg` | -0.8 | 5 |
| `mov_split_0` | `fmull; faddp; add; cmp; mov; jg` | -1.1 | 5 |
| `inc_0` | today's order with `inc` | +0.1 | 5 |

`mid_0` equals `adj_0`, so where the FP add sits against its multiply does not matter: **the gain is the
compare and the jump issuing together.** One model fits all six: an x87 instruction issues alone; an
integer instruction cannot share an issue with the instruction that produces its input (`add` then
`cmp`, `add` then `mov`); `cmp` and `jg` share one. That is what R02 p.56 says (verified in the source;
production or pre-production hardware not stated there): pairing is for independent single-cycle
instructions, with compare-and-jump among the dependent pairs that the hardware accepts. One issue
group is 44.8 / 27 = 1.66 ns per iteration, which is one issue opportunity of a thread (two core clocks
in `knc.md`'s model). `mov_adj_0` shows that the compare must be the first of its pair: an independent
integer instruction just before it takes it as partner and the jump is alone again. The scheduler's
model (`knc.md`) lets a scalar instruction, the jump included, share an issue with an x87 instruction;
the measurement says the jump cannot. Whether other scalar instructions can, and whether a jump can
share with a vector instruction, is not measured (S12-14 B03's pairing table).

Padding, second sample: the assembler's long NOPs cost +9.5 to +10.8 ns at 13-15 bytes and at most
+2.6 up to 10 bytes; prefix-free NOPs of any length at most +3.3; true single-byte NOPs about 1.5 ns
each (15 of them +22.7).

HPCG itself, set up as the pilot, `CG` 2 iterations, 3 alternating samples, median seconds:

| Kernel code | SpMV, `knc` process | SpMV, `donor` process | MG, `knc` process | MG, `donor` process |
|---|---|---|---|---|
| `donor_at` (donor pilot code at its address) | 1.8791 | 1.8643 | 7.9533 | 7.8601 |
| `knc_at` (GCC-KNC pilot code at its address) | 1.8819 | 1.8712 | 8.0327 | 7.8689 |
| `knc_at_pf` (slow-prefix NOPs re-encoded) | 1.8738 | 1.8637 | 7.9929 | 7.8146 |
| `knc_at_adj` (compare next to jump) | 1.7386 | 1.7223 | 7.4594 | 7.3028 |
| `own` | 1.8830 | 1.8609 | 8.0328 | 7.8601 |

1. **Part of the loss belongs to the process, not to the kernels' code.** The same bytes at the same
   address are slower in the process built by GCC-KNC: `donor_at` by 0.8% (SpMV) and 1.2% (MG), the
   three `knc_at` variants by 0.5-0.9% and 2.1-2.3%. Observed in the same logs: in the `knc` process the
   coarse-level matrices and vectors and the fine level's `rc`/`xc` are on the heap at arbitrary page
   offsets, in the `donor` process nearly all of them are separate mappings (offset 16 in the page).
   That is the placement difference predicted from the row-map type (`__cplusplus` 202002 against
   199711; HPCG picks `std::unordered_map` from C++11 on). It follows from the language default, not
   from generated code. That the map is the cause is still not measured (`knc98` did not run), and why
   that placement is slower is not known. No change is proposed for it.
2. **The pilot's code in place adds little.** `knc_at` against `donor_at` is 0.4% (SpMV) and 0.1%
   (MG) in the `donor` process, 0.1% and 1.0% in the `knc` process; re-encoding the NOPs takes back
   0.4-0.7%. Pilot against pilot (`knc_at` in `knc`, `donor_at` in `donor`) is 0.9% on SpMV and 2.2% on
   MG: about half of the pilot's 2.1% and 3.9%. The rest did not reproduce in 2 iterations.
3. **Rule A in the pilot's own code, in place:** `knc_at_adj` against `knc_at` is 8.2% and 8.6% faster
   on SpMV and 7.7% and 7.8% on MG. Against the donor's pilot (`knc_at_adj` in `knc`, `donor_at` in
   `donor`) HPCG would be 7.2% faster on SpMV and 5.4% on MG, the process loss included. A prediction
   from 2 iterations; the paired A/B decides.

## Phase 2 design (red tests committed; green waits for the lead's approval of the red)

Both changes are KNC only. No FP operation changes order or form.

A. **Keep a scalar compare with its conditional jump in a block that has x87 instructions.**
   `ix86_macro_fusion_p` (`x86-tune-sched.cc`) returns true for `CPU_KNC`, and
   `ix86_macro_fusion_pair_p` hands KNC to a new helper in `i386-knc.cc` (one prototype in
   `i386-knc.h`; the shared file changes by a few lines, in its own commit). The helper is true when
   the second instruction is a conditional jump, the first is a `knc_pipe` scalar instruction that sets
   the flags the jump reads, and the jump's block has an instruction of `knc_pipe` `fp`. The scheduler
   then keeps the two adjacent (`SCHED_GROUP_P`, `sched-deps.cc`), which gives `adj_0` or `mid_0`.
   Blocks without x87 are scheduled exactly as today: S6-06 switched grouping off so that a vector
   instruction could take the compare or the jump as its partner, and nothing measured here says
   otherwise. `pass_dep_fusion` also calls the pair hook, but it never moves a jump. Not done:
   changing `knc.md` so that x87 takes both pipes (wider, and the greedy scheduler would still issue
   the compare first); steering which instruction precedes the compare (`mov_adj_0`).
   T1: `tests/t1/knc-scheduler-cmp-jump.c`.
B. **Bound the loop-head skip at 7 bytes**: `align_loop` in the KNC cost table from `"16"` to
   `"16:8:8"` (`.p2align 4,,7` then `.p2align 3`, the donor's rule; measured as `knc_skip7`).
   Jump alignment stays: `final.cc` uses it only for a block with no fallthrough predecessor, so that
   padding is never run. (My earlier sentence that `-falign-jumps` could put a NOP on a fallthrough
   path was wrong.) `docs/research/knc-costs.md` "Code alignment" says loops are `.p2align 4,,10`;
   they have been unbounded `.p2align 4`, and the green commit corrects that text.
   T1: `tests/t1/knc-tune-align-loops.c`.

Red, on the build of `knc` at 7a3b34430e3 (`python tools/check.py t1 --compiler gcc16
--knc-scheduler --tune-align`, log `.work/_state/logs/check_gcc16_t1-20261115-043150.log`): both new
tests fail on their first scan, for the reason they exist (`fmull; add; cmp; faddp; jg` in the short
loop and `fmull; cmp; faddp; jne` in the unrolled one; `.p2align 4` before the inner loop). The three
existing tests in those selections pass.

Green, then: one GCC build (`tools/gcc_build.py --if-stale` through `tools/run.py`, after committing),
the two selections, full T0-T2, the ICE sweeps (`tools/vect_ice_check.py`, `tools/torture_compile.py`),
the paired HPCG A/B from `tools/hpcg_round.py stage` (S11-28 fixed work, two pairs per profile) and
two controls: one with no x87 in its loops (expected identical code apart from loop padding) and one
x87 loop program. x86 identity is the lead's.

## Phase 2: green (GCC `s12/S12-31` at `299aaf16b72`, five commits on `knc` `7a3b34430e3`)

What was built differs from the design in two places, both found by the first build:

- **B needed one more line.** `ix86_default_align` takes loop alignment from the shared per-processor
  table, not from the KNC cost table, so `"16:8:8"` there changed nothing. `ix86_knc_vectorizer_params`
  (`i386-knc.cc`) already replaces the function alignment for that reason (S8-08) and now replaces the
  loop alignment the same way. An explicit `-falign-loops=` still wins. As for functions, an `optimize`
  attribute or pragma reruns `ix86_default_align` and gets the old unbounded 16 for that function.
- **A is narrower than designed: x87 in the block and no vector instruction.** With "any block that
  has an x87 instruction", preheaders that spill an x87 value beside vector setup
  (`fstps; vbroadcastss; cmp; vpermf32x4; ...; jbe`) had the compare pulled away from the vector
  instruction it paired with (S6-06) to sit before the jump: one issue more, none saved, and no
  measurement behind it. The card result covers blocks of x87 and scalar instructions only, and that is
  now the condition. Blocks with vector instructions, and blocks without x87, are scheduled as before.

Shared i386 code: `x86-tune-sched.cc` only, 5 lines added and 3 removed in 2 hunks (`e3ec6feec45`), both conditions on
`ix86_schedule == CPU_KNC`. `pass_dep_fusion` calls the same pair hook; for KNC the generic answer was
true only for a flag setter and its jump (`fuse_mov_and_alu` is not a generic flag), the pass never
moves a jump (`can_move_insn_p`), and `sched2` clears the group flag before it reads any, so that pass
does the same as before.

Loops of the two T1 functions (`-O2 -march=knc`), as the lead asked. `row_products`, unrolled by 8
(the first seven products each end `fmull; faddp` with loads and pointer updates between them), then
the remainder loop, then the short-count loop; `row_sweep` is the same with `fsubrp`:

```
.L4:    ...                              .L5:                              .L6:
        fldl    (%rsi,%rdi,8)                    movslq  (%r9,%rax,4), %rdx        movslq  (%r9,%rax,4), %rdx
        fmull   -8(%rdx)                         fldl    (%rsi,%rdx,8)             fldl    (%rsi,%rdx,8)
        faddp   %st, %st(1)                      fmull   (%r8,%rax,8)              fmull   (%r8,%rax,8)
        cmpl    %r11d, %ecx                      addq    $1, %rax                  addq    $1, %rax
        jne     .L4                              faddp   %st, %st(1)               faddp   %st, %st(1)
                                                 cmpl    %eax, %r10d               cmpq    %rax, %r10
                                                 jg      .L5                       jne     .L6
```

Before, each had `cmp` one line higher, ahead of the last `faddp`/`fsubrp`. The remainder and
short-count loops are the measured `mid_0` order (counter, accumulate, compare, jump: -45.6 ns per
row). In the unrolled loop an x87 instruction precedes the compare, so no integer instruction takes
it as partner. None of the six is the `mov`-before-`cmp` form. That form does occur outside inner
loops, for example the outer latch of `knc-tune-align-loops.c` (`leaq; leaq; cmpq; jne`): the
scheduler is not told which instruction should precede the compare, so the jump gains nothing there
and loses nothing against before. Each loop head has `.p2align 4,,7` then `.p2align 3`.

All 85 listings of the T1 C sources that compile to assembly, built by `knc` `7a3b34430e3` and by this branch and compared:
`knc-scheduler.s` and 43 others differ only in `.p2align` lines; seven differ in instruction order,
always a compare moved down to its jump in a block of x87 and scalar instructions, with the scalar
instructions around it reordered (`knc-broadcast-load`, `knc-loop-report-rejected`, `knc-perm-loops`, `knc-phinix-nest`,
`knc-vec-fold-fma` and the two new tests); the rest are identical.

HPCG at the pilot's flags, installed compiler against this branch: 13 of 40 listings change beyond
`.p2align`. In `ComputeSPMV_ref` the only change is the inner loop, now
`fldl; fmull; addq; faddp; cmpl; jg`; in `ComputeSYMGS_ref` the two inner loops likewise, and in each
sweep's row block the length load and its `testl` move down to the `jle`. zlib (no floating point): 0
of 12 listings change beyond `.p2align`.

### Staged A/B (lead runs it)

`tools/s12_31_ab.py stage` built `.work/_shared/S12-31/ab`: HPCG serial (S11-28's fixed-work
`hpcg.dat`, 104 cubed), PB-cholesky (x87 inner loops) and zlib (no floating point), each as `before`
(installed GCC-KNC, which is `knc` `7a3b34430e3`, installed 2026-11-15 01:11) and `after` (this
branch's `cc1`/`cc1plus` through the same driver). Both arms are assembled and linked by the installed
driver with its runtimes, so only the generated assembly differs. All six programs lint clean.

```
python tools/s12_31_ab.py lead
```

Windows Python, serial launches through `card_run --benchmark` with S11-28's launcher: two pairs per
profile (full, 3100, 5100), the second pair in the opposite order, HPCG then the two controls. About
13 minutes per HPCG launch (12 launches), about 15 s and 2 s per control launch (12 each): about 2.7
hours in all. A launch that passed is not repeated, so the round can be split over card turns
(`--profile full`, `--program HPCG`); `report` prints the table again. The table gives launch time,
and for HPCG the rating and the SpMV, MG and total timers, per arm and after/before; it also prints the
donor's rating range from the S11-28 pilot. No donor launch is in the round.

What would count: HPCG `after` rating above the donor's 0.0861-0.0863 in every profile (predicted
about 0.091); PB-cholesky `after` not slower than `before` and its arrays the same; zlib within noise.

## What phase 2 would change (written before the first run; superseded by "Phase 2" above)

- Executed loop padding on KNC: stop aligning loop heads that are entered by fallthrough, or bound the
  skip, or emit padding without slow prefixes. Keyed on the padding being on an executed path; it affects
  every program with short inner loops, not only HPCG. `-falign-jumps=16:11:8` can also place a 9 or
  10-byte NOP (1 or 2 slow prefixes) on a fallthrough path.
- Keeping `cmp` next to its jump in the second scheduling pass is a separate possible gain above the
  donor (S12-07 measured 7-11% cache-resident); it belongs with S12-21's scheduling model if Part 1
  confirms it on the real kernels.
- Not S12-30's subject (no gather or prefetch is involved) and not S12-21's `imul` cost (neither kernel
  multiplies integers).

## What ran

- `python tools/run.py --name s12_31_host ... tools/s12_31_stage.py --host`: driver logic on the host
  with the Cygwin compiler (not KNC code): pass. Log `.work/_state/logs/s12_31_host-20261114-210905.log`.
- `python tools/run.py --name s12_31_stage ... tools/s12_31_stage.py`: 16 kernel objects, 65
  microbench loops, link, layout checks, `knc_lint`: pass. Log
  `.work/_state/logs/s12_31_stage-20261114-211046.log`.
- No card job, no GCC build, no T1 test yet (phase 2). x86 not run. No held-out program built or read.

2026-11-15, after the lead's card run of the first diagnostic:

- Kernel identity against the pilot binaries: cross `objdump` of `ComputeSPMV_ref`/`ComputeSYMGS_ref`
  in both S11-28 `workload` files against the diagnostic's `knc_*`/`donor_*`: same instructions at the
  same offsets, apart from assert call targets and string addresses.
- `python tools/run.py --name s12_31_host ... tools/s12_31_stage.py --host`: pass; both drivers on the
  host, pilot pages executed (relocated), all five variants byte-identical. Log
  `.work/_state/logs/s12_31_host-20261115-000912.log`.
- `python tools/run.py --name s12_31_stage ... tools/s12_31_stage.py`: pass; first diagnostic rebuilt
  with true single-byte `one_K` and three order variants, three layout binaries with their runtimes,
  four pilot page images checked, layout checks, `knc_lint` on all four programs. Log
  `.work/_state/logs/s12_31_stage-20261115-000419.log`.
- No card job by me, no GCC build, no T1 test (phase 2). x86 not run. No held-out program built or read.

2026-11-15, phase 2 green (GCC `s12/S12-31` at `299aaf16b72`, built by `tools/gcc_build.py --if-stale`,
log `.work/_state/logs/s12_31_gcc_build-20261115-050001.log`):

- `python tools/check.py t1 --compiler gcc16 --knc-scheduler --tune-align`: 5 of 5 pass, the two new
  tests among them. Log `.work/_state/logs/check_gcc16_t1-20261115-050204.log`. The first green build
  passed `knc-scheduler-cmp-jump.c` and still failed `knc-tune-align-loops.c` (the cost-table string
  alone does not reach `-falign-loops`); fixed in `149e5ee8197`.
- `python tools/check.py t0 t1 t2 --compiler gcc16`: 371 pass, 0 fail. Log
  `.work/_state/logs/check_gcc16_t0_t1_t2-20261115-050259.log`.
- `python tools/torture_compile.py` (2003 files, four levels): 0 ICE; pass 1968/1969/1969/1969,
  compiler error 33/32/32/32, user inline asm rejected 2 at each level, as in S12-32's sweep. Summary
  `.work/_shared/S12-31/torture.txt`, log `.work/_state/logs/s12_31_torture-20261115-051713.log`.
- `python tools/vect_suite.py`: 0 ICE, 23 compile errors, 632 skipped, as in S12-32's sweep. Log
  `.work/_state/logs/s12_31_vect-20261115-053357.log`.
- `tools/s12_31_ab.py stage`: pass, six programs built and linted. Log
  `.work/_state/logs/s12_31_ab_stage-20261115-051303.log`. Its `report` step was tried on the host
  with the S11-28 captures standing in for the two arms (it reproduces the pilot's 0.981-0.983).
- No card job by me: the new compiler's code has not run on the card. x86 not run. No held-out program
  built or read.
