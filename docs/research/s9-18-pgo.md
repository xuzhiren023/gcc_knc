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

## S11-17: complete development zlib program (evaluation pending)

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
missing profiles. Native correctness of the use binary and paired evaluation
timings remain pending on all three profiles. No speedup is claimed.

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

Sprint 12 plan: first finish this train/use/evaluation cycle and record every
missing/mismatched profile and per-profile paired time ratio. Freeze a separate
training input per development program, preserve compiler/source/output names
between generate/use, and keep diagnostics fatal. Extend to further development
programs only after this complete-program path works; retain plain -O2 pairs and
keep training separate from frozen evaluation and held-out programs.
