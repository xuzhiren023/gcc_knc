# S12-18: double vector math before the valid card rerun

Phase 1, 2026-11-14. No new card result is claimed. The library and compiler
are unchanged. The staged benchmark is `.work/_shared/S12-18/vmath-bench.mic`.

## What failed in the old measurement

The ticket's `tmp/claude-s11-12-turn/bench-full-1.out` records these L2
vector/scalar ratios: exp 1.2131, log 1.5769, pow 2.0339. Their vector batch
medians were 25.4, 26.7 and 20.5 ms, respectively, all INVALID. The run later
exited 2 after the first memory-set correctness check (expf), before printing
its sizing. It also contains repeated monitor `sleep: invalid number '0.1'`
errors. Neither the ratios nor that run establish valid native performance.

S10-10 scaled each build independently but accepted one in-range calibration
sample. If early execution is slower, that sample selects too few repetitions
for warmed-up execution. Nothing repaired later short batches; validity only
examined medians, and measure returned success even for INVALID. The approved
red fixture reproduces this mechanism with a simulated clock, not its cause
on the card. A second fixture scenario exposes another limitation: when one
memory sweep exceeds 200 ms, integer repetitions cannot shorten it.

The fix requires two consecutive in-range calibration samples. Every timed
sample must be 50-200 ms. A rejected group is printed as `retry_batches`, then
recalibrated and retried, with a finite retry limit and error exit on failure.
Only complete accepted groups contribute ratios. Each group's actual repetition
count supplies its element denominator, including after resizing.

For memory measurements, a repetition now visits one chunk equal to the L2
kernel's element count. Separate vector/scalar cursors advance across the full
memory arrays and wrap; calibration, warmup and timed batches all advance them.
The working set is rounded down to whole chunks and its actual byte count is
printed. At density 4, unary double uses 4096 elements/chunk and 524288/span;
pow uses 2720/chunk and 348160/span (about 31.875 MiB/core). This does not repeatedly
time the first cache-resident slice. It does introduce a function-call boundary
per chunk, so the old whole-sweep memory ratios are not directly interchangeable.
L2 element counts are unchanged. Persistent load or an individually overlong
chunk still fails rather than relaxing the 50-200 ms rule.

Host regression: all 12 scenarios passed (exp/log/pow, steady L2, startup
transient, transition during timing, and a memory sweep too long for one batch).
The memory fixture checks successive offsets and at least one complete wrap
for each build, as well as batch durations and normalized ratios.

- Approved red: commit `6a256a79`.
- Memory scenario red: `.work/_state/logs/s12_18_mem_red-20261114-142225.log`
  (three expected calibration failures; L2 controls passed).
- Final host pass: `.work/_state/logs/s12_18_batches_mem_green-20261114-142439.log`.
- Final cross-build/link/lint pass:
  `.work/_state/logs/s12_18_stage-20261114-142509.log`.

Build command: `python tools/run.py --name s12_18_stage --inputs tests/bench/vmath tools/s10_04_vmath_bench.py -- python tools/s10_04_vmath_bench.py build --out ../_shared/S12-18`.
Host regression uses Cygwin `python3.12.exe tests/vmath/test_s12_18_batches.py`
through tools/run.py, with the shared toolchain's cygwin/bin on PATH.

## Generated code and per-element work

Inspected the linked benchmark with the shared K1OM objdump, `-d
--no-show-raw-insn`; disassembly is `.work/_shared/S12-18/bench.asm`.
Scalar calls go through exp/log/pow@plt. The comparison library inspected is
`toolchain/sysroot/lib64/libm-2.21.so`, with disassembly in
`.work/_shared/S12-18/libm.asm`. This describes the staged sysroot library;
the rerun must use the corresponding card libm to make that comparison exact.
No ICC headers, SVML or libimf were read.

Counts exclude nop/data32 alignment padding and `xchg %ax,%ax`. Static counts
include exceptional paths once and do not expand loops; they are code-size/work
indicators, not executed instruction counts or cycles. Stack references below
are explicit rsp-based memory instructions, excluding lea. They include local
arrays and lane transfers, so they must not all be described as allocator spills.

| Mathematical core | Static instructions | Instructions with zmm operands | x87 sites | Explicit stack-memory sites | Frame reservation |
| --- | ---: | ---: | ---: | ---: | ---: |
| exp: pw_core_exp | 551 | 81 | 18 | 201 | 0x488 bytes |
| log: pw_core_log | 745 | 270 | 33 | 200 | 0x388 bytes |
| pow: core called by __knc_vmath_core_pow_8.part.0 | 1233 | 263 | 58 | 370 | 0x708 bytes |

The by-value entry really passes/returns zmm registers, but immediately stores
its arguments into aligned stack unions. exp/log reserve 128 bytes and pow 192
bytes there, then call a separate pointer/mask adapter (256-byte frame), which
calls the noinline mathematical core. Thus each eight-element call has two
additional call/return pairs. The adapter still snapshots inputs and merge
data with scalar moves and runs two eight-lane mask loops despite mask=255.
The mask was not propagated through that out-of-line boundary.

For the all-active path, expanding those eight-iteration loops gives the
following **executed instruction counts from manual path accounting**, including
the public entry and adapter but excluding the mathematical core and caller.
These costs apply even when no exceptional lane occurs.

| Entry | Entry + adapter instructions / eight elements | Per element | Additional ordinary table-loop instructions / element |
| --- | ---: | ---: | ---: |
| exp | 242 | 30.25 | 14 (two seven-instruction loops) |
| log | 243 | 30.375 | 32 (four eight-instruction loops, far path) |
| pow | 222 | 27.75 | 16 for the log table alone, plus the exp table |

Accounting landmarks in bench.asm: exp adapter input loop at
`pw_apply_exp.constprop.0+0xd0`, output loop at +0x118/+0x12e; log equivalents
+0xe0 and +0x128/+0x13e; pow adapter loops at +0x120 and +0x170.
exp table loops start at pw_core_exp+0x2e0 and +0x310, log at
pw_core_log+0x670/+0x6a0/+0x6d0/+0x700, and pow's log table at core+0x5e0.
The rows are additive components, not complete hot-path totals: classification,
range reduction, polynomial work, exponent construction and result repair remain.

There are **no gather instructions** in these three cores. exp performs two
scalar indexed table loads per lane, into arrays later read by vectors. log
performs four table loads per lane using fldl/fstpl pairs, then reloads their
arrays into vector arithmetic. pow does three such pairs for its log table and
two table entries for its exponential stage. Integer vector shifts and exponent
construction also travel through stack slots and per-lane GPR instructions.
log and pow convert their eight integer exponents through fild/fstpl and memory
before vector use. These are ordinary-path x87 operations, not only cold errors.

log unconditionally evaluates its near-one polynomial using sanitized inputs;
when any lane needs the far path, it also performs table reduction and that
polynomial. The benchmark's log-uniform exponent range overwhelmingly uses the
far path. pow retains compensated high/low log, split y/log products, and an
exponential remainder; it is not one cheap vector log followed by one cheap
vector exp. The installed code contains FMA instructions as well as the
compensation sequences. exp's inputs span [-708,709], so lanes frequently
enter the additional large-positive/negative-result handling above |x|=512.
Its 551-site total cannot be treated as one uniform ordinary path.

The scalar libm code is substantially more compact. exp's internal helper at
0x5680 uses frndint, f2xm1 and fscale; log's at 0x8090 uses fyl2x or fyl2xp1;
pow's at 0x8170 uses a log/exponential x87 sequence for noninteger exponents
and a separate integer-power loop. Ordinary positive/finite paths, counting
the public wrapper and its __finite helper where called, are:

| Scalar function | Instructions / element, excluding caller and resolved PLT jump |
| --- | ---: |
| exp, finite nonzero result | 67 (33 wrapper + 24 core + 10 finite) |
| log, positive far from one | 38 (16 wrapper + 22 core) |
| pow, positive base far from one, noninteger exponent, finite nonzero result | 107 (35 wrapper + 62 core + 10 finite) |

These paths are anchored at libm exp 0xb510, log 0xc120, pow 0xc260 and
__finite 0x10b20. x87 transcendental instructions have substantial internal
latency; an instruction count is not a cycle prediction. Nevertheless, the
vector log adapter plus just its table loops already costs 62.375 instructions
per element, before its main arithmetic, versus 38 for the scalar callee path.
This makes the observed ordering plausible without proving its timing ratios.

The exp benchmark's prefetched vector loop has 13 instructions/eight elements
(1.625/element, including the vector call). The scalar prefetched loop has
81/eight (10.125/element, including eight scalar calls), with extra x87/stack
movement around the register ABI. Vector calling does save loop/call overhead;
the callee overhead above can consume that saving. The vector loop uses paired
unaligned loads/stores; the library entry is unmasked. Counts are multiples of
16, so the generated scalar tail is not executed in these measurements.

## M4 development corpus and phase 2 choice

Read the 28 records (14 programs, both compilers) in S12-01/census.json.
None contains a double `__knc_vmath_exp_8`, `__knc_vmath_log_8` or
`__knc_vmath_pow_8` entry, including PLT entries. Therefore none of these census
builds calls these vector double functions in a loop, and no matching corpus
A/B is staged. Development programs checked: STREAM, NPB-CG, NPB-EP, NPB-MG,
NPB-IS, HPCG, SQLite, PB-gemm, PB-atax, PB-cholesky, PB-ludcmp, PB-jacobi-2d,
PB-heat-3d, zlib. NPB-CG has scalar pow@plt and NPB-EP scalar log@plt;
SQLite's sqlite3_log is unrelated. No held-out executable was accessed.

If valid reruns confirm the losses, the cheaper scoped option is a measured
vectorizer cost correction for these three double calls. Removing adapter
overhead alone does not remove the table loops, scalarized integer operations
or compensated math. A library rewrite also needs S10 qualification at 1 ULP.
The cost correction should preserve ADR-0014's library binding and public
entries, while making profitability reflect the measured per-element costs;
it should not globally disable the binding or affect the profitable float calls.
No cost values are selected from the invalid run. This ticket is currently
gcc:no/tools3; implementing phase 2 requires lead results and a GCC lane/build.

## Staged exclusive rerun for the lead

Use the staged binary above. Both sets and all seven kernels are enabled;
21 rounds x 5 batches, three launches per profile, targeting roughly 10-30
minutes per profile with setup/retries. Run sequentially in the coordinated
exclusive card turn. From the project root, first launch of each profile:

```text
python tools/run.py --name s12_18_full_l1 -- python tools/card_run --benchmark --profile full --threads 240 --timeout 1800 .work/_shared/S12-18/vmath-bench.mic --cores 60 --density 4 --set all --kernel all --rounds 21 --batches 5
python tools/run.py --name s12_18_3100_l1 -- python tools/card_run --benchmark --profile 3100 --threads 224 --timeout 1800 .work/_shared/S12-18/vmath-bench.mic --cores 56 --density 4 --set all --kernel all --rounds 21 --batches 5
python tools/run.py --name s12_18_5100_l1 -- python tools/card_run --benchmark --profile 5100 --threads 236 --timeout 1800 .work/_shared/S12-18/vmath-bench.mic --cores 59 --density 4 --set all --kernel all --rounds 21 --batches 5
```

Repeat with names ending l2 and l3, retaining the wrapper logs. Profiles select
core/memory limits, not physical SKU clocks. Require successful exit, all
correctness checks, all accepted batches in range, and the full 14 summaries.
Inspect retry_batches and monitoring errors before accepting a timing comparison;
report each profile/set separately, with round ratios and launch variation.
No engineer card execution, GCC rebuild, or x86 check was performed.
