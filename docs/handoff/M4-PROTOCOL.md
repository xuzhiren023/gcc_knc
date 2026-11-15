# M4 optional-mode freeze for S13-01

Frozen by S12-09 at GCC `b2ce6a9eebffcb5c23512c2cec4ba3d8b9e2f046`.
S13-01 must read this file before staging its optional panels. The S13 gate
uses lane 1, `$SHARED/gcc-knc-16.2.0`, exclusively. Every frozen GCC-KNC
line below refers to that prefix at the revision above. Lane 2 is stale
(Sprint 11 head `619e14b479a`, installed 2026-11-14 11:50 EST) and is not
validated by S12-09. ADR-0015 remains
the scoring authority. The primary serial flags remain donor `-O2` (SQLite's
previously frozen assembling level excepted) and GCC-KNC `-O2 -march=knc`.
Optional results never enter that score. Build or correctness failures remain
visible panel failures; there is no optimization-level fallback in these panels.

## Build lines

Use `tools/corpus.py:build_program` for the frozen sources, workload defines,
language selection, include paths, link paths, and identical authorized HPCG
shared-list fix. Replace only its `flags` argument as follows; preserve the
remaining command arguments and archive the complete emitted build.log.
`variant=serial` removes OpenMP and adds `HPCG_NO_OPENMP` for HPCG.

| Label | Donor flags | GCC-KNC flags | Variant |
| --- | --- | --- | --- |
| O3 | `-O3` | `-O3 -march=knc` | serial |
| phinix | `-O2` reference | `-O2 -march=knc -mphinix` | serial |
| OpenMP | unavailable | `-O2 -march=knc -fopenmp` | openmp |

The OpenMP build path adds `-fopenmp` once through the existing per-program
extra arguments. It covers STREAM, NPB-CG/EP/MG/IS and HPCG only. Its exact
panel label is `the donor toolchain has no OpenMP runtime`. Use each profile's
compute-core count times density 1, 2 and 4, fixed teams and GOMP affinity,
as implemented by the corpus harness. Serial panels allocate one worker.
Run all panels under full, 3100 and 5100 resource profiles, retaining the
profile interpretation and correctness checks of the primary protocol.

The equivalent corpus extra-flag configuration is:

```json
{"gcc-5.1.1": [["-O3"]], "gcc-knc": [["-O3", "-march=knc"], ["-O2", "-march=knc", "-mphinix"]]}
```

This describes the flag choices, not authorization for this ticket to build
held-out programs. S12-09 performs no corpus staging or measurement.
The gate must label the extra serial configurations as panels when consuming
the corpus records; the harness's generic serial record label alone is not a
scoring specification. No missing optional measurement is a primary result.
The gate must schedule the phinix row against a fresh donor `-O2` reference;
the generic flag-index pairing does not supply that reference for index 2.

## PGO build and training lines

The bounded whole-program PGO implementation is zlib in
`tools/s11_17_pgo.py`; freeze that program and its separate training input.
Its compiler is the installed GCC-KNC prefix. The complete compiler argument
sequence (shell variables below denote absolute paths) is:

```sh
CC="$SHARED/gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc"
LIB="$SHARED/corpus-build/sources/zlib-1.3.1"
BUILD="$SHARED/S11-17/build"
SUPPORT="$PROJECT/tools/corpus"
SYSROOT="$SHARED/toolchain/sysroot"
# Run in BUILD; generate and use keep the same directory and output name.
"$CC" -O2 -march=knc -fprofile-generate -fprofile-update=atomic \
  -I"$LIB" -DCORPUS_ZLIB \
  "$LIB/adler32.c" "$LIB/crc32.c" "$LIB/deflate.c" "$LIB/infback.c" \
  "$LIB/inffast.c" "$LIB/inflate.c" "$LIB/inftrees.c" "$LIB/trees.c" \
  "$LIB/zutil.c" "$LIB/compress.c" "$LIB/uncompr.c" "$SUPPORT/roundtrip.c" \
  -Wl,-rpath-link,"$SYSROOT/lib64" -Wl,-rpath-link,"$SYSROOT/usr/lib64" \
  -lm -o "$BUILD/workload"
"$CC" -O2 -march=knc -fprofile-use -Werror=missing-profile \
  -Werror=coverage-mismatch -fdump-ipa-profile-details \
  -I"$LIB" -DCORPUS_ZLIB \
  "$LIB/adler32.c" "$LIB/crc32.c" "$LIB/deflate.c" "$LIB/infback.c" \
  "$LIB/inffast.c" "$LIB/inflate.c" "$LIB/inftrees.c" "$LIB/trees.c" \
  "$LIB/zutil.c" "$LIB/compress.c" "$LIB/uncompr.c" "$SUPPORT/roundtrip.c" \
  -Wl,-rpath-link,"$SYSROOT/lib64" -Wl,-rpath-link,"$SYSROOT/usr/lib64" \
  -lm -o "$BUILD/workload"
```

Host preparation, lead-only native training, then host profile import/use:

```text
python tools/run.py --name s13-pgo-stage --inputs tools/s11_17_pgo.py tools/corpus -- ../_shared/toolchain/cygwin/bin/python3.12.exe tools/s11_17_pgo.py stage
python tools/card_run --timeout 600 --threads 1 --file-list .work/_shared/S11-17/train-files.txt .work/_shared/S11-17/train/train.sh > .work/_shared/S11-17/train.stdout 2> .work/_shared/S11-17/train.stderr
python tools/run.py --name s13-pgo-use --inputs tools/s11_17_pgo.py -- ../_shared/toolchain/cygwin/bin/python3.12.exe tools/s11_17_pgo.py use ../_shared/S11-17/train.stdout
```

The generated training script runs `./workload` with
`GCOV_PREFIX="$PWD/gcda" GCOV_PREFIX_STRIP=64`, then exports the real gcda
data. The training input is the script's fixed 8 MiB seed-29 data; evaluation
retains corpus seed 11. Require the clean training correctness marker, the
exact twelve profile files and positive measured edge counts. Preserve native
failure output. Do not manufacture profiles or train on held-out evaluation.

This recipe provides a GCC-KNC-only PGO feasibility panel against its own
untrained `-O2 -march=knc` binary. A donor-PGO competitiveness panel remains
unqualified: the existing implementation does not generate donor profiles.
Do not label this as GCC-KNC PGO versus donor PGO or extrapolate it to all
17 programs. A matched donor-PGO panel is not part of M4.

## Known limits and lead evidence

Carry S12-34 and S12-38 (O3 ICEs), S12-42 and S12-31's zlib loss (minor) into
the M4 report. These are ticket-reported limits, not new native observations
from this batch. The owner cut the Sprint 11/Sprint 12 corpus comparison and
per-program donor comparison from S12-09; S13-01 performs its final-head gate.
Lead card window 9 (2026-11-15, 18:31-18:51Z): execute suite 1680 PASS,
1 FAIL (`930529-1.c`, exit 4). The S12-09 builder misses its brace-form
`dg-options { "-fwrapv" }`; the emitted command omits `-fwrapv`. This is the
known S3/S6 harness miss, not a compiler result; no rerun was performed.
See `tests/baseline/S12-09-t0-t2.txt` for the builder command and evidence.

All six timed vmath launches were valid (zero invalid rows). Vector speedup
was 1.22-3.40x except double log at density 1: 0.85x (l2), 0.87x (mem).
At density 4 double log was 1.25-1.32x. Carry density-1 double log as a known
minor limit into the M4 report; no Sprint 12 fix is in scope. Summary log:
`.work/_state/logs/s12_09_vmath_summary-20261115-135441.log`.

Lead x86 identity at `b2ce6a9eebf` versus `releases/gcc-16.2.0`,
`-O2 -mavx512f`: identical=1962, different=0, both-failed=41 (header-only
failures in both trees), errors=0. Log:
`.work/_state/logs/s12_09_x86-20261115-100743.log`.
