# S12-42: knc-twin diagnosis of the 32-row SpMV losses to GCC 5.1.1 (host only, 2026-11-15)

Twin knc-twin 0.3.0 (`.work/twin-0.3/knc-twin`), profile `card-7120-measured`, hash `2058f0ec2d80...`, frozen for
every run. One context, steady state: per-call cycles = slope between 2 and 3 calls (as `tests/heldout_native/s12-30-small`).
Card figures are window 8 (`.work/_shared/tmp/claude-s12-window8/s12-30-gate-hpcg.out`, five-sample medians).

## Inputs and commands

- Builds: donor-off = `S12-30/compiler-donor.o`, knc-switch-off = `compiler-knc.o`, knc-switch-off-two-nests =
  `compiler-twin.o` (the mapping in the gate's `PROOF_SLOTS` and the twin's `make_s12_30_cases.py`). Timed entry
  `<p>_csr_scalar` / `<p>_hpcg_scalar` with callee `<p>_raw`.
- Today's prefix (`.work/_shared/gcc-knc-16.2.0`; the brief says knc b2ce6a9eebf, `gcc -v` does not show a hash), one
  compile, the gate's switch-off flags (the prefix has no `-m[no-]knc-indirect-prefetch`, so that flag was dropped):
  `k1om-mpss-linux-gcc -O2 -std=gnu99 -ffp-contract=off -DLEGAL_PROOF -DCOMPILER_PROOF -DPREFIX=today_ -march=knc
  --sysroot=.../toolchain/sysroot -S s12_30_precision.c` (source `git show s12/S12-30:tools/s12_30_precision.c`), then
  `k1om-mpss-linux-as --march=k1om`. No two-nest (`-DTWIN_PROOF=1`) compile was made: the brief allowed one compile.
- `knc_twin.py capabilities`; `k1om-mpss-linux-objdump -dr` of each object; kernels from
  `make_s12_30_cases.make_kernel` (which calls `from_binary.Converter`, so layout, NOP bytes and prefixes are real);
  `knc_twin.py simulate K --profile card-7120-measured` for 2 and 3 calls; `knc_twin.py batch` on csr13 (10 variants).
- Input: the gate's `compiler_case` generator (LCG 1664525/1013904223, x in [-4,4], values in [-3,3], 4096 x entries =
  32 KiB, shuffled 64-byte row allocations for HPCG-pointers), seed 1. The card's generator state cannot be reproduced
  (it depends on all the guard runs before it). Seeds 2 and 3 move absolute cycles by up to 4% but leave every
  build-to-build difference unchanged to within 1 cycle per call. Expected outputs come from exact integer arithmetic;
  functional check `ok` on every run.
- Scratch (not in git): `%TEMP%/claude/.../scratchpad/s1242/` (kernels `k/`, results `r/`, edits `ed/`, `tools/*.py`).

## Results (seed 1; cycles per call / ratio to donor; card ratio in brackets)

Every row has status ok, `result_class: unvalidated_scenario_estimate`, `unsupported: []`. Why it is not a forecast:
the declared shape `x87_sparse_rows_l1` has no held-out validation (S12-30 small cases: 16% median, uniformly 12-18%
slow from L1 conflict misses under true LRU), and memory beyond L1 is modeled. limiting_constraints, every row:
miss_stall > x87_serial > spacing > dependency (csr13 knc: 14564 / 11493 / 8316 / 1345 context cycles over 3 calls).
Assumed parameters consulted: `latency.scalar_extend_extra` 0, `latency.x87_move` 3, `pairing.u_instruction_can_be_branch`
false; derived: taken-branch bubble 1, x87 load 3 / mem operand 1, x87 mem-operand serializes, load/store pairing,
store-load interlock 4, memory 328, HWP depth 16.

| variant | CSR n=13 | CSR n=27 | HPCG-ptr n=13 | HPCG-ptr n=27 |
|---|---|---|---|---|
| donor-off | 9513 / 1.000 | 25748 / 1.000 | 9718 / 1.000 | 27529 / 1.000 |
| knc-switch-off (old) | 9651 / 1.015 [1.015] | 25887 / 1.005 [1.006] | 9823 / 1.011 [1.018] | 27632 / 1.004 [1.007] |
| knc two-nests (old) | 9556 / 1.005 [0.991] | 25793 / 1.002 [0.999] | 10047 / 1.034 [1.048] | 27856 / 1.012 [1.018] |
| E0: old + `.p2align 4,,7` | 9515 / 1.000 | 25751 / 1.000 | 9823 / 1.011 | 27632 / 1.004 |
| E0: old two-nests + `.p2align 4,,7` | 9548 / 1.004 | 25785 / 1.001 | 9855 / 1.014 | 27664 / 1.005 |
| today's prefix | 8683 / 0.913 | 24023 / 0.933 | 8991 / 0.925 | 25904 / 0.941 |
| today + P1 (guard inverted) | 8683 / 0.913 | 24023 / 0.933 | 8991 / 0.925 | 25904 / 0.941 |
| today + P2 (no prefetch versioning) | 8491 / 0.893 | 23831 / 0.926 | 8927 / 0.919 | 25840 / 0.939 |
| today + P3 (no pad before inner loop) | 8651 / 0.909 | 23991 / 0.932 | 8959 / 0.922 | 25872 / 0.940 |
| today + P2 + P3 | 8459 / 0.889 | 23799 / 0.924 | 8895 / 0.915 | 25808 / 0.937 |

Reproduction: absolute cycles are 12-18% above the card (the known open miss), but the ordering is right in all four
cases (knc slower than donor) and for two-nests against switch-off (HPCG slower, CSR faster), and the knc/donor gap
is close in cycles: CSR 138/139 predicted vs 129/138 measured; HPCG 105/103 vs 155/168 (about 1.6 cycles per row of
the HPCG gap is not explained). These numbers equal the twin's recorded `s12-30-small` predictions.

## Mechanism (old build), from per-instruction issue logs of the third call

1. Executed padding NOPs with slow prefixes on the short-row path. Loop-versioning sends every short row out of line
   to the plain copy, and its loop head is aligned with `.p2align 4` + `.p2align 3`; gas fills the gap that each row
   executes with a prefixed long NOP. CSR: `66 66 2e 0f 1f 84 00 00 00 00 00` at `knc_csr_raw+0x155` (before loop head
   0x160) costs 6.0 cycles per row against 2.0 for the donor's prefix-free `nopl` at `donor_csr_raw+0x33`
   (frontend: 33 slow-prefix instructions, `decode` 136 cycles per call, the whole CSR gap). Two nests, HPCG:
   `66 66 66 2e 0f 1f 84 ...` at `twin_hpcg_raw+0x544` (before 0x550) costs 8.0 per row (`decode` 192 per call),
   which is the extra two-nest loss (+224 predicted, +255 measured on n=13). Old `knc_hpcg_raw` has a prefix-free
   `nopl` there (0x2fc), so the HPCG single-nest gap is not this.
2. The prefetch loop-versioning guard on every row (`version_loop_for_prefetch`, `niter >= 1023` goes to the
   unrolled, prefetching copy, laid out as the likely path): `lea -0x1(%rdi),%eax; cmp $0x3fe,%eax; jbe` at
   `knc_hpcg_raw+0x1ec/0x1f3/0x1fd` (CSR: `+0x41..0x4b`, plus a `sub`). HPCG per-row preheader 22.7 cycles against the
   donor's 19.7: extra issue events, and the pointer-load miss stall lands on the guard. The taken forward `jbe`
   itself costs nothing at one thread (the 1-cycle refill bubble is hidden by the 2-cycle same-context spacing;
   inverting it, P1, changes nothing). Not x87 serialization, AGI or a dependency chain: inner loops cost the same in
   donor and old knc (20.1 cycles per nonzero CSR, 20.6 HPCG), and x87_serial and miss_stall totals are equal across builds.
3. Today's prefix: S12-31's `.p2align 4,,7` removes item 1 (E0 alone brings CSR to donor and two-nests HPCG to within
   0.3% of single-nest), and S12-31's cmp/jcc adjacency in the inner loop (`faddp; cmp; jg` at
   `today_csr_raw+0x15f..0x163`, `today_hpcg_raw+0x308..0x30d`) pairs cmp with jcc: 2 cycles per nonzero (18.1/18.6 against
   20.1/20.6), which is 832 (n=13) or 1728 (n=27) cycles per call and turns the loss into a predicted 6-9% win. Item 2 is still in today's
   code (`today_hpcg_raw+0x1ec..0x1fd`, `today_csr_raw+0x39..0x43`).

## Proposals (hand-edited copies of `compiler-today.s`, CFI lines stripped; the stripped base reassembles byte-identical)

| rank | change | edit | gain over today (csr13 / csr27 / ptr13 / ptr27) |
|---|---|---|---|
| 1 | P2: do not version for prefetch an inner loop whose trip count is loaded per outer iteration (sparse rows); keep the plain loop only | guard (`lea/sub/cmp $1022/jbe`) deleted, plain copy falls through, prefetch copy left unreachable | -2.2% / -0.8% / -0.7% / -0.2% |
| 2 | P3: no alignment padding before an inner-loop head that is entered by fall-through once per outer iteration | `.p2align 4,,7/.p2align 3` before `.L8`/`.L34` deleted | -0.4% / -0.1% / -0.4% / -0.1% (1 cycle per row; removing the NOP exposes a 3-cycle AGI on `movslq %ecx,%rax` then `(%r10,%rax,4)`) |
| 3 | P1: lay the short copy out as the fall-through (guard probability inverted) | `jbe .L4` -> `ja .LPF` with the plain block moved after it | 0 at one thread (bubble hidden); only 2-4 threads could show it, not simulated |

P2+P3 together: -2.6% / -0.9% / -1.1% / -0.4%. Batch on csr13 ranks today+P2+P3 < today+P2 < today+P3 < today =
today+P1 < donor < E0 < old knc < twin-E0 < old two-nests; every candidate `uncertain` (unvalidated shape).

## Validated band and what needs the card

- Mechanisms: prefix-NOP decode, padding style and cmp/jcc order are the rules calibrated and held out on S12-31's
  `x87_row_loop_l1` rows (2.9% median, padding styles 14/14, loop orders 8/8; HPCG card 1.088 for the order change).
- Numbers: all are `x87_sparse_rows_l1`, which is not validated. The old-build gaps (0.4-1.5%), E0 and P1-P3
  (0.1-2.6%) are inside any error band: the twin explains them, but only the card can decide. Today's predicted
  6-9% lead over donor is above 5%, but on an unvalidated shape it is still a scenario estimate.
- Card next (S12-42's own first step): rerun the four 32-row cases plus two-nests with today's prefix. Prediction:
  today's build at least 6% faster than donor in each case, and the two-nest loss mostly gone (two-nests not
  compiled here; the E0 two-nest row stands in for it). If the card agrees, S12-42 reduces to optional P2 (and P3),
  which would need their own card rows.
