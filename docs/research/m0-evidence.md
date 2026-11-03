# M0 evidence: GCC 16 on the Windows host

2026-11-02, S1-07. **Recommendation: adjust.** Keep GCC 16.2 as the base,
but do not declare M0 met on this host: the header loop takes 23.36 minutes
and the machine-description loop is not reliably within five minutes.
Request an owner decision on enabling WSL2 for a comparison before accepting
the host loop. WSL2 has not been enabled or measured. Cygwin is the measured
environment, but these runs cannot prove that Cygwin alone causes the miss.
No blocker has been demonstrated to be exclusive to GCC 16 versus 14.4;
there is no measured basis for a compiler-version bridge.

Owner decision (2026-11-02): M0 is adjust; keep GCC 16.2 as the base and run Sprint 2 on this Windows/Cygwin host; no WSL2 for now.

## Six requested measurements

Shared source: `.work/_shared/gcc`, branch `knc`, commit `6d879ee3154`;
build: `.work/_shared/gcc-build`, configured for `k1om-mpss-linux`.
Host: Windows 10, Cygwin GCC/G++ 14.4.0, Make 4.4.1, Python 3.12.
Each run used `tools/run.py --inputs ...` and the existing gcc16 step's
`make all-gcc CFLAGS='-O2 -g1' CXXFLAGS='-O2 -g1'`, with `-j8` to obey
AGENTS.md's maximum rather than the helper's `-j<os.cpu_count()>`.
No reconfiguration, installation, clean build or card execution was done.

The monotonic timer started immediately after each touch/edit and included
the build followed by `tools/check t1 --compiler gcc16`, through its return.
T1 time includes its runner overhead. Runs were sequential, with no other
agent work during builds. The edit prepended one `;;` comment to `i386.md`,
shifting generated source references; original bytes were restored after
that run, and the next run rebuilt the revert. The fork finished clean on
the original branch and commit; touched files have newer timestamps only.

All log filenames below are relative to `.work/_state/logs/` in the main
project, outside the disposable ticket worktree. Times are seconds.

| Change | Build | T1 | End to end | Within 300 s? | Log |
|---|---:|---:|---:|---|---|
| Touch `linux-k1om.h` | 1392.567 | 8.886 | 1401.453 | No | `S1_07_header-20261102-230040.log` |
| Touch `i386-options.cc`, 1 | 73.750 | 8.598 | 82.349 | Yes | `S1_07_options1-20261102-232408.log` |
| Touch `i386-options.cc`, 2 | 72.113 | 8.868 | 80.981 | Yes | `S1_07_options2-20261102-232535.log` |
| Touch `i386-options.cc`, 3 | 73.759 | 9.115 | 82.874 | Yes | `S1_07_options3-20261102-232702.log` |
| Add `i386.md` comment | 318.813 | 8.617 | 327.430 | No | `S1_07_md_edit-20261102-232830.log` |
| Remove comment | 281.870 | 9.249 | 291.119 | Yes | `S1_07_md_revert-20261102-233404.log` |

All six builds exited 0; all six T1 commands exited 1 solely on the pending
`m1_affine` packed-zmm/vectorization-report scans, in both contraction modes.
All 15 `tests/t1` sources passed, as did both fixture assembly/lint checks.
The nested T1 log path is in each measurement log; final T1 details are in
`check_gcc16_t1-20261102-233847.log`. These are completed measurements,
not six green full-T1 results. The two `.md` totals average 309.275 s.

S0-06's stock x86-64 rebuild-only figures (168.536 s for `i386.cc`,
264.552 s for `.md`) did not measure this target or include T1. S1-06's
1391.896 s rebuild with the lighter debug flags improved on S1-05's
2056.884 s, but did not solve header invalidation. Their logs are
`S1_06_gcc16-20261102-223037.log` and `S1_05_gcc16-20261102-210115.log`.

## M0 conditions (PROJECT_PLAN section 6)

| Condition | Verdict | Evidence |
|---|---|---|
| `cc1` builds for `k1om` | Met | Six successful `all-gcc` runs above. S1-02's final build took 3560.636 s and its driver printed `k1om-mpss-linux`, with as/ld/sysroot in the shared toolchain: `S1_02_gcc16_final-20261102-142543.log`. |
| Emitted integer assembly accepted by as 2.22 | Met for the compiled corpus | Current T1 assembly/lint passes. S1-05 measured 2003 files at three levels (6009 cases) in 808.426 s: zero ICE, hang, compiler-generated assembler rejection, lint or infrastructure failures. See `S1_05_torture_selectors-20261102-221119.log` and `tests/baseline/gcc16-torture-compile.txt`. |
| Incremental rebuild plus T1 at most five minutes | Not met | Header 1401.453 s; `.md` edit/revert 327.430/291.119 s. All three options-file loops meet the timing limit. Expected M1 scan failures remain explicitly recorded. |

The corpus result is not universal C coverage: passes were 1873/1877/1877;
front-end/other compiler errors 18/17/17; SSE-disabled FP ABI errors
110/107/107; rejected user inline assembly 2/2/2. Those inputs never supply
successful compiler-generated objects. No native result is claimed.

## Sprint 1 blockers and disposition

Source: ticket records S1-01 through S1-06 and the logs named there. A
GCC-16 port gap or changed default is distinguished from evidence that
switching to 14.4 would fix it; the latter comparison has not been run.

| Blocker encountered | Disposition | GCC 16 specificity |
|---|---|---|
| PM could not branch/review/commit the shared fork; ownership refusal | S1-01/S1-02 added the two-repository workflow and `commit --gcc`; dispatcher supplied ownership configuration. | Project tooling, not compiler-version specific. |
| Protected collaboration document, test-count/size/ratio/session/run limits | Lead retained ownership of that document, approved justified budgets/overrides or completed verification; no policy bypass. | Project process, not compiler-version specific. |
| No k1om routing, missing `HAVE_AS_GOTOFF_IN_DATA`, unresolved `host_detect_local_cpu` | S1-02 routed target headers, existing assembler probes and host driver object; build and driver-path checks passed. | Missing GCC 16 port integration; not an exclusive GCC 16 defect. |
| Long build exceeded tool/session limits; teardown caused user32.dll error 8/Hangup and a zero-byte object | Resume/repair completed; quiet polling is now authorized. No such failure in these six runs. | Host/session infrastructure, not a GCC target diagnostic. |
| DejaGnu absent; bootstrap/shared runtime mismatch caused donor exit 127 | S1-03 added scan tests; checks use shared Cygwin environment. Lead verified smoke and unchanged donor baseline. | Test infrastructure, not compiler-version specific. |
| Generic x86 defaults/macros and unconditional 64-bit CMOV/FCOMI/MFENCE assumptions | S1-04 selected independent KNC defaults, avoided generic macro ICE and guarded shared instructions. Seeded CMOV was caught and restored. Equivalent branch/x87 forms replaced over-specific donor scans; scan-failure assembly/lint regression fixed. | Port assumptions in current i386 machinery; no 14.4 comparison. |
| GCC 16 `-g` defaults to DWARF 5; card debugger version unknown | As 2.22 already accepted measured debug assembly. Owner chose DWARF 4 to match donor; S1-05 red/green passed. | Changed default versus donor, not an observed assembler blocker or proof against 16 alone. |
| Torture directives initially ignored; AVX-header timeout; apparent foreign-arch and inline-asm assembler failures | S1-05 applied unselected dg options, skipped target-selected options, retried timeouts, and classified asm errors only inside `#APP/#NO_APP`. Final sweep has no hangs or generated-code assembler failures. | Corpus/runner scope, not a demonstrated GCC 16 defect. |
| Remaining torture compiler diagnostics | SSE/AVX/MMX options, foreign tuning/MIPS registers, invalid SI pointer mode, impossible asm constraints, absent isl and front-end C errors are enumerated in the baseline audit. Invalid user asm is `920520-1.c`/`920521-1.c`. | Input/configuration limits; no evidence for a version bridge. |
| Float/double arguments or returns require disabled SSE; affine zmm scans fail | Open: SSE-free FP and IMCI/vector work remain for E2/M1; not hidden, skipped or weakened here. | Unimplemented KNC facilities, not evidence of a 16-only regression. |
| Missing K1OM link defaults and GCC 16 `*_asneeded` scripts; no target libgcc yet | S1-06 ported defaults. Temporary donor `-B` plus test-local linker scripts/library paths bridge until E2-05. T2 proves ELF 181, K1OM loader, glibc <=2.21 and only libc DT_NEEDED: `check_gcc16_t2-20261102-225729.log`. | Script behavior changed versus donor GCC 5; 14.4 untested. Runtime build remains pending. |
| Card is on owner hold | No native execution in Sprint 1 evidence; E2-06 remains the native hello gate. | External constraint, not compiler-version specific. |
| Current five-minute host-loop miss | Open M0 blocker; retain GCC 16, escalate the WSL2 comparison decision to the owner. | Only Cygwin measured; compiler-versus-host attribution unresolved. |

## Shared i386 change budget for M1

Net tree diff from `releases/gcc-16.2.0` (`78d4ac73dd3`) to
`6d879ee3154`, using `git diff --numstat`; additions plus deletions count
changed lines, including comments/blank lines. Count every existing shared
file conservatively, including KNC hooks, rather than assuming exemptions.

| File (under `gcc/`) | Added | Deleted | Changed |
|---|---:|---:|---:|
| `common/config/i386/i386-common.cc` | 3 | 0 | 3 |
| `config/i386/i386-c.cc` | 9 | 0 | 9 |
| `config/i386/i386-options.cc` | 16 | 0 | 16 |
| `config/i386/i386.h` | 7 | 2 | 9 |
| `config/i386/i386.opt` | 4 | 0 | 4 |
| `config/i386/sync.md` | 2 | 2 | 4 |
| **Existing shared i386 subtotal** | **41** | **4** | **45** |
| New dedicated `config/i386/linux-k1om.h` | 63 | 0 | 63 |

The conservative shared baseline leaves **255 of 300 lines** for M1.
Of the 45, 32 are KNC registration/macros/option handling and 13 are in
`i386.h`/`sync.md`; the dedicated header is outside the shared subtotal.
`i386.md` has zero final changes. Routing/probes outside i386 directories
also changed: `config.gcc` +16/-11, `config.host` +1/-0, and `configure`
and `configure.ac` each +1/-1; they are reported separately from M1's
shared-i386 limit.
