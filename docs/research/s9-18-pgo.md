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

### Positive controls (lead's 2026-11-13 amendment; assembly gate incomplete)

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

Sprint 12 plan: complete the positive-control assembly and native timing gates
before treating one-flag automatic PGO as qualified. Preserve matched/inverted
controls as regression cases and require the inverted profile to lose or reverse
the gain. Zlib's completed cycle establishes functionality, with no missing or
mismatched profiles and only a small observed median gain. Freeze a separate
training input per development program, preserve compiler/source/output names
between generate/use, and keep diagnostics fatal. Extend to further development
programs only after this complete-program path works; retain plain -O2 pairs and
keep training separate from frozen evaluation and held-out programs.
