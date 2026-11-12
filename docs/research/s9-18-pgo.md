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

## S11-17: complete development zlib program (card training pending)

`tools/s11_17_pgo.py` reuses the S11-18 zlib 1.3.1 source list,
`roundtrip.c`, `-O2 -march=knc`, includes, defines and linker search paths.
Both plain and `-fprofile-generate -fprofile-update=atomic` programs compiled
and passed binary lint. They are staged as
`.work/_shared/S11-17/{base,train}/workload`. No GCC compiler build was needed.
The host stage passed once; log:
`.work/_state/logs/S11_17_stage-20261112-180819.log`.
No program has run natively for this ticket yet.

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
3. Once the use build passes lint, the lead runs
   `python tools/run.py --name S11-17-eval -- powershell -NoProfile -File ../_shared/S11-17/lead.ps1 -Evaluate`.
   It stages three adjacent base/PGO pairs per full 7120, 3100 and 5100 profile,
   alternating AB/BA/AB, with one pinned worker. The unchanged S11-18 launcher
   measures CLOCK_MONOTONIC_RAW launch-to-exit latency, then checks donor decoding
   and corruption rejection. Each launch retains its stdout/stderr in S11-17.

What remains unproven: real profile generation/return, the profile-use build,
profile diagnostic counts and native correctness/timing on all three profiles.
The use build cannot be produced honestly before the lead supplies training data.
Do not interpret instrumented compilation or lint as an end-to-end PGO result.

Sprint 12 plan: first finish this train/use/evaluation cycle and record every
missing/mismatched profile and per-profile paired time ratio. Freeze a separate
training input per development program, preserve compiler/source/output names
between generate/use, and keep diagnostics fatal. Extend to further development
programs only after this complete-program path works; retain plain -O2 pairs and
keep training separate from frozen evaluation and held-out programs.
