# Windows vector-math algorithm experiments

These are separate host arithmetic experiments. They define no `_ZGV` export,
do not provide `libknc_mvec.a`, and do not qualify G5, IMCI instructions, target
ABI, masks or target floating exceptions. The existing 36-symbol specification and six
source wrappers in `../libknc_mvec/` retain their separate status. In particular,
the four declared full-width expf/exp/logf/log interfaces remain undefined.

The algorithm source and coefficients come from Arm optimized-routines release
v26.01, annotated tag object `ed2fb3fb33eb023a0444e193e5fddc4fa2e0b01e`,
resolved commit `649ccc8411e7c4862965710f25c570d854a1483f`.
The small unmodified source set, complete upstream license and per-file SHA256
lock are retained at `native/upstream/arm-optimized-routines-v26.01/`.
The separate `arm-optimized-routines-v26.01-dp/` subset retains the double
algorithms and data at the same commit, preserving the first subset's lock.
These adaptations select the MIT license offered by upstream; copyright
notices are retained in each adapted source. No approximation coefficients
were fitted locally. The upstream scalar error claims do not transfer to the
adapted vector code.

The algorithms use GCC vector extensions with four double intermediate
lanes. The expf/logf experiments have four binary32 input/output lanes;
exp/log have four binary64 input/output lanes. Individual lanes select the exact
upstream table entries; range reduction and polynomial arithmetic use vectors.
They call no scalar exp/log implementation. This initial width is a host
algorithm implementation, not a statement about the final 16-lane KNC ABI.

| Experiment | Algorithm | Admitted input domain |
|---|---|---|
| `phi_expf_bounded4` | 32-entry exp2 table, degree-three polynomial, double intermediates | Finite binary32 [-80,80], including both zero signs and subnormal inputs |
| `phi_logf_bounded4` | 16-entry reciprocal/log table, degree-four polynomial, double intermediates | Positive normal binary32 [2^-126, largest finite] |
| `phi_exp_bounded4` | 128-entry scale/tail table, split-ln2 reduction, degree-five polynomial | Finite binary64 [-500,500], with upstream tiny-input 1+x treatment |
| `phi_log_bounded4` | 128-entry split-c reduction, general degree-six and compensated near-one degree-twelve polynomials | Positive normal binary64 [2^-1022, largest finite] |

The caller must establish nearest-even rounding with MXCSR FTZ and DAZ off.
The drivers verify that state and AVX2 support before executing the kernels.
The low-level bounded interfaces check all four input lanes before writing
any output. Unsupported lanes fail the experiment; they are not replaced by a
libm fallback. These interfaces are not production mathematical functions.
NaNs, infinities, log zero/negative/subnormal inputs, exp overflow/underflow,
non-nearest rounding, errno and floating-exception behavior remain outside
these initial checks. Input-domain rejection is not mathematical handling of
those cases. No full-range or exhaustive accuracy claim is made.

The actual executing compiler is the existing **Cygwin GCC14.4.0** targeting
`x86_64-pc-cygwin`, which produces Windows host executables. It differs from the
project **GCC14.3.0 x86_64-linux-gnu** assembly generator. Native target options
and a baseline-x86-64 capability executable record the actual host; the first
run reports Skylake, AVX2/FMA available and AVX-512 unavailable. Each algorithm
is built separately with `-ffp-contract=off` and `fast`, `-march=native`, no
fast-math, and no scalar libm imports. Inspecting generated vector arithmetic
and FMA counts is part of each local experiment. These flags do not modify
WRF BIND, OPT, NOOPT or the frozen G0 sources.

The independent oracle uses Python3.12 Decimal/libmpdec exp or ln at 100 and
160 decimal digits. Binary32/binary64 inputs are converted exactly. Each result is
enclosed by one decimal last-place unit; exact integer rational-to-binary32/64
nearest-even conversion must round both interval endpoints identically at
both precisions. Ambiguous or inconsistent intervals fail closed. No binary64
exp/log or binary64-to-binary32 reference rounding is used. The assay records
both the distance from the correctly rounded reference and a conservative
upper bound on error in the rounded reference's binary32/64 ULP spacing.
The 4-ULP check compares the exact
rational upper bound, not its displayed floating approximation.

Deterministic corpora include independently mixed lanes, uniform admitted bit
patterns, numerical-range samples, range-reduction/table boundaries and
neighboring binary32 numbers. Log additionally samples densely near one.
Inputs, outputs, rounded references, worst cases, histograms, compiler/tool
and Cygwin dependency identities, Python binary identity, raw commands,
source snapshots and source drift checks are retained privately. Previous
failed attempts are retained separately. Each run writes its own
`experiment.json`, not a public G5 receipt.

```powershell
& 'C:/Users/xuzhi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' scripts/Check-HostExpf.py
& 'C:/Users/xuzhi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' scripts/Check-HostLogf.py
& 'C:/Users/xuzhi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' scripts/Check-HostExp.py
& 'C:/Users/xuzhi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' scripts/Check-HostLog.py
& 'C:/Users/xuzhi/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m unittest discover -s tests -p 'test_host_*py'
```

The first expf experiment retained at
`artifacts/test-state/host-expf/315edfac489c42219740f4f0e0cfd16e/experiment.json`
checks 84,612 lanes, with two padded zero lanes. For both contraction policies,
84,569 results equal the rounded reference and 43 differ by one binary32
step. The maximum conservative absolute error is 0.5013890255560783 ULP.
The off/fast kernel assemblies contain 0/5 FMA instructions respectively.
Five actual exceptional/out-of-domain controls per variant fail without an
output file. These observations apply only to the frozen finite corpus and
stated environment. Larger independent random sets, full special-value and
exception policy, all 36 symbols, translated-pipeline qualification and card
measurements remain required before G5.

The first logf experiment retained at
`artifacts/test-state/host-logf/f393f9f4cd884c5d8099ffd27d637508/experiment.json`
checks 89,208 lanes over positive normal inputs. Both contraction variants
stay within one binary32 step of the rounded reference, with a maximum
conservative absolute error of 0.7748329359029679 ULP. The full raw histograms
and worst-case inputs are in that private report. Seven actual unsupported
domain controls per variant fail without output. The dense near-one set
includes every binary32 value within 16,384 input steps on either side of one;
all admitted normal-exponent table-cell edges have neighbor checks. This is
sampled finite-domain evidence, not exhaustive coverage of all normal inputs.

The two report SHA256 values are respectively
`3c7ae6b310887e5ff32f0af286b0c7ab78fa089a6f5c23aaefdad919cdbe213c`
and `235d68dd5687f12f00adce179256276231b7c2263c5c992917fe277285f00a6e`.
Nine focused Python controls check exact binary32 tie/overflow/subnormal
rounding, reference special identities, wrong-output rejection, empty and
truncated comparisons, log(1) zero sign and exact upstream data identity.
These source/oracle controls are separate from the actual C executions.

The double exp experiment at
`artifacts/test-state/host-exp/fb66719ba1824aee8a974f32195e2047/experiment.json`
checks 96,304 lanes in [-500,500], including one padding lane. The off build
has 96,239 exact rounded-reference matches and 65 one-step differences;
the fast build has 96,261 matches and 43 one-step differences. Their maximum
conservative absolute errors are 0.5049744233837652 and 0.5042504123839824 ULP.
The off/fast kernel assemblies contain 0/8 FMA instructions. Its report SHA256
is `7644e0fb2e77f681b5af2b90418f56b51639549c1da1c7434703cf4797a4775d`.
Raw filenames inherited the `.u32` suffix in that frozen first DP experiment;
the payloads are explicitly packed/decoded little-endian 64-bit words, with
eight bytes per recorded lane. The filename suffix does not describe their
binary representation. Its exact source snapshots and original files remain
unchanged.

The DP data builds use the original upstream configuration and exact tables,
with `HAVE_FAST_FMA=0` selecting split-c log reduction for both contraction
experiments. Polynomial arithmetic can still contract in the fast build.
Original ELF hidden-visibility annotations are unsupported on Cygwin PE;
`-Wno-error=attributes` retains that warning, with all other enabled warnings
treated as errors. No upstream source or production build policy is changed.

The double-log experiment at
`artifacts/test-state/host-log/02a1daeba4704ed190f5b51adaa86c44/experiment.json`
checks 140,780 lanes over positive normal binary64. Both contraction policies
stay within one binary64 step of the rounded reference, with maximum
conservative absolute error 0.5113124677352584 ULP. The report SHA256 is
`d616ceb7a140ae65ce2e982edc3cad96c7860af5283a4a0b229c4be5e7b9261a`.
Seven actual unsupported-domain controls per variant reject without output.
The corpus includes 65,537 consecutive binary64 inputs around one, near-one
branch boundaries, all powers-of-two neighbors, every table cell at selected
exponents, and separate normal-bit/numerical-range random samples. This does
not exhaust positive normal binary64 values.

Sixteen focused Python controls now cover both binary32 and binary64 exact
rounding, oracle identities, assay failure paths, zero signs and upstream data
identity. Successful numeric reports retain source snapshots and show no
source drift during their runs. A preceding expf include-path compile failure
and a DP-exp visibility-warning compile failure are retained privately; no
numerical candidate executed in those failed preparations.

Next work remains full-range/special-value and exception policies, larger
independent random and directed corpora, every remaining declared family,
and eventual qualified translation/card tests. Four bounded host algorithms
do not implement the 36 target exports or complete G5.

| Algorithm | Lanes (including padding) | Off max ULP upper bound | Fast max ULP upper bound | Off/fast FMA instructions |
|---|---:|---:|---:|---:|
| expf | 84,612 | 0.5013890255560783 | 0.5013890255560783 | 0/5 |
| logf | 89,208 | 0.7748329359029679 | 0.7748329359029679 | 0/5 |
| exp | 96,304 | 0.5049744233837652 | 0.5042504123839824 | 0/8 |
| log | 140,780 | 0.5113124677352584 | 0.5113124677352584 | 0/21 |

The bound's unit is the rounded reference's ULP spacing. Every variant has
maximum rounded-reference distance one on its checked corpus. No row in this
table is a full-domain, million-input-per-export or target execution result.

Official sources: [Arm release](https://github.com/ARM-software/optimized-routines/releases/tag/v26.01),
[pinned expf](https://github.com/ARM-software/optimized-routines/blob/649ccc8411e7c4862965710f25c570d854a1483f/math/expf.c),
[pinned logf](https://github.com/ARM-software/optimized-routines/blob/649ccc8411e7c4862965710f25c570d854a1483f/math/logf.c),
[Python Decimal reference](https://docs.python.org/3.12/library/decimal.html).

A fresh [full-input expf experiment](expf_full_experiment/README.md) now admits
all binary32 encodings under nearest-even, masked exceptions and FTZ/DAZ off.
Its separate source handles subnormal results, overflow, signed zeros,
infinities and an explicit NaN sign/payload/quieting policy, using the same
pinned Arm core plus an independently pinned official error-helper supplement.
The four bounded source/report snapshots above remain unchanged.

The private result
`artifacts/test-state/host-expf-full/f2a1c047df2c4990a1ac120458a88291/experiment.json`
has SHA256 `0f092cd34c46391f7508cf9c42b797ea90ac559b34837ac0a9f786433a0288f1`.
Both native AVX2 contraction variants checked 1,220,356 lanes: finite-result
histograms have 957,985 exact matches and 123 one-step differences, with maximum
conservative error0.501584174251554 ULP. There are no special-value mismatches
or exception-policy mismatches across 305,089 vectors per variant. The corpus
contains 73,127 subnormal results, 253,260 finite rounded zeros, 254,207 finite
overflows, 3,974 qNaNs and 4,064 sNaNs. All 12 actual malformed-input/unsupported-
state controls rejected without output; seven focused oracle/assay tests passed.
Both compilations have empty warning logs, and raw symbols show no scalar
expf import or `_ZGV` export. The off/fast assemblies contain 0/5 FMA instructions.

This extends sampled host evidence, not exhaustive binary32 proof or G5.
The million raw-bit draws use explicitly recorded Python MT19937; the kit's
LCG Fortran/card conformance is still open. Non-nearest rounding, errno,
unmasked traps and target NaN/exception/ABI/mask behavior remain unqualified;
none of the 36 target exports is implemented by
these private host functions. The full-input expf source is kept separate
from the earlier finite-only algorithm so its evidence stays reproducible.

The strict compiler-policy expf rerun now supersedes the first full-input
result for current host evidence. It is retained at
`artifacts/test-state/host-expf-full-strict/c74a714c45474547a2648b5770f61529/experiment.json`,
SHA256 `94950124777249787add0b45118dd7e287332a80dc386f4b344e121c69044542`.
Only `-fno-math-errno` is replaced by `-fmath-errno`; the earlier source/report
remains immutable. Both strict off/fast executables reran the same corpus,
reference and 12 rejection controls with byte-identical output/flag records,
the same ULP bound and zero mismatches. This preserves compiler errno
semantics while leaving the library errno contract explicitly open.

A separate [full-input logf experiment](logf_full_experiment/README.md) now
covers positive subnormal through maximum-finite inputs and explicit pole,
negative-domain, infinity, q/sNaN and exact log(1)=+0 policies under the same
nearest/masked/FTZDAZoff host limits. It uses `-fmath-errno` from the start.
Private report `host-logf-full/8c5e4d8d78264c69a6dc8173461bc926/experiment.json`
under `artifacts/test-state/` has SHA256
`211f7b557b84b6582fce2b4274e885f39f8f6cb5e0ac565ea1fa42f6feacd95f`.
Both off/fast variants checked 1,300,452 lanes, with 790,359 exact finite
matches, 3,162 one-step differences and maximum error upper bound
0.7551645736009517 ULP. All 506,931 special comparisons and 325,113 exception
vectors match per variant. The corpus has one million deterministic 64-bit
LCG draws plus dense directed and isolated cases. Eight focused controls and
all 12 actual malformed/state controls passed; no warnings, scalar logf
delegation, `_ZGV` export or source drift occurred. The five earlier algorithm
components and their successful reports remain unchanged. This adds sampled
host coverage and no target, errno, directed-rounding or G5 qualification.

Full-input binary64 host results are now retained separately. The DP exp
[source and policy](exp_full_experiment/README.md) checks 1,375,996 lanes with
maximum conservative errors 0.505430639581543 (off) and 0.5043706063521957 (fast)
ULP; its result SHA256 is
`cc3869c8a61387c9c5f53ed1456fee000f4a5154c4fd8870efc9d154326f606d`.
All 343,999 vector exception checks per variant match, including tiny/subnormal
inputs handled by the official 1+x path without spurious underflow. A separate
[exact one-ULP evaluation](ONE_ULP_ASSESSMENT.md), SHA256
`1881484a32abe05c9e40c2c0323291bb804251b9f44cfe170fc37fc9880703a2`,
recomputes independent bounds over those same authenticated raw outputs and
directly enforces <=1 ULP, without compiler/kernel/card reruns or old-receipt
changes. Exact worst-bound fractions are retained.

The [full-input DP log source](log_full_experiment/README.md) uses an actively
enforced <=1 ULP acceptance test from the start. Its result SHA256 is
`ae4efb5931507013d14d2326ca0b7b31ea9ed0261fbe7b70b7c4c27e745454df`.
Both off/fast variants check 1,364,460 lanes, with 859,798 exact finite matches
and 102 one-step differences, maximum conservative error 0.510228845583582 ULP,
and zero special/exception mismatches across 504,560 special comparisons and
341,115 exception vectors each. Its million64-bit LCG inputs are supplemented
by dense subnormal, near-one and branch-boundary cases and isolated specials.
All 12 actual malformed/state controls and eight focused tests passed.

Both new DP kernels retain `-fmath-errno`, no fast-math, official pinned data
and the original narrow visibility-warning demotion for Cygwin PE. The active
host numerical target is now <=1 ULP; historical four-ULP report fields remain
immutable and do not relax that target. The earlier SP full-input measured
bounds are also below 1 ULP. These four host algorithms still define no target
exports and qualify no vector calling convention, masking/FP state, target
runtime, directed rounding, errno or G5. The complete 36-symbol target remains
separate and unqualified.

A fresh [private e-width host experiment](e_width_experiment/README.md) now
checks actual GCC vector arithmetic with 16SP/8DP lanes on AVX2, with no target exports.
Its completed private report is
`host-e-width/b595df3d71fb4a8cb8b0c7b82f9b746b/experiment.json` under
`artifacts/test-state/`, SHA256
`03681944dd7d66185a51343b85e6901af7c04b725e22e4c1225de63ae9cc4f25`.
Both strict off/fast variants passed the active <=1ULP interval guard, exact
specials/identities, active-lane exception union and inactive merge-bit checks.
Maximum ULP bounds are 0.501584174251554 for expf, 0.7753994128742986 for logf,
0.505430639581543 / 0.5043706063521957 for exp off/fast and 0.510228845583582
for log. Each function has one million fresh deterministic LCG draws plus
preserved directed edges; the complete experiment checks 6,445,024 active and
1,184,784 inactive lanes per variant across 653,454 vectors. Every 16SP/8DP mask
pattern, empty-mask zero-FP behavior, exact input/output and merge/output
aliases, arbitrary inactive encodings and actual unsafe-inactive negative
controls are covered. No value, merge or exception mismatches or source drift
occurred. Seven focused tests and all 72 malformed/state execution controls
passed. Actual GCC14.4 native compilation uses YMM arithmetic and no ZMM;
`-fmath-errno` and no-fast-math remain in force. Only the known unchanged Arm
DP data-file PE visibility warnings are retained.

The mask is an explicit private software test contract. Observed eN exports
remain unmasked; this adds no GNU masked-vector ABI, b/d target inactive-lane,
KNC instruction, reserved-mask epoch, calling convention or G5 qualification.
Full readable 64-byte buffers are required, with no memory fault suppression or
partial-overlap contract. Errno and directed rounding remain open. All prior
successful source/report bytes and the canonical 36-symbol scaffold/wrappers
remain unchanged. No card action or production integration was performed.
