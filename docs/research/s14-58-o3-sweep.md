# S14-58: installed-prefix torture and vect sweep

Compiler: `.work/_shared/gcc-knc-16.2.0/bin/k1om-mpss-linux-gcc.exe`.
This records the installed prefix, without asserting its GCC source commit.
No GCC change or build. Native execution **NOT RUN**; x86 not run.

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
S12-34 was not observed. No new ICE, assembler/lint defect or wrong-code failure
is established, so there is no new defect ticket draft. Native wrong-code
triage remains dependent on the lead's card run.

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

Native execution **NOT RUN**. A timeout is unresolved, not evidence of wrong
code. Triage every native FAIL/TIMEOUT with the retained test name and details
before claiming zero known wrong code for this run.

## Tool regression

The builtins discovery/harness regression failed with `KeyError: builtins`
before implementation and passed after implementation (one test each).
Logs: `.work/_state/logs/S14_58_builtins_red-20261117-112647.log` and
`.work/_state/logs/S14_58_builtins_harness-20261117-112852.log`.
The earlier suite-path regression and option-parser correction are recorded
in the original sweep log and the ticket's earlier commits.
