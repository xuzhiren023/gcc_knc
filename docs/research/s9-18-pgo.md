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
