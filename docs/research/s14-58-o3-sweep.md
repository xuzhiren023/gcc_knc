# S14-58: installed-prefix torture and vect sweep

Compiler: `.work/_shared/gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc.exe`.
This records the installed prefix, without asserting its GCC source commit.
No GCC change or build. Window 17: 1,797 native PASS, six FAIL, zero TIMEOUT;
x86 not run. Corrected-harness native results are still pending.
The affected harness subset has been rebuilt and linted at both O2 and O3;
the staged list now contains the corrected O3 binaries.

## Scope and method

The original recursive sweep attempted 6,259 C inputs at both `-O2` and
`-O3 -march=knc` (12,518 configurations), using eight host workers.
Successful compilation was followed by assembly with `--march=k1om`, source
lint and decoded-object lint. Successful O3 execute objects were linked with
`-lm` and the installed runtime, then executable linted before staging.
Per-source unselected `dg-options` and `dg-additional-options` precede the
requested architecture and level. Target-selected options, effective-target
requirements, expected diagnostics, dump scans and auxiliary-source directives
are not interpreted. These are sweep outcomes, not DejaGNU pass rates.

The original 144 O3 builtins link errors were harness misuse, not compiler
failures. Per the lead's 2026-11-17 answer, only builtins were rerun, at both
levels, using `builtins/builtins.exp`: 59 primary tests, each with its
`<name>-lib.c` companion and `lib/main.c`. Companions include their required
`lib/*.c` implementations; those are not independent executable tests.
All three translation units use the harness flags:
`-fno-tree-dse -fno-tree-loop-distribute-patterns -fno-tracer -fno-ipa-ra
-fno-inline-functions`. They are compiled separately, assembled and linted;
O3 objects are then linked together and the executable is linted. One rule
set in `tools/torture_compile.py` serves the host sweep and staging.
The 146 raw builtins inputs are superseded by these 59 harness cases.

## Host results

Corrected counts below replace raw builtins outcomes with the harness rerun.
Pass includes successful O3 linking/executable lint for execute tests.

| Suite | Level | Cases | Pass | Compiler diagnostic | ICE | Input asm rejection | Assembler/lint/infrastructure/link failure |
|---|---|---:|---:|---:|---:|---:|---:|
| compile | O2 | 2003 | 1969 | 32 | 0 | 2 | 0 |
| compile | O3 | 2003 | 1969 | 32 | 0 | 2 | 0 |
| execute (including harness builtins) | O2 | 1820 | 1803 | 17 | 0 | 0 | 0 |
| execute (including harness builtins) | O3 | 1820 | 1803 | 17 | 0 | 0 | 0 |
| vect | O2 | 2349 | 2168 | 181 | 0 | 0 | 0 |
| vect | O3 | 2349 | 2166 | 182 | 1 | 0 | 0 |
| builtins rerun (included in execute above) | O2 | 59 | 59 | 0 | 0 | 0 | 0 |
| builtins rerun (included in execute above) | O3 | 59 | 59 | 0 | 0 | 0 | 0 |

The raw sweep took 3949.887 seconds; the builtins rerun took 109.072 seconds.
Two original O2 execute compilations exceeded 60 seconds and passed the single
600-second retry (`memcpy-a1.c`, `memcpy-a8.c`). No hang occurred.
Ordinary compiler diagnostics include target-specific inputs, language-version
errors and unsupported modes/options. They are retained in the full per-case
classification, not asserted to be new backend defects. Raw support-file
diagnostics disappear from the corrected execute count.

Full original classifications: `.work/_shared/S14-58/summary.txt`.
Builtins replacement classifications: `.work/_shared/S14-58/builtins-summary.txt`.
Detailed nonpassing commands/diagnostics and retained assembly are under
`.work/_shared/S14-58/O2/` and `O3/`. Successful builtins reruns remove their
old missing-main logs. The original summary preserves those historical counts.
Host logs:
- `.work/_state/logs/S14_58_sweep-20261117-093421.log`
- `.work/_state/logs/S14_58_builtins-20261117-112916.log`

## Real failure triage

`CC` is the installed compiler above; `TS` is
`.work/_shared/gcc/gcc/testsuite`. Each command emits `repro.s`.
For the assembler rows, follow with
`k1om-mpss-linux-as --march=k1om repro.s -o repro.o`.

| Test | Level | Classification | Pass / instruction | Duplicate or disposition | Reduced compiler command |
|---|---|---|---|---|---|
| gcc.dg/vect/vect-pr123221.c | O3 | ICE: segmentation fault | vect; `vect_analyze_slp_reduc_chain`, tree-vect-slp.cc:4275; before RTL | S12-38, per lead; no re-triage | `$CC -fno-tree-pre -march=knc -O3 -S $TS/gcc.dg/vect/vect-pr123221.c -o repro.s` |
| gcc.c-torture/compile/920520-1.c | O2 | Input inline asm rejected | user asm; no generated insn implicated | target input, no backend defect established | `$CC -std=gnu89 -march=knc -O2 -S $TS/gcc.c-torture/compile/920520-1.c -o repro.s` |
| gcc.c-torture/compile/920521-1.c | O2 | Input inline asm rejected | user asm; no generated insn implicated | target input, no backend defect established | `$CC -std=gnu89 -march=knc -O2 -S $TS/gcc.c-torture/compile/920521-1.c -o repro.s` |
| gcc.c-torture/compile/920520-1.c | O3 | Input inline asm rejected | user asm; no generated insn implicated | target input, no backend defect established | `$CC -std=gnu89 -march=knc -O3 -S $TS/gcc.c-torture/compile/920520-1.c -o repro.s` |
| gcc.c-torture/compile/920521-1.c | O3 | Input inline asm rejected | user asm; no generated insn implicated | target input, no backend defect established | `$CC -std=gnu89 -march=knc -O3 -S $TS/gcc.c-torture/compile/920521-1.c -o repro.s` |

Every assembler error in the four input-asm rows resolves inside `#APP/#NO_APP`;
source lint was clean. No generated assembler rejection or lint failure occurred.
S12-34 was not observed. The six native failures are triaged below.

## Window 17 native failure triage

The lead ran the installed-prefix O3 execute set with 60 workers in window 17
(2026-11-17 17:33-17:34Z): 1,797 PASS, six FAIL, zero TIMEOUT.
Raw results: `.work/_shared/S14-58/card/out/execute-O3.{out,err}`.
The raw stderr records status **4** for `930529-1.c`, rather than the status 6
reported for all six in the ticket; the other five have status 6.
Original failing-function disassembly is retained in
`.work/_shared/S14-58/native-triage.txt`.

All rows use `-march=knc -O3`. Paths are relative to
`$TS/gcc.c-torture/execute`. These are harness diagnoses from source and
generated code, not claims that a corrected binary passed on the card.

| Test | Original result | Pass / instruction and cause | Disposition / corrected command flags |
|---|---|---|---|
| 930529-1.c | FAIL, raw 4 (SIGILL) | `main` is `ud2`; its braced, quoted `dg-options` value was ignored, losing `-fwrapv` for the signed-wrapping loop | harness parser miss; `$CC -fwrapv -march=knc -O3 930529-1.c -lm -o repro.mic` |
| builtins/abs-1.c | FAIL, raw 6 | `main_test` checks `abs_called` without an `abs` call; `abs-1.x` supplies `-fno-builtin-abs` | harness `.x` miss; compile abs-1.c, abs-1-lib.c and lib/main.c with `-fno-builtin-abs` |
| builtins/uabs-1.c | FAIL, raw 6 | same missing-call mechanism; `uabs-1.x` supplies `-fno-builtin-uabs -std=c2y` | harness `.x` miss; compile uabs-1.c, uabs-1-lib.c and lib/main.c with `-fno-builtin-uabs -std=c2y` |
| ieee/20030331-1.c | FAIL, raw 6 | inlined `rintf` keeps the add/subtract sequence in x87 precision instead of rounding each float assignment | missing IEEE harness controls; `$CC -fno-inline -ffloat-store -march=knc -O3 ieee/20030331-1.c -lm -o repro.mic` |
| ieee/pr109008.c | FAIL, raw 6 | `foo` compares x87 `1 + eps` before a double store, so the small epsilon remains distinguishable from 1 | excess-precision harness mismatch; same IEEE flags and command, substituting pr109008.c |
| ieee/pr67218.c | FAIL, raw 6 | `foo` has `fildll` then `fstpl`, with no intervening float rounding for `(double)(float)` | excess-precision harness mismatch; same IEEE flags and command, substituting pr67218.c |

`builtins.exp` delegates to `lib/c-torture.exp`, which sources a companion
`.x` driver before compilation; a simple `set additional_flags` replaces the
inherited flags. The two missing builtin options are therefore required test
inputs, rather than a request to disable a failing optimization.
`ieee.exp` supplies `-fno-inline` and conditionally adds `-ffloat-store` for
ia32 x86 and m68k. Its target predicate does not name k1om; applying the latter
flag to this sweep is an explicit adaptation for the x87 evaluation observed
in these executables. The original IEEE aborts do not establish wrong code
under the compiler's excess-precision mode.

No new compiler defect is established by these six incorrectly configured
tests, so there is no new defect ticket draft. Corrected native execution is
required before claiming that these six pass.

The corrected host subset covers all 69 IEEE inputs, `930529-1.c`,
`builtins/abs-1.c` and `builtins/uabs-{1,2,3}.c`: 74 cases at each level.
At O2 and O3, 68 pass compilation/assembly/lint (and O3 link/executable lint);
the same six IEEE `fp-cmp-*.c` inputs retain ordinary compiler diagnostics.
There are no ICEs, assembler errors, lint errors or link failures in this rerun.
The `.x` assignments replace inherited builtins flags, including `-std=c2y`
for uabs-2 and uabs-3, using the same function for host checks and staging.
Full classifications: `.work/_shared/S14-58/corrected-summary.txt`.
Log: `.work/_state/logs/S14_58_corrected_harness-20261117-144345.log`.

Retained corrected O3 `.unit0.s` files under the per-case paths above show
`call abs` and `call uabs`, no `ud2` in 930529-1, float stores and a separate
`rintf` call in 20030331-1, a double store before the comparison in pr109008,
and a float store/reload before the double conversion in pr67218. These address
the observed mechanisms; they are host evidence, not native execution results.

## Card staging

1,803 lint-clean O3 execute binaries (1,744 standalone plus 59 builtins) and
the lint-clean driver are staged under `.work/_shared/S14-58/card/`.
`claude-torture.list` is the single correctness list; `card-files.list` supplies
its inputs. The driver inherits affinity, starts at most 60 independent serial
processes, and records ordered PASS/FAIL/TIMEOUT plus `claude-torture.details`.
The 17 ordinary execute compiler diagnostics are excluded because they did not
compile. Builtins helpers are never listed independently.

Lead only, from the main checkout in an owner-approved window:

```sh
python tools/card_run --threads 240 --timeout 7200 --file-list .work/_shared/S14-58/card/card-files.list .work/_shared/S14-58/card/claude-torture.mic -j 60 --limit-mb 128 claude-torture.list
```

Window 17 results and outstanding corrected-harness native checks are above.
The same 1,803-entry list includes the 68 replacement binaries; the lead must
rerun it in an approved window before treating the original six aborts as closed.
A timeout is unresolved, not evidence of wrong code. No zero-wrong-code
acceptance claim is made from the original harness run.

## Tool regression

The builtins discovery/harness regression failed with `KeyError: builtins`
before implementation and passed after implementation (one test each).
Logs: `.work/_state/logs/S14_58_builtins_red-20261117-112647.log` and
`.work/_state/logs/S14_58_builtins_harness-20261117-112852.log`.
The earlier suite-path regression and option-parser correction are recorded
in the original sweep log and the ticket's earlier commits.
The native-options regression failed with `KeyError: source_options`, committed
as `25f3e9c8`, and passed after the braced dg-options, `.x` flags and IEEE controls
were implemented. Logs: `.work/_state/logs/S14_58_native_options_red-20261117-133902.log`
and `.work/_state/logs/S14_58_native_options-20261117-144327.log`.
