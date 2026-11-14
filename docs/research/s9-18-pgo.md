# S9-18: branch hints and PGO on KNC (build and assembly; card numbers pending)

Kernels: `tests/bench/pgo/{skewed,dispatch,calls,pointer}.c`. Tool: `tools/s9_18_pgo.py`.
Variants, all `-O2` (card `-march=knc`, prefix `gcc-knc-16.2.0`): **base** (GCC's static guesses),
**hint** (right `__builtin_expect`), **wrong** (inverted), **pgo** (`-fprofile-use`, trained on the
timed mix with another seed), **pgox** (`-fprofile-use`, trained on the other mix).

## Card steps (lead)

1. `python tools/s9_18_pgo.py build` (done): `.work/_shared/S9-18/*-train-*.mic`, `train.sh`,
   `train-files.txt`. `libgcov.a` is in the prefix; instrumented programs link and lint clean.
2. `card_run --timeout 600 --file-list .work/_shared/S9-18/train-files.txt .work/_shared/S9-18/train.sh`
   (not timed). It sets `GCOV_PREFIX`/`GCOV_PREFIX_STRIP` and prints each `.gcda` with `od`.
3. `python tools/s9_18_pgo.py use <stdout file>`: writes the `.gcda` files, builds pgo and pgox,
   links `<kernel>.mic` (all five variants in one program), lints, writes `time.sh` and
   `time-files.txt`, and prints the REPORT table for all five variants.
4. `card_run --benchmark ... time.sh` in several launches. Each program pins to CPU 1, sizes
   batches to about 100 ms on base, and runs 21 rounds with the variants in a shuffled order per
   round. `SUMMARY ratio_median` is the median over rounds of T(variant)/T(base). Every batch's sum
   is checked against base.

## Host check (x86, cygwin gcc 14)

`python tools/s9_18_pgo.py host` runs the whole path on x86, including `train.sh` under the
host's `sh` and the hex round trip through `use`. All five variants give the same checksum for
all four kernels (log `.work/_state/logs/s9_18_host-20261110-191356.log`). The x86 times there
(3 rounds of 10 ms) are not results.

## What the card assembly shows (static variants, `build` REPORT)

| kernel | base / hint / wrong `.text` bytes | layout |
|---|---|---|
| skewed | 121 / 120 / 138 | `rare` is inlined in all three. base and hint have the same layout: common path one taken branch per element. wrong moves the common path after `ret`, so it costs two taken branches per element (`jbe .L2` then `jne .L5`). |
| dispatch | 678 / 597 / 663 | All test `op <= 3` first. base and wrong put the hot four after a taken branch; hint makes the hot four fall through and moves the 16-entry jump table out of line, 81 bytes smaller. |
| calls | 815 / 813 / 827 | `hash` and `eq` stay indirect calls and `find` is out of line in every static variant; `grow` is inlined twice (loop versioned). Hints only reorder the lookup loop; the static variants are expected to tie. Gains here can only come from PGO (indirect-call promotion, then inlining into `find`). |
| pointer | 187 / 180 / 179 | base already keeps the `snprintf` path off the fall-through in practice (one taken back-edge per node, as hint); hint moves the error block after `ret`; wrong puts the `snprintf` call on the fall-through and adds a taken `jmp` per good node. |

Expected readings: hint ≈ base for skewed, calls and pointer (GCC's guesses already right);
hint < base for dispatch; wrong > base for skewed and pointer (an extra taken branch on an
in-order core). The pgo/pgox columns of the `use` REPORT show `.text.hot`/`.text.unlikely`
splitting, `.cold` parts and whether `calls` gained direct calls; read the card ratios against
them.

## S11-17: complete development zlib program

`tools/s11_17_pgo.py` reuses the S11-18 zlib 1.3.1 source list,
`roundtrip.c`, `-O2 -march=knc`, includes, defines and linker search paths.
Both plain and `-fprofile-generate -fprofile-update=atomic` programs compiled
and passed binary lint. They are staged as
`.work/_shared/S11-17/{base,train}/workload`. No GCC compiler build was needed.
The host stage passed once; log:
`.work/_state/logs/S11_17_stage-20261112-180819.log`.
The lead ran the instrumented program on the card on 2026-11-13 at 14:47 EST:
exit 0, `CORPUS_CHECK pass`, empty stderr (ticket's lead report).

Training uses a separate 8 MiB input: LCG seed 29, half of each 4096-byte
block pseudorandom and half a training literal. Evaluation uses the unchanged
S11-18 frozen input (seed 11, one-quarter random), copied verbatim. Both run
level-6 compression, decompression, and a full byte comparison. Only this
development program is staged; held-out programs are never used for training.

Lead sequence, from this worktree (all execution through `tools/run.py`):

1. Run `python tools/run.py --name S11-17-train -- powershell -NoProfile -File ../_shared/S11-17/lead.ps1`.
   This runs only the instrumented workload on the card, not a timed evaluation,
   and returns every profile through the S9-18 `od -b -v` capture format.
2. After the lead returns `train.stdout`, run the host use step with the shared
   Cygwin Python and cross/cygwin bin directories on PATH:
   `python tools/run.py --name S11-17-use --inputs tools/s11_17_pgo.py -- ../_shared/toolchain/cygwin/bin/python3.12.exe tools/s11_17_pgo.py use ../_shared/S11-17/train.stdout`.
   Preserve the instrumented build directory: generate/use share the exact
   executable path so GCC profile lookup names match. The importer requires all
   twelve translation-unit profiles and clean training output. Missing profiles
   and coverage mismatches are errors, never silently accepted fallbacks.
3. The use build has passed lint. The lead runs
   `python tools/run.py --name S11-17-pilot -- powershell -NoProfile -File ../_shared/S11-17/lead.ps1 -Evaluate -Phase pilot`.
   This runs five adjacent base/PGO pairs per full 7120, 3100 and 5100 profile.
   Review the pilot for correctness and timing variation, then run
   `python tools/run.py --name S11-17-confirm -- powershell -NoProfile -File ../_shared/S11-17/lead.ps1 -Evaluate -Phase confirm`
   for ten confirmatory pairs per profile. Pairs alternate base/PGO then PGO/base
   (C T T C), with one pinned worker. The unchanged S11-18 launcher
   measures CLOCK_MONOTONIC_RAW launch-to-exit latency, then checks donor decoding
   and corruption rejection. Each launch retains its stdout/stderr in S11-17 as
   `<phase>-<profile>-<pair>-<variant>.stdout` and `.stderr` (zero-based pairs).

The host use step passed on 2026-11-13. PowerShell captured training stdout as
UTF-16LE; the importer now decodes the BOM before parsing the octal records.
All 12 expected `.gcda` files were returned and imported, with zero missing
profiles and zero coverage mismatch diagnostics. The use build makes both
diagnostics fatal and preserves the generate build's output path. The resulting
`.work/_shared/S11-17/pgo/workload` compiled and passed binary lint.
Log: `.work/_state/logs/S11_17_use-20261113-145120.log`.

`-fdump-ipa-profile-details` also shows measured edge counts read by the use
build, rather than merely successful profile lookup. Dumps remain under
`.work/_shared/S11-17/build/`. The tool rejects a use build with no positive counts.

| Translation unit | Edges read | Positive edges | Maximum count |
|---|---:|---:|---:|
| adler32 | 22 | 7 | 965686 |
| compress | 13 | 9 | 1 |
| crc32 | 34 | 0 | 0 |
| deflate | 496 | 111 | 8355585 |
| infback | 139 | 0 | 0 |
| inffast | 35 | 13 | 4192718 |
| inflate | 358 | 81 | 74938 |
| inftrees | 34 | 25 | 84772 |
| roundtrip | 50 | 22 | 1 |
| trees | 154 | 114 | 2098495 |
| uncompr | 18 | 10 | 1 |
| zutil | 6 | 2 | 6 |

The crc32 and infback files are present with zero measured edges; they are not
missing profiles. Native evaluation subsequently passed on all three profiles;
the paired results are recorded below.

The 2026-11-13 pilot stopped after the base program's successful byte check;
it is an infrastructure failure, not a completed pilot. The donor decoder in
`peer.tar` had mode `0660`. The launcher's subsequent `execl("./peer/workload", ...)`
therefore failed and its child returned 127, without an exec diagnostic. This
was not evidence of a missing BusyBox command. Unlike S11-18's peer packaging,
the original S11-17 packager did not force executable permissions. Packaging now
sets the decoder to `0755`, libraries to `0644`, and uses USTAR instead of PAX.
The generator also preserves the lead's Windows PowerShell 5.1 fix: native stderr
does not terminate the script; `$LASTEXITCODE` still stops failed card launches.

Host regressions reproduced the PAX failure before the fix and now pass archive
extraction, both decoder argument paths, and mocked PowerShell launches with
benign native stderr and nonzero native exit status. Log:
`.work/_state/logs/S11_17_peer_green-20261113-152708.log` (two tests).
The actual peer archive has been rebuilt without changing the trained binaries.
`tools/s11_17_pgo.py check` passed extraction/executable checks, interpreter and
dynamic dependency resolution for the launcher, base, PGO and donor, and exact
evaluation-input equality with S11-18 plus inequality with training. Log:
`.work/_state/logs/S11_17_launch_check-20261113-152819.log`.
The zlib launch calls only `mkdir -p` and `tar -xf ... -C ...` through `/bin/sh`,
then directly executes the workload and donor decoder twice. The failed native
pilot already demonstrated the shell/unpack commands work on the card. No cached
BusyBox applet list was supplied with the ticket; comparison with that literal
list remains a lead prerequisite before rerunning the pilot.

The shared `lead.ps1` already contains the lead's `Continue` fix. Regeneration
was denied by file permissions through both Cygwin and Windows Python; neither
attempt changed that script. Logs:
`.work/_state/logs/S11_17_restage-20261113-152749.log` and
`.work/_state/logs/S11_17_lead_restage-20261113-152809.log`.
The existing staged script was sufficient for the lead's completed evaluation.

### Zlib card evaluation, 2026-11-13

The lead completed five pilot pairs and ten confirmatory pairs per profile at
`ce3d9920`. Every launch passed `CORPUS_CHECK`: 30/30 pilot, 60/60 confirmatory.
Times are measured on the card; the host was loaded with downloads, WPS and lead
builds. Each base run takes about 1.25 seconds. Ratios below are **base time / PGO
time** (greater than one means PGO is faster), in chronological pair order.
Spread is the observed min–max, not a confidence interval. No outlier was removed.

| Phase | Profile | Per-pair speedups (zero-based order) | Median | Min–max |
|---|---|---|---:|---|
| pilot | full 7120 | 1.0010, 1.0123, 0.9942, 1.0164, 0.9951 | 1.0010 | 0.9942–1.0164 |
| pilot | 3100 | 1.0124, 1.0153, 1.0060, 1.0000, 1.0084 | 1.0084 | 1.0000–1.0153 |
| pilot | 5100 | 1.0048, 1.0155, 1.0362, 1.0084, 1.0089 | 1.0089 | 1.0048–1.0362 |
| confirm | full 7120 | 0.8971, 1.0085, 1.0079, 1.0006, 1.0082, 1.0220, 1.0089, 1.0183, 1.0105, 0.9787 | 1.0084 | 0.8971–1.0220 |
| confirm | 3100 | 1.0446, 1.0040, 0.9676, 1.0070, 1.0146, 1.0077, 1.0106, 0.9937, 1.0061, 1.0067 | 1.0069 | 0.9676–1.0446 |
| confirm | 5100 | 1.0047, 1.0001, 1.0089, 1.0179, 1.0176, 1.0040, 1.0120, 1.0099, 1.0028, 1.0132 | 1.0094 | 1.0001–1.0179 |

Captures: `.work/_shared/S11-17/{pilot,confirm}-<profile>-<pair>-{base,pgo}.stdout`
and `.stderr` (PowerShell UTF-16LE). An SSH upload-deadline infrastructure stop
occurred at confirm/3100/pair 7/base; its captures have suffix `.infra`. The lead
resumed pairs 7–9 and all 5100 pairs through `lead-rest.ps1`. The table uses the
successful replacements. Earlier pilot attempts are in `pilot-run1/` (full median
0.996); they are separate from the completed pilot above.

The pipeline works end to end: atomic instrumented training on distinct input,
twelve matching profiles, positive applied counts, profile-use build and correct
evaluation. Confirmatory median gains are approximately 0.7–0.9%, with substantial
pair variation on full and 3100. This is a small observed gain, far below the
19–21% microcase gains; these ranges alone do not establish statistical significance.

### Positive controls: initial candidates (historical)

`tools/s11_17_controls.py` stages five independent integer kernels: a 99%-zero
branch against GCC's nonzero static guess, a volatile function-pointer table with
one 99% target, division with divisor seven 99% of the time, a large hot callee
beside an out-of-line alternative, and a switch with 99% case zero. Each computes
an unsigned sum checked against a separately compiled scalar reference on every
timed batch. Defined unsigned wraparound is part of the result. The inline helper
has 24 dependent arithmetic steps; its actual base/use assembly is the gate for
whether it straddles the effective inline threshold.

Matching training uses seed 29 and the 99% mix; inverted training reverses the
mix. Evaluation uses seed 11 and the matching mix. No corpus or held-out input
is involved. KNC GCC is 16.2.0 and the installed Cygwin host GCC is 14, so host
profiles cannot be used directly with fatal version/mismatch checks. The staged
fallback trains the actual KNC binaries on the card and captures ten `.gcda`
files through the existing octal protocol. No synthetic counters are used.

One new T1 test file, `tests/tools/test_s11_17_controls.py`, requires hot branch
fall-through, guarded indirect-call promotion plus inlining, a guarded constant
division fast path, hot-callee inlining, and dominant switch-case fall-through.
Run it with `--variant base` for the red baseline, then with `--variant pgo`
after importing real training profiles for green. The profile-use builder makes
missing/mismatched profiles fatal and requires positive applied edge counts for
each matched and inverted object. Assembly or timing failures remain failures;
no kernel is yet claimed to be a passing positive control.

The plain `-O2` T1 run failed all five assertions for the intended missing
transformations, without test errors:
`.work/_state/logs/S11_17_controls_red-20261113-170126.log`.
Initial stage/lint passed in
`.work/_state/logs/S11_17_controls_stage-20261113-165822.log`; the revised inline
candidate (external linkage prevents static called-once inlining) compiled and
linted in `.work/_state/logs/S11_17_controls_inline-20261113-170116.log`.

Lead sequence (host commands use the shared Cygwin Python and bin directories
on PATH; card commands run only by the lead):

1. Instrumented binaries and the lead script are under
   `.work/_shared/S11-17/controls/`. Run
   `python tools/run.py --name S11-17-controls-train -- powershell -NoProfile -ExecutionPolicy Bypass -File ../_shared/S11-17/controls/controls-lead.ps1`.
   Return `controls/train.stdout` and `.stderr` to the engineer. The script runs
   ten short checked training programs in parallel, waits for every exit status,
   and only then exports their independent profiles. No timed results are inferred
   from them. The training programs currently share the first allowed CPU; this
   is a correctness/profile collection step, not a throughput measurement.
2. Engineer: `python tools/run.py --name S11-17-controls-use --inputs tools/s11_17_controls.py -- ../_shared/toolchain/cygwin/bin/python3.12.exe tools/s11_17_controls.py use ../_shared/S11-17/controls/train.stdout`.
   Then run the T1 test with `--variant pgo`. Retain the genuine profile data
   as the card-training fixtures requested by the amendment; binaries and assembly stay shared.
3. Once assembly checks pass, lead runs the same PowerShell script with
   `-Phase pilot`, reviews correctness/spread, then `-Phase confirm`. Each phase
   visits full/3100/5100. All five kernels share one uploaded timing script.
   Each binary pins to its first allowed CPU, calibrates a base batch to about
   0.2 seconds, and runs five or ten pairs separately for matched and inverted
   profiles. Pairs alternate C/T then T/C; every batch checks the reference.
   Intended timing work is about three minutes total plus launch overhead,
   below fifteen minutes; each individual native process is under a minute.
   Output: `controls/<phase>-<profile>.stdout` and `.stderr`, retaining every
   per-pair time. Speedup and spread for all five controls remain pending.

The lead's 2026-11-14 00:12 EST training returned all ten profiles and ten
successful correctness checks. The host use build imported all ten, made missing
and mismatched profiles fatal, and compiled/linted all five timing binaries.
Every matched and inverted profile had positive edge counts:

| Kernel | Positive edges, matched / inverted | Maximum count, matched / inverted |
|---|---:|---:|
| branch | 7 / 7 | 2141304 / 2141304 |
| indirect | 5 / 5 | 2162688 / 2162688 |
| division | 2 / 2 | 2162688 / 2162688 |
| inline | 6 / 6 | 2141304 / 2141304 |
| switch | 25 / 25 | 2141304 / 310365 |

Use log: `.work/_state/logs/S11_17_controls_use-20261114-002518.log`.
The real card profiles (3112 bytes total) are retained in
`tests/tools/data/s11_17_controls/`, as the card-training fallback requested by
the amendment. Their names, the `SOURCE` constant in `tools/s11_17_controls.py`, and
compiler version must remain matched; they are not portable host-GCC profiles.

The first matching-profile T1 run passed indirect-call promotion/inlining and
the constant-divisor fast path, but failed three gates. Branch assembly still
takes `je` to the 99% hot call; inverted training reverses that arrangement.
The profile dump does read the correct 99.01% hot edge, so this is not an absent
profile. The inline caller retains `call inline_pgo_hot`. The switch retains
an indexed jump table without a dominant-case guard. These are real missing
transformations for these candidates, not regex spelling differences. The tests
remain unchanged and failing. Log:
`.work/_state/logs/S11_17_controls_green-20261114-002545.log` (2 pass, 3 fail).
No native timing result for the controls is claimed. The assembly prerequisite
has not been met; compiler changes are outside this research ticket's `gcc: no`
scope. Lead direction is needed on revised candidates and card retraining versus
separate compiler investigation tickets.

The generator now writes LF explicitly, preserving the lead's shell-script
repair under Windows Python as well as Cygwin Python. PowerShell invocations
above include the lead's required `-ExecutionPolicy Bypass`. The generated timing
script is `.work/_shared/S11-17/controls/controls-lead.ps1`; when cleared by the
lead, run it through `tools/run.py` and PowerShell with that option, first
`-Phase pilot`, then `-Phase confirm`. Its binaries are staged and linted, but
this is not a request to accept the failed controls as qualified.

### Revised positive-control candidates, 2026-11-14

Following the lead's 01:02 answer, the branch's hot side is now straight-line
unsigned arithmetic; its T1 gate requires zero-input fall-through into that
arithmetic while preserving the cold call. The inline helper has six dependent
shift/xor/multiply steps instead of 24. GCC 16's `gcc/params.opt` sets
`max-inline-insns-auto` to 15; `gcc/opts.cc` raises it to 30 at `-O3`.
`gcc/ipa-inline.cc`, `inline_insns_auto` and `want_inline_small_function_p`,
scale the limit for the known-hot hint (default hint factor 200%). The new
candidate targets that interval: plain `-O2` still keeps the hot call; matched
profile-use must remove it. Its green result remains unmeasured.

The switch is dropped as a gate: GCC has no profile-driven dominant-case
peeling, per the lead's capability assessment. No follow-up ticket is requested.
Its replacement, `loop`, calls a helper containing a variable-trip recurrence.
Matching training uses trip count three for 99% of elements; inverted training
uses varied counts 20 through 51 for 99%. Evaluation uses the matching mix with
the separate evaluation seed. The T1 assembly gate requires at least three
recurrence bodies before the first backward branch in that helper, identifying
loop peeling rather than an arbitrary assembly difference. GCC's
`gcc/tree-ssa-loop-ivcanon.cc`, `try_peel_loop`, uses estimated iterations for
this transformation. Indirect-call and division kernel semantics and gates
are unchanged. Every batch still checks its separately compiled reference.

All ten revised atomic training binaries compiled and linted. Staging then
failed writing the existing lead-owned
`.work/_shared/S11-17/controls/controls-train.sh` with `PermissionError`.
No attempt was made to bypass that permission. Log:
`.work/_state/logs/S11_17_controls_revised_stage-20261114-011218.log`.
The revised plain `-O2` T1 run failed all five transformation assertions, with
no test errors; the loop helper has one recurrence body. Red log:
`.work/_state/logs/S11_17_controls_revised_red-20261114-011318.log`.

The lead must resolve the script's ownership, then regenerate scripts without
repeating the successful builds:

```
python tools/run.py --name S11-17-controls-revised-scripts --inputs tools/s11_17_controls.py -- ../_shared/toolchain/cygwin/bin/python3.12.exe tools/s11_17_controls.py scripts
python tools/run.py --name S11-17-controls-revised-train -- powershell -NoProfile -ExecutionPolicy Bypass -File ../_shared/S11-17/controls/controls-lead.ps1
```

Use the shared Cygwin and cross bin directories on PATH as above. The second
command is **training only**, under three minutes including its timeout;
the script runs ten correctness checks in parallel and returns ten profiles.
Its path is `.work/_shared/S11-17/controls/controls-lead.ps1`. Script generation
writes LF, and the PowerShell command includes `-ExecutionPolicy Bypass`.
The existing staged training script/file list still names the old switch:
do not run it until regeneration succeeds. Likewise do not run the old timing
files. A combined training/timing run cannot qualify the changed candidates
before the host imports profiles, builds use variants and checks T1 green.

Retrain all ten variants because source locations changed even for the two
semantically unchanged kernels. Earlier captured profiles and the checked-in
fixtures describe the original source, not this revision. Replace those
fixtures with the new genuine card profiles after a successful use build.
Return `controls/train.stdout` and `controls/train.stderr`; the engineer then
imports profiles with the existing fatal missing/mismatch checks, verifies
positive counts and T1 green, and stages the pilot and confirm timing phases.
Revised profile-use correctness, transformations and native timings are pending.

### Revised profile-use result and branch retry, 2026-11-14 02:40 EST

The lead's 01:32 training capture decoded successfully: ten checks and exactly
ten profiles. All matched/inverted use objects compiled with fatal missing and
mismatched profile diagnostics, and all five timing binaries linked and linted.
Use log: `.work/_state/logs/S11_17_controls_revised_use-20261114-023827.log`.
Positive edges and maximum counts were:

| Kernel | Positive edges, matched / inverted | Maximum count, matched / inverted |
|---|---:|---:|
| branch | 5 / 5 | 2141304 / 2141304 |
| indirect | 5 / 5 | 2162688 / 2162688 |
| division | 2 / 2 | 2162688 / 2162688 |
| inline | 6 / 6 | 2141304 / 2141304 |
| loop | 5 / 5 | 7173672 / 76031472 |

T1 passed indirect promotion/inlining, division specialization, hot-call
inlining and short-loop peeling. Branch alone failed: both base and matching
builds jumped backwards to the zero-input arithmetic; inverted training made
that arithmetic fall through. This is not a passing branch control.
Log: `.work/_state/logs/S11_17_controls_revised_green-20261114-023842.log`.

The next branch candidate isolates the decision in a `noipa` helper, outside
the accumulation loop. An explicit unlikely static expectation for zero is
opposed by the matching 99%-zero training input. The required transformation
remains zero-input fall-through into arithmetic, preserving the other outcome
through a cold helper call or tail jump. Plain `-O2` emits `testl; je` to the
arithmetic and falls through to the cold tail jump. All five plain gates fail
by assertion, with no errors, in
`.work/_state/logs/S11_17_controls_branch3_red-20261114-024016.log`.
Matching-profile behavior of this new candidate is still unknown.

All ten current atomic training binaries compiled and linted. Regeneration
then failed on the lead-owned `controls-train.sh` with `PermissionError`:
`.work/_state/logs/S11_17_controls_branch3_stage-20261114-023955.log`.
The lead must resolve ownership and run the scripts-only regeneration command
above, then the training command with `-ExecutionPolicy Bypass`. Script path:
`.work/_shared/S11-17/controls/controls-lead.ps1`; training only, under three
minutes. Source line changes require fresh profiles for all ten variants.
The previous timing binaries and checked-in profile fixtures belong to older
sources; do not time them as this revision. Replace fixtures after the next
successful use build. Return `controls/train.stdout` and `controls/train.stderr`.
Native control timing and the full five-gate green result remain pending.

### Train3 profile-use and timing handoff, 2026-11-14 07:52 EST

The lead's 07:44 EST card training at `4954896d` returned ten clean checks
and all ten real profiles in `controls/train3.stdout`. All ten matching/inverted
use objects compiled with fatal missing-profile and coverage-mismatch diagnostics;
all five timing binaries linked and passed binary lint. No missing or mismatched
profile was reported. The current card profiles replace the older fixtures in
`tests/tools/data/s11_17_controls/`, including removal of the obsolete switch data.

| Kernel | Positive edges, matched / inverted | Maximum count, matched / inverted |
|---|---:|---:|
| branch | 7 / 7 | 2162688 / 2162688 |
| indirect | 5 / 5 | 2162688 / 2162688 |
| division | 2 / 2 | 2162688 / 2162688 |
| inline | 6 / 6 | 2141304 / 2141304 |
| loop | 5 / 5 | 7173672 / 76031472 |

All five matching-profile T1 gates now pass: hot zero branch falls through,
indirect target is promoted and inlined, division has a guarded constant-seven
fast path, the hot callee is inlined, and the short loop is peeled. The unchanged
gates were red for plain `-O2` in the branch3 red log above. Use log:
`.work/_state/logs/S11_17_controls_branch3_use-20261114-075123.log`.
T1 log: `.work/_state/logs/S11_17_controls_branch3_green-20261114-075136.log`.
This supersedes the earlier pending/failed assembly results, without claiming
native profile-use correctness or a timing gain.

The fresh LF scripts are staged successfully (log
`.work/_state/logs/S11_17_controls_timing_scripts-20261114-075148.log`).
Lead only, from the S11-17 worktree in an exclusive card turn:

```
python tools/run.py --name S11-17-controls-pilot -- powershell -NoProfile -ExecutionPolicy Bypass -File ../_shared/S11-17/controls/controls-lead.ps1 -Phase pilot
python tools/run.py --name S11-17-controls-confirm -- powershell -NoProfile -ExecutionPolicy Bypass -File ../_shared/S11-17/controls/controls-lead.ps1 -Phase confirm
```

Run pilot first; review correctness and spread before confirm. Each phase visits
full, 3100 and 5100 and runs all five controls with base, matched and inverted
variants on the distinct evaluation seed. Every batch checks its reference sum;
matched and inverted treatments each have adjacent alternating CT/TC pairs
(5 pilot, 10 confirmatory). Native processes are short single-core timing checks.
Nominal timed batches total about 180 seconds across both phases and all profiles,
plus calibration/upload overhead; each profile has a 240-second timeout, keeping
the staged protocol under fifteen minutes absent infrastructure delays. Return
`controls/pilot-{full,3100,5100}.stdout/.stderr` and separately
`controls/confirm-{full,3100,5100}.stdout/.stderr`. Control speedups, spread and the
required loss/reversal under inverted training remain pending. Sprint 12's PGO
regression qualification remains open until those native results are reviewed.

### Positive-control card evaluation, 2026-11-14 08:16-08:21 EST

The lead ran pilot (1.9 minutes) and confirm (2.8 minutes) at `b1151831`,
exclusively on the card with a quiet host. All 30 kernel launches reported
`CONTROL_CHECK pass`; all 900 timed batches reported `check=pass` (300 pilot,
600 confirmatory). Every batch checks against the separately compiled reference.
The engineer performed no native run. These results supersede the historical
pending statements above. T1 remains five red baseline gates followed by five
matched-profile green gates, recorded in the train3 section.

The table gives **time reduction = 100 * (1 - treatment time / adjacent base
time)**: median and observed min-max in percentage points. Positive means faster.
This is the lead's percentage convention; the zlib table instead gives base/PGO
speedup ratios. For example, division saves about 39.1% of time on full confirm,
equivalent to about 1.642 times base throughput. Spread is not a confidence
interval; no pair was removed. Pilot has five pairs per treatment, confirm ten,
with separate adjacent baselines and alternating CT/TC order.

| Phase | Profile | Kernel | Matched: median (min to max) | Inverted: median (min to max) |
|---|---|---|---:|---:|
| pilot | full | branch | +2.07% (+2.03 to +2.35) | +0.06% (-0.09 to +0.38) |
| pilot | full | indirect | +12.71% (+12.42 to +12.89) | -18.15% (-18.53 to -17.78) |
| pilot | full | division | +38.93% (+38.80 to +39.14) | -17.38% (-17.47 to -17.04) |
| pilot | full | inline | +5.73% (+5.64 to +5.88) | +6.00% (+5.80 to +6.11) |
| pilot | full | loop | +30.14% (+29.89 to +30.40) | +5.87% (+5.63 to +5.92) |
| pilot | 3100 | branch | +2.23% (+2.01 to +2.31) | -0.04% (-0.12 to +0.39) |
| pilot | 3100 | indirect | +12.72% (+12.41 to +13.05) | -18.18% (-18.24 to -18.11) |
| pilot | 3100 | division | +39.02% (+38.88 to +39.19) | -17.14% (-17.27 to -16.96) |
| pilot | 3100 | inline | +5.81% (+5.74 to +5.91) | +5.78% (+5.66 to +5.98) |
| pilot | 3100 | loop | +30.18% (+29.88 to +30.32) | +5.83% (+5.64 to +5.90) |
| pilot | 5100 | branch | +2.11% (+2.01 to +2.40) | +0.31% (-0.04 to +0.42) |
| pilot | 5100 | indirect | +12.76% (+12.65 to +12.88) | -18.17% (-18.31 to -17.97) |
| pilot | 5100 | division | +38.87% (+38.83 to +39.52) | -17.34% (-17.40 to -17.18) |
| pilot | 5100 | inline | +5.73% (+5.61 to +6.03) | +5.63% (+5.18 to +5.88) |
| pilot | 5100 | loop | +30.27% (+30.04 to +31.25) | +5.80% (+5.25 to +5.81) |
| confirm | full | branch | +2.19% (+1.90 to +2.66) | +0.07% (-0.32 to +0.52) |
| confirm | full | indirect | +12.81% (+12.72 to +13.09) | -18.07% (-18.35 to -17.45) |
| confirm | full | division | +39.11% (+38.80 to +39.29) | -16.97% (-17.31 to -16.83) |
| confirm | full | inline | +5.88% (+5.58 to +6.05) | +5.90% (+5.70 to +6.34) |
| confirm | full | loop | +30.35% (+30.02 to +30.83) | +5.69% (+5.31 to +5.97) |
| confirm | 3100 | branch | +2.24% (+1.98 to +2.68) | +0.04% (-0.30 to +0.47) |
| confirm | 3100 | indirect | +12.71% (+12.17 to +13.20) | -18.02% (-18.19 to -17.24) |
| confirm | 3100 | division | +38.97% (+38.80 to +39.12) | -17.00% (-17.18 to -16.74) |
| confirm | 3100 | inline | +5.77% (+5.31 to +6.35) | +5.83% (+5.59 to +5.94) |
| confirm | 3100 | loop | +30.25% (+30.08 to +30.48) | +5.73% (+5.61 to +5.83) |
| confirm | 5100 | branch | +2.06% (+1.89 to +2.39) | +0.11% (-0.08 to +0.52) |
| confirm | 5100 | indirect | +12.57% (+12.06 to +12.88) | -18.27% (-18.58 to -17.81) |
| confirm | 5100 | division | +38.95% (+38.77 to +39.19) | -17.31% (-17.54 to -17.14) |
| confirm | 5100 | inline | +5.73% (+5.50 to +6.87) | +5.84% (+5.65 to +6.33) |
| confirm | 5100 | loop | +30.29% (+29.99 to +30.36) | +5.79% (+5.43 to +5.97) |

Raw captures retain every pair and elapsed time (UTF-16LE):
`.work/_shared/S11-17/controls/pilot-{full,3100,5100}.stdout` and separately
`controls/confirm-{full,3100,5100}.stdout`, with corresponding `.stderr` files.
Logs: `.work/_state/logs/S11_17_controls_pilot-20261114-081627.log` and
`.work/_state/logs/S11_17_controls_confirm-20261114-081824.log`.
No tests or card jobs were rerun for this write-up.

Branch, indirect and division demonstrate profile-dependent gains: approximately
2.2%, 12.7% and 39.0% time reductions. Inverted training removes the branch gain
within observed variation and reverses indirect and division into approximately
18.1% and 17.0% slowdowns. These three qualify under the matching/inverted rule;
the branch's near-zero inverted result is distinct from its consistent matched gain.

Inline is **not demonstrated** as a profile-dependent control: inverted training
matches the approximately 5.8-5.9% time saving of matched training. Its green
assembly gate does not establish a profile-dependent timing benefit.

Loop saves about 30.2% with matching training and 5.7% with inverted training.
Report that residual separately as a profile-independent benefit of the use
build. Matched elapsed time is about 26% lower than inverted, demonstrating a
substantial profile-dependent component. However, loop fails the strict timing
requirement that inverted training show no gain or a loss. The removed switch
remains a GCC capability gap (no profile-driven dominant-case peeling), with no
follow-up ticket requested. No gate or acceptance criterion was weakened.

The whole-program feasibility question is answered: zlib generate/train/use
works with complete matching profiles, positive counts and 90/90 correct launches,
with only a small observed gain. Three controls show that this pipeline can
produce much larger gains where the decisions matter. The full five-control
acceptance clause is not met: inline is not demonstrated and loop retains an
inverted-profile benefit. Per the lead's 08:21 instruction, this final research
result is submitted with those limitations, without claiming all controls passed.

### Lessons from PhiWeather

The lead's 2026-11-13 ticket note reports that PhiWeather's WRF-only GCC 5.1.1
pipeline worked after preserving the `-o` path, but its 0.78% gain was below its
noise bar and its tolerance gate failed by one cell. That result does not settle
GCC-KNC 16 PGO on zlib. Preserve generate/use names, require complete matching
profiles and positive use counts, and evaluate correctness before accepting
timings. Because each zlib run is about 1.25 seconds, the staged protocol uses
five pilot pairs and ten confirmatory pairs per profile, as requested by the lead.
Keep pilot and confirmatory results separate; report paired PGO/base ratios and
variation for each hardware profile before deciding whether PGO pays.

Sprint 12 plan: preserve branch, indirect and division as demonstrated
matched/inverted regression controls for one-flag automatic PGO. Keep all five
assembly gates, but label inline and loop timing qualification incomplete.
Any future inline candidate must distinguish matching from inverted training;
loop reporting must separate its residual profile-independent gain. Do not
claim that the five-control suite is fully qualified from this experiment.

Freeze separate training inputs for development programs; preserve compiler,
source and output names between generate/use; require complete profiles and
positive applied counts, with missing/mismatch diagnostics fatal. Reuse the
completed zlib path for further development-program experiments, retaining plain
-O2 pairs, separate pilot/confirm results and per-profile variation. Zlib's
0.7-0.9% observed median gain does not promise a general performance win.
Never train on held-out programs or the frozen evaluation input.

## Lessons from PhiWeather's first WRF PGO attempt (2026-11-12, for our own PGO work)

Source: our review `docs/reviews/2026-11-12-phiweather-pgo-review.md` (S11-22) of PhiWeather's GCC 5.1.1 k1om
instrumented PGO on WRF (their write-up: `PhiWeather/docs/implementation/PGO_KNC_LESSONS_20261112.md`, read-only).
Apply these when S11-17 and Sprint 12 put PGO on whole programs.

- **Build identity:** GCC 5 hashes the object's `-o` path into non-public function ids, so the `-fprofile-use` build
  must reuse the instrumented `-o` path (check whether GCC 16 does the same before relying on it).
- **Silent failures:** under `-w`, a missing or mismatched `.gcda` is silent. Never build `-fprofile-use` with `-w`;
  treat "profile not found", "coverage mismatch" and checksum warnings as errors, and **enforce** that the profile was
  consumed (positive execution counts in the use build), not only that the code changed.
- **Instrumentation changes the code:** `-fprofile-generate` changes inlining, so the training binary is not the
  production binary; `-fprofile-use` re-enables loop-to-`memset`/`memcpy` idiom recognition (their use build gained
  694 memset and 182 memcpy call sites and grew hot objects 26.8%). Check hot-code growth and helper calls in the A/B.
- **Threads:** GCC 5's counters are not atomic, so they trained one thread per rank; GCC 16 has
  `-fprofile-update=atomic` (we already use it, S9-18), which lets training use the production thread layout.
- **Representativeness is the main risk:** train on inputs and layouts like production; exclude warm-up from both
  training and the timing statistic consistently; keep training and evaluation inputs distinct and never train on
  held-out programs; when merging profiles (`gcov-tool`), know that the default weights cases unequally.
- **Where PGO pays:** branchy, call-heavy, indirect-dispatch code (our 19-21% microcases, SQLite/zlib-style code), not
  regular floating-point loops with predictable branches (their near-zero WRF result is plausible even with correct
  feedback). Diagnose a restricted-flags twin against the full PGO build before adding objects; check hot/cold
  placement (`-freorder-functions`, `-freorder-blocks-and-partition`); value profiling is on by default.
- **Measurement:** one A/B pair cannot detect 1-2%. Freeze one statistic, run about 5 pilot pairs to estimate the paired
  spread, then a frozen confirmatory block (about 10 pairs at 1% spread, more if larger), balanced ordering (C T T C),
  keeping every valid result (ADR-0010, ADR-0015).
- **Numerics:** a PGO image is not bitwise identical (x87 rounding can change through spills); validate with a
  calibrated tolerance gate that is shown to reject a faulty result.
