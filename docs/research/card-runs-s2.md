# Sprint 2 native checks: S2-10 handoff

Native status: **lead reports 9 of 10 passed; counter rerun pending**. The
lead's 12:38 ticket answer reports byte-exact stdout and exit 0 for the first
nine programs, with one ledger start/finish pair each, no card fault and an
unchanged boot ID. The counter exited 127 because the card lacks
`libatomic.so.1`. Exact boot IDs and card minutes still require the lead's
result JSON records below; this engineer has not run a native check.
The owner's decision recorded on S2-10 at 11:20
on 2026-11-03 assigns every card job to the interactive lead. This engineer
session prepares the batch only; no connection, card configuration or key is
read. Boot IDs and card minutes remain pending until the lead records each
run's result JSON here. Host reference execution is not native acceptance.

## Build and expected outputs

The shared GCC checkout is clean at merged `knc`, commit
`80bc88d9f9ecc1f460e079def55b40c72627c111` (S2-06 merge). The compiler is
`.work/_shared/gcc-build/gcc/xgcc.exe`. Every GCC 16 link uses S1-06's bridge:
donor 5.1.1 `crtbegin.o`, `crtend.o` and `libgcc` through `-B`, the donor
`cross/k1om-mpss-linux/lib64` through `-L`, and temporary `gcc_s`/`atomic`
AS_NEEDED linker scripts. The sysroot is `.work/_shared/toolchain/sysroot`.
No compiler or runner implementation changes belong to this handoff.

All handoff files live in `.work/_shared/tmp/S2-10/`, outside git. The build
recipe is `prepare.py` there; its checkout argument selects the source root.
It overwrites its outputs and deletes temporary host executables and link
objects (deferred Windows file locks are cleaned up afterward). From a Cygwin
shell in the S2-10 worktree, the build commands are:

```sh
export PATH="$PWD/../_shared/toolchain/cross/bin:$PWD/../_shared/toolchain/cygwin/bin:$PATH"
../_shared/toolchain/cygwin/bin/python3.12.exe tools/run.py \
  --name S2-10-merged-compiler \
  --inputs tools/toolchain.py ../_shared/gcc/gcc/config/i386 -- \
  ../_shared/toolchain/cygwin/bin/python3.12.exe tools/toolchain.py gcc16 --resume
../_shared/toolchain/cygwin/bin/python3.12.exe tools/run.py \
  --name S2-10-prepare --inputs tests/t2 tests/t1/knc-atomics.c \
  tests/t1/knc-spin-hint.c tests/regress/knc-secondary-pressure.c \
  tests/acceptance/m1_affine ../_shared/tmp/S2-10/prepare.py -- \
  ../_shared/toolchain/cygwin/bin/python3.12.exe ../_shared/tmp/S2-10/prepare.py .
```

Build results on 2026-11-03:

- Shared merged compiler refresh: PASS, exit 0.
  Log: `.work/_state/logs/S2_10_merged_compiler-20261103-121536.log`.
- Initial preparation: donor hello and affine builds and both host references
  passed, then cleanup of `m1_affine-host.exe` raised a Windows
  `PermissionError`. No target program ran on the host.
  Log: `.work/_state/logs/S2_10_prepare-20261103-123009.log`.
- Preparation resumed with `prepare.py . --resume-after-affine`: PASS, exit 0;
  ten target executables, ten expected-output files and `batch.txt` ready.
  The already passing hello/affine steps were retained. Affine's expected
  stdout was recovered from its successful host-reference log above.
  Log: `.work/_state/logs/S2_10_prepare-20261103-123044.log`.
- All six distinct host references passed: hello, affine, scalar ABI, varargs,
  pressure and the exact-total pthread counter. Deferred host executable
  cleanup completed after preparation. No native checks were run.

`batch.txt` is tab-separated, with columns `program`, `arguments` (a JSON
array), `memoryMB` (MiB), and `expected`. Paths are relative to its directory.
Each program has its own `<program-stem>.expected.txt`, generated as raw stdout
bytes from a successful Cygwin host build of the same source. A shared source
reference is executed once, then used for each compiler combination. All jobs
have no arguments, require exit 0 and exact stdout, and declare 128 MiB.

| Order | Executable | Source and purpose |
| --- | --- | --- |
| 1 | `hello.mic` | Donor build of shared `hello.c`: `puts("hello from KNC")`. |
| 2 | `m1_affine.mic` | Donor build of `tests/acceptance/m1_affine/{driver,loops}.c`; guard pages, tails and scalar FP. |
| 3 | `scalar-gcc16-caller.mic` | GCC 16 caller / donor callee from `tests/t2/knc-scalar-abi-{caller,callee}.c`. |
| 4 | `scalar-donor-caller.mic` | Donor caller / GCC 16 callee from the same sources. Both executables include the callback in the reverse direction. |
| 5 | `varargs-donor.mic` | Donor-only build of `tests/t2/knc-varargs-{caller,callee}.c`; native output oracle. |
| 6 | `varargs-gcc16.mic` | GCC 16-only build of the same varargs sources. |
| 7 | `varargs-gcc16-caller.mic` | GCC 16 caller / donor callee. |
| 8 | `varargs-donor-caller.mic` | Donor caller / GCC 16 callee. |
| 9 | `secondary-pressure.mic` | GCC 16 build of `tests/regress/knc-secondary-pressure.c`, with `PRESSURE_MAIN`; seven seeds compared with the host. |
| 10 | `atomic-counter.mic` | Rebuilt from S2-06 T2: `tests/t2/knc-atomic-counter.c` plus `tests/t1/knc-{atomics,spin-hint}.c`. Four threads, 100000 increments each. |

Scalar ABI builds use `-O2 -ffp-contract=off`. Varargs builds use
`-O2 -fno-builtin -march=knc`. The pressure test uses S2-04's flags:
`-O2 -fomit-frame-pointer -fno-tree-vectorize -ffp-contract=off -DPRESSURE_MAIN`
and `-march=knc` for the target. The counter uses `-O2 -pthread`. Affine
uses `-O2 -ftree-vectorize -ffp-contract=off`. No fast-math option is added.

### Counter static-library follow-up (2026-11-03)

Following the lead's 12:38 instruction, rebuilt only `atomic-counter.mic`
with the same shared GCC 16 compiler and S1-06 donor bridge, adding the donor
archive `toolchain/cross/k1om-mpss-linux/lib64/libatomic.a` after its sources.
`prepare.py` now includes that archive for future preparation as well.
The expected-output file and batch row still apply: exit 0, exact totals
of 400000, no arguments, 128 MiB. The nine passing programs were not rebuilt
or rerun, and no host reference was repeated.

The focused recipe is `.work/_shared/tmp/S2-10/relink-atomic.py`. With the
toolchain PATH above, it was invoked through:

```sh
../_shared/toolchain/cygwin/bin/python3.12.exe tools/run.py \
  --name S2-10-static-atomic \
  --inputs tests/t2/knc-atomic-counter.c tests/t1/knc-atomics.c \
  tests/t1/knc-spin-hint.c ../_shared/tmp/S2-10/relink-atomic.py -- \
  ../_shared/toolchain/cygwin/bin/python3.12.exe \
  ../_shared/tmp/S2-10/relink-atomic.py .
```

Result: PASS, exit 0. The recipe checks the rebuilt executable with donor
`readelf -d` and fails if any `NEEDED` entry names libatomic; no such entry
remains. Log:
`.work/_state/logs/S2_10_static_atomic-20261103-124014.log`.
Native execution of this rebuilt counter remains pending with the lead.

Expected stdout includes:

- Hello: `hello from KNC` followed by a newline.
- Affine: `ACCEPT-PASS scalar=3.00 failures=0` followed by a newline.
- Both scalar cross-links: `S2-02 scalar ABI PASS` followed by a newline;
  the program checks float/double, mixed integers, ten FP arguments, both
  structs and callbacks before printing it.
- Each varargs program: two copies of `17|2.500|3.1250|-0.75|-9`, each followed
  by a newline. It checks direct `snprintf`, forwarded `vsnprintf`, and sums
  of 0/1/8/10 doubles internally. Compare all GCC 16 variants with the actual
  donor-only stdout byte for byte as well as with their expected files.
- Counter: `atomic=400000 sync=400000 expected=400000` followed by a newline.
- Pressure: seven lines of four hexadecimal values, in its expected file.

## Lead execution and native results

Use the merged `tools/card_run` exclusively, serially in batch order, with the
owner-supplied configuration and its `memoryMB` set to the declared 128 MiB.
The runner obtains physical cores 30-59 and handles the shared ledger, CPU
affinity, memory admission, `claude-` staging and cleanup as documented in
`docs/card-run.md`. Use its existing single overwritten result JSON; record
the result before starting the next job. This engineer did not generate any
runtime result JSON.

For each row record result class, program exit, stdout comparison, both boot
IDs and card minutes here. Do not publish performance figures. Stop on a
refusal or infrastructure failure and report it on S2-10. If a refusal lists
unknown processes, include their exact names; only the owner can approve
baseline names. Report a mismatch with its source, actual and expected
outputs, and the compiler commit above; do not fix compiler behavior here.

| Executable | Native result | Boot ID before / after | Card minutes |
| --- | --- | --- | --- |
| `hello.mic` | exit 0, stdout matches byte for byte (lead run, job `claude-d9f5ef6c`) | `e9bfb0ab` / same | 0.0237 |
| `m1_affine.mic` | exit 0, stdout matches byte for byte (lead run, job `claude-855d0925`) | `e9bfb0ab` / same | 0.0242 |
| `scalar-gcc16-caller.mic` | exit 0, stdout matches byte for byte (lead run, job `claude-ab414606`) | `e9bfb0ab` / same | 0.0237 |
| `scalar-donor-caller.mic` | exit 0, stdout matches byte for byte (lead run, job `claude-da525b2a`) | `e9bfb0ab` / same | 0.0240 |
| `varargs-donor.mic` | exit 0, stdout matches byte for byte (lead run, job `claude-feb5be07`) | `e9bfb0ab` / same | 0.0237 |
| `varargs-gcc16.mic` | exit 0, stdout matches byte for byte (lead run, job `claude-f9e5bc70`) | `e9bfb0ab` / same | 0.0237 |
| `varargs-gcc16-caller.mic` | exit 0, stdout matches byte for byte (lead run, job `claude-68564c29`) | `e9bfb0ab` / same | 0.0239 |
| `varargs-donor-caller.mic` | exit 0, stdout matches byte for byte (lead run, job `claude-d6cb3b3d`) | `e9bfb0ab` / same | 0.0234 |
| `secondary-pressure.mic` | exit 0, stdout matches byte for byte (lead run, job `claude-999a15ee`) | `e9bfb0ab` / same | 0.0237 |
| `atomic-counter.mic` | exit 0 after static-libatomic rebuild (first run exit 127, libatomic.so.1 missing); stdout matches (job `claude-9ec5937a`) | `e9bfb0ab` / same | 0.0245 |

The lead ticks the other tickets' native lines only after their corresponding
native comparisons pass.

## S2-08: GCC 16 own-runtime batch prepared for the lead

Native status: **NOT RUN by this engineer**. This is the host preparation
handoff requested by S2-08; every card invocation belongs to the interactive
lead. GCC source/build is the merged `6ea9258d818` (S2-07), with its own
`gcc-build/gcc/libgcc.a`, `crtbegin.o` and `crtend.o`. There is no donor `-B`
or test-written `*_asneeded` script in this batch.

The retained handoff is `.work/_shared/tmp/S2-08/batch.txt`, in S2-10's TSV
format. It lists nine jobs: donor and GCC 16 twins of hello, scalar arithmetic
in float/double/long double, and printf of int/double/long double; the S2-05
compare table; the S2-07 integer/soft-float helpers; and `claude-torture`.
The arithmetic exercises addition, subtraction, multiplication and division
without fast math or FP contraction. Inexact thirds are stored in volatile
float, double and long double objects and printed with `%.9g`, `%.17g` and
`%.21Lg` to expose rounding or precision-control differences in the donor
comparison. Each of the nine jobs has its own expected-output file.

Hello/scalar/printf expectations currently come from host executions of the
same sources. **The lead must run each donor twin first and confirm or replace
its expected output with donor stdout before comparing its GCC 16 twin.** No
donor native output has been invented. The comparison reference uses S2-05's
host adapter for the emitted x87 functions and the independent integer-rank
oracle: 833 checks per type, 2499 total, zero failures including invalid flags.
The helper reference is a host run of S2-07's unchanged fixture: four integer
lines and one soft-float line, including infinities, NaN and a denormal.

The torture selection is the first 256 top-level `gcc.c-torture/execute/*.c`
in lexical filename order, `20000112-1.c` through `20031201-1.c`, chosen before
compilation. All 256 compile and link at `-O2 -march=knc`, with `-lm` and GCC
16's own libgcc. Unselected `dg-options` and `dg-additional-options` are
applied as in S1-05; directives with target selectors are ignored. The tracked
summary is `tests/baseline/gcc16-torture-execute.txt`; `compile.tsv` in the
handoff directory records every source, result, staged filename and option.
Per-source `.build.log` files retain warnings and link diagnostics there.

`claude-torture` is linked by GCC 16 with its own libgcc and dynamically
against the shared sysroot glibc, like hello. It needs no PhiWeather path or
bootstrap static glibc. Readelf reports interpreter
`/lib64/ld-linux-k1om.so.2` and NEEDED `libc.so.6`.
It reads `claude-torture.list`, runs each child
in a separate owned process group with a two-second wall limit, disables core
dumps and prints exactly one `PASS`/`FAIL`/`TIMEOUT name` line per child on
stdout. Failure diagnostics and raw wait status go to stderr before cleanup;
exit is 1 if any child fails or times out, 125 for driver infrastructure errors.
The host check exercised all three classifications and preserved failure
diagnostics. It is a driver check, not native KNC validation.

For the torture row, run `bash .work/_shared/tmp/S2-08/run-torture.sh` from
the merged checkout under Cygwin. The script invokes only `tools/card_run`,
with all 257 extra files supplied through S2-14's `--file`, a 542-second
execution limit and a 900-second transport limit for the many sequential
uploads. Use the configured 128 MiB memory limit from the batch. Driver,
tests, manifest and runner helper total 6,270,785 bytes including a 64 KiB
watchdog reserve, below the configured 67,108,864-byte staging cap. Children
inherit the runner's affinity and per-process memory limit.

The lead records byte-exact stdout comparisons, exit status, boot IDs and
card minutes here. For each torture failure, retain its stderr/source and
classify it as a compiler bug, a test needing a missing runtime, or a test for
another target. There are currently no native results or native failure
classifications. Stop on runner refusal or infrastructure failure.

Host logs in `.work/_state/logs/`: `S2_08_prepare-20261103-132843.log`
(basic builds/references passed; Cygwin GCC ICE compiling the combined host
compare fixture), `S2_08_remaining-20261103-132911.log` (adapter reference,
helper reference, initial driver and 256/256 compile/link PASS), and
`S2_08_driver_final-20261103-133100.log` (earlier static driver and host outcome
checks PASS). A separate host-driver check initially lacked the Cygwin DLL
PATH; `S2_08_driver-20261103-133002.log` records that infrastructure failure.
`S2_08_review_fixes-20261103-133411.log` records the scalar donor/GCC 16
rebuilds, host rounding output, dynamic driver link/readelf check and updated
staging cap check, all PASS. Host thirds are provisionally `0.333333343`,
`0.33333333333333331` and `0.333333333333333333342`; donor confirmation is
still pending. `python tools/prepare_s2_08.py --refresh-affected`, invoked
through `tools/run.py`, reuses the prior torture compile summary and rebuilds
only scalar-fp and the driver. Other passing program builds, driver behavior
checks and the 256-test sweep were not repeated.
