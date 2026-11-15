# S12-31: why HPCG is slower with GCC-KNC than with GCC 5.1.1

2026-11-14, phase 1. **Status: cause identified statically, not yet proven on the card.** One staged
single-core diagnostic (about 3 minutes) decides it. No GCC change yet.

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
   twice what SpMV (1 extra) loses.
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

## What phase 2 would change (to be chosen from the result)

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
