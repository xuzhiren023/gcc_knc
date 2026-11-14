# S12-08: distinguish pressure spills from ordered-reduction storage

2026-11-14, phase 1: **premise failed, no compiler change**. No native
execution. The lead closed the failed premise without a card run; phase 2
is not entered.

The large x87 stack count does **not** establish an x87-pressure problem in
the qualified ludcmp loops. Its 128 floating-point stack reads are ordered
consumption of vector products in the later triangular solves, outside the
three selected hot regions. The remaining two reads convert integers.
There are real GPR spills around the dense loops, but no demonstrated
removable spill inside their hot bodies. Phase 2 has not started.
The hot matrix-construction exposure stays unexplained by pressure.

## Evidence and scope

Read the S12-08 facts and residual-gap table in
[knc-reference-gaps.md](knc-reference-gaps.md), the selected regions in
[m4-baseline.md](m4-baseline.md), and the pressure/scalar-FP counts in
[m4-code-census.md](m4-code-census.md). The reference note's R02/R03/R17
qualifications apply: ABI transfers are not free; pairing depends on actual
encodings; density four is not a measured single-worker schedule. No new
vendor-document claim is needed for the diagnosis below.

Only the primary, serial, checked GCC-KNC entries for PB-ludcmp,
PB-cholesky and NPB-CG in `.work/_shared/S11-18/builds.json` were
disassembled. Their disassemblies are under `.work/_shared/S12-08/`.
No held-out program was opened, built or run. Existing census counts are
static sites, not execution counts or time fractions.

For causal RTL evidence, the existing **gcc2** compiler
`.work/_shared/gcc-build-2/gcc/xgcc` compiled the two original PolyBench
translation units and original diagnostic kernels at `-O2 -march=knc`.
The lane's source and clean build stamp identify GCC commit
`619e14b479a952edff32e94f22573710d0b8ac17`. Benchmark dimensions and capture
header match the corpus build (`N=512`, double, dump arrays). No upstream
source was copied into this repository or changed. These newly compiled
translation units provide RTL evidence; the address ranges below refer to
the frozen S11-18 binaries, not the new assembly.

## Hot regions and stack classification

Ranges exclude the end address, consistent with the baseline's loop body
boundaries. Direct inspection found zero stack memory operands in each:

| Program / region | Address range | Instructions | Stack operands |
| --- | --- | ---: | ---: |
| ludcmp matrix construction | `400c80..400d8c` | 63 | 0 |
| ludcmp factorization A | `400fc0..4010b7` | 56 | 0 |
| ludcmp factorization B | `4011e0..4012da` | 56 | 0 |
| cholesky matrix construction | `400b50..400c5a` | 63 | 0 |
| cholesky factorization reduction | `400eb0..400ec5` | 7 | 0 |
| CG indexed reduction | `402480..402499` | 8 | 0 |

**Ludcmp x87 counts.** All 130 whole-program x87 stack-read sites are in
`main`: 128 `fsubl` and two `fildl`. For example, `401449` multiplies a pair
of vectors, `40144f` stores the product vector at `rbp-0xb0`, and
`401459..401480` subtracts the eight elements in order from one x87
accumulator. The same storage is reused by subsequent chunks. This is an
intentional vector-to-scalar transfer for a fold-left reduction, not eight
live x87 accumulators spilling. It belongs to the later contiguous
triangular solves, not the factorization ranges above. The census's
`x87_memory` field counts only fld/fst families, whereas its x87 stack-load
field also counts arithmetic memory operands; neither is a spill counter.

**Ludcmp GPR traffic.** Assembly and IRA do establish allocation pressure
around the loops. `ludcmp.s` marks saved induction values/pointers as
`%sfp`; the ISA-level accesses around `400fb1..400fb8` and after `4010b7`
are outside the selected inner body. `ludcmp.c.330r.ira` records region
pressures up to `GENERAL_REGS=31`, but only `FLOAT_REGS=3`. Its
spill/restore movement at lines 18749--18761 includes general-register
pseudos 378, 561 and 588; 378 and 588 are induction variables
`ivtmp.135` and `ivtmp.323`. Unrolled strided accesses and their address
increments require many live integer values. These are compiler-created
spills, not address-taken source locals, but their existence does not prove
that a different schedule can remove them profitably. The hot bodies
already keep their operands in registers.

**Cholesky cross-check.** Its three x87 stack reads comprise one integer
conversion and two loads of scalar sqrt return values transferred from
ZMM storage (`401015`, `401055`). The latter follows the sqrt call at
`401035`; the first is another return path. They are ABI-domain transfers,
not evidence that the x87 register stack filled up. Its IRA pressure peaks
at 21 general registers and three x87 registers. The matrix-construction
loop has the same outer-address storage issue as ludcmp, while neither
selected inner body accesses the stack.

**NPB-CG cross-check.** `conj_grad_` accounts for 168 `faddl` stack-read
sites; the other functions account for the remaining 49 x87 stack-read
sites in the whole executable. In the vector-product path near `401db0`,
vector loads/multiply and a vector store precede eight ordered `faddl`
reads at `401e0a..401e3b`. This is the same fold-left transfer mechanism.
The qualified indexed sparse reduction at `402480..402499` has no stack
operand. Thus the dense and sparse program census totals cannot be
assigned to their selected hot loops.

## Reduced experiment and causality

`tools/s12_08_pressure.c` contains five original kernels. The baseline uses
`-O2 -march=knc`; its paired diagnostic uses the same flags plus
`-fno-tree-vectorize`. This override is diagnostic only, not a proposed
compiler policy or an M4 scoring build.

| Kernel | Purpose | Baseline x87 stack reads | Scalar-control reads |
| --- | --- | ---: | ---: |
| independent | Independent element updates, with ordinary alias legality | 0 | 0 |
| dense_update | Ordered per-element updates through column-strided sources | 0 | 0 |
| dense_recurrence | Ordered row/column products as in dense factorization | 0 | 0 |
| contiguous | Ordered contiguous dot subtraction, matching the bridge mechanism | 72 | 0 |
| indexed | Ordered indexed dot addition, sparse control | 0 | 0 |

The contiguous baseline has nine static vector stores feeding nine sets of
eight `fsubl` sites, including unrolled/remainder paths. Its IRA pressure is
only `GENERAL_REGS=8 FLOAT_REGS=1 ALL_SSE_REGS=3`. In
`base.c.275r.expand`, the vector product already feeds sequential lane
extractions and DF subtractions (e.g. lines 3361--3420), before allocation.
The vectorizer dump explicitly selects a fold-left reduction. Allocation
implements those transfers through memory; it is not reacting to exhausted
x87 registers. Source `gcc/config/i386/i386-knc.cc` near line 2023 also
states that the backend supplies no fold-left-plus expansion. A pressure
scheduler cannot simply delete these stores and reads while retaining the
chosen vector-product lowering.

The dense kernels vectorize zero loops. Both variants retain 48 and 54
`%sfp`-annotated instruction sites respectively (these include reads,
writes and updates, not just loads). Disabling vectorization therefore
does not remove their address pressure. This comparison does not isolate
prefetch-generated unrolling from other induction-variable transformations,
and no scheduling-before-RA explanation is established. No claim is made
that every outer spill is necessary or that all scheduling alternatives
have been exhausted.

The experiment can distinguish useful vector products from a transfer cost
that outweighs them. It cannot assign the 11.0 s initialization exposure
or 6.8 s factorization exposure to those later contiguous reductions.
There is currently no measured removable cost justifying a failing
fewer-spill test or a general compiler change. Do not create an arbitrary
red test by demanding removal of required fold-left storage.

## Staged batch for the lead

Host command, run once:

```text
python tools/run.py --name S12-08-stage --inputs tools/s12_08_stage.py tools/s12_08_pressure.c -- python tools/s12_08_stage.py
```

Result: **PASS**, compiler/assembler/linker, KNC binary lint, and launcher
shell syntax. Log:
`.work/_state/logs/S12_08_stage-20261114-145601.log`.
ELF inspection reports only `libc.so.6` and `librt.so.1` as dependencies;
no compiler runtime needs transport. Assembly, vectorizer, expand, IRA and
reload dumps remain under `.work/_shared/S12-08/`. There was no GCC build.

One paired batch, well below the ticket's 20-minute ceiling:

```text
python tools/card_run --threads 1 --timeout 60 --file-list .work/_shared/S12-08/files.txt .work/_shared/S12-08/diagnostic.sh
```

`files.txt` transports `pressure-diagnostic.mic`. This is a **single-core
timing diagnostic**, not a long single-threaded correctness sweep. It
requires one CPU in its affinity mask, prints that CPU, runs all five
cases in AB/BA/AB order, calibrates bounded repetition counts toward 50 ms
per member, and has a 50-second alarm. The launcher adds a 60-second limit.
Allocation occurs before timing; each timed repeat includes input/output
initialization, kernel execution and comparison of all output elements.
Inputs are bounded binary fractions so the reductions are exactly
representable; the scalar variant provides the reference. A mismatch or
timeout is a failure, never a passing timing result. These inputs do not
qualify arbitrary FP rounding, exceptions, or alias-overlap behavior.

**Native results: not run.** The engineer may only stage card work under
AGENTS.md. No T0--T2/ICE/x86 or whole-corpus acceptance is claimed. No
before/after compiler pair exists, so the phase-2 ludcmp/cholesky/CG/zlib
full/3100/5100 corpus batch has not been staged. x86 not run.

## Open for a later ticket

- The fold-left vector-to-x87 bridge through stack memory in the ludcmp
  solves and CG `conj_grad_` (168 sites) has unmeasured cost. The staged
  `.work/_shared/S12-08/diagnostic.sh` is the ready measurement; these
  bridges do not explain the qualified ludcmp hot-region exposure.
- Outer GPR induction-variable spills around the strided loops have not
  been shown removable. They do not establish a benefit that would justify
  entering phase 2.
