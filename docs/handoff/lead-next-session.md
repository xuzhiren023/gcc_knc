# Next lead session prompt (written 2026-11-04 05:40)

Paste everything below the line into a new Claude session in `C:\Users\xuzhi\Documents\gcc_knc`.

---

Act as tech lead on GCC-KNC, per `CLAUDE.md`. Start by reading `STATUS.md` and `CURRENT_STATE.md`
and running `python tools/pm.py board`. Check every fact below with a command before you rely
on it.

**Where things stand (2026-11-04 05:40).** Sprint 3 is finished except two tickets, then the M1
decision.

- Merged and checked on the card: S3-10 to S3-21. After S3-20 (`knc` `73cc9c03798`) the full
  `gcc.c-torture/execute` suite has no ICE, links 1,681 of 1,692, and passes 1,681 of 1,681 on the
  card. S3-10's whole batch passes (job IDs in `docs/research/card-runs-s3.md`).
- **S3-22** (the last three KNC blocks in shared i386 code become hooks) is in **owner** state:
  20.6M of 20M input tokens used. The lead raised `input_tokens` to 30M in the ticket. Only the
  owner role can run `pm.py decide`, and the permission check refused the lead doing it. If S3-22
  is still in owner state, ask the owner to run:
  `PM_ROLE=owner python tools/pm.py decide S3-22 "Budget raised to 30M input tokens (20.6M used) for one rerun of the x86 check, which failed at 05:21 on a Cygwin out-of-resources error, plus the final note."`
  Its code is done (GCC `43ded4fa4d8`: shared 202 lines/56 hunks to 184/53, 4,216 identical-assembly
  comparisons, 0 differences). Only its x86 rerun and the final note remain.
- **S3-23** (KNC's `atomic_storeti` clashes with upstream's new one in `sync.md`; trunk build with
  T1 and T2) is ready and depends on S3-22.
- The dispatcher has exited. Once S3-22 is back in `doing`, restart it detached:
  `python tools/dispatch.py --lane gcc --max-sessions 12`. It exits at 12 sessions, engineer
  and lead together, or when a ticket needs the owner; restart it whenever S3-22 or S3-23 is still
  open. The owner asked that the gcc lane be watched until it finishes, because M1 depends on it.

**When S3-22 merges:**
1. Verify that the merged tree equals the tested branch (`git diff <branch tip> <merge>` is empty),
   that `cc1` was built after the last commit, and the red: `8783d2c` (`tools/knc_relocation.py`)
   failing at the old head. Recount shared lines and hunks (expect 184/53).
2. Read its hunk list and drill conflicts (one each in `i386-c.cc`, `i386.cc`, `configure`,
   `configure.ac` onto master). Each must be textual for M1 criterion 5.
3. Its varargs save now goes through `mov<V4SF>`, enabled for KNC only for that save, with a
   `gcc_assert` on any other V4SF move. Run the `-O3` ICE sweep to confirm nothing else reaches it:
   `python tools/torture_compile.py --level O3 --jobs 4 --output .work/_shared/tmp/claude-o3 --summary .work/_shared/tmp/claude-o3/summary.txt`
   (expect 0 ICE). Also run `--level O2` with `-ftree-vectorize` if the tool allows extra flags;
   otherwise note that S3-11's wrapper added it.
4. Card: `python harness/card/build_suite.py .work/_shared/tmp/claude-suite-s3-22 gcc16`, then
   `python harness/card/run_suite.py .work/_shared/tmp/claude-suite-s3-22 .work/_state/card/claude-suite-s3-22`
   (expect 1,681 of 1,681). Also rebuild and run S3-15's varargs and ABI checks and
   `tests/acceptance/s3_tls_card` if the varargs save path changed codegen anywhere. Record the
   cc1 SHA-1 before and after the build, so you know no other build replaced it mid-run.

**When S3-23 merges:** the same verification, plus the trunk result (cc1 builds; T1 and T2 against
trunk match 16.2, or each difference has a cause). Run `python tools/check t1 t2 --compiler gcc16 --atomics`
(check the flag spelling with `--help`) and the card suite again, since the atomic expanders moved.

**Then decide M1** against the fixed criteria in `work/tickets/S3-11.md`, item by item, using
`docs/research/m1-result.md` (items 1 to 4 met; 5 and 6 depend on S3-23 and S3-22). Criterion 7
(the separate backend's estimated cost exceeds the subtarget's measured cost plus its expected
cost to M2) is marked "not proven, effort estimates overlap" there; read the method and judge it.
- Go: add `"accepted": "<date>"` to M1 in `work/milestones.json`, write the decision into
  `m1-result.md` and `CURRENT_STATE.md`, and make a local milestone commit and an annotated tag
  `m1` in both repositories (this repo's `main` and `.work/_shared/gcc` branch `knc`). Never push.
- Adjust: write the failing items as tickets ahead of Sprint 4's work.
- Stop: escalate the case to the owner with `pm.py escalate`.

**Rules that still apply.**
- Run every card job through `tools/card_run` (the suite scripts use it). Use cores 30-59, 7 GB,
  the ledger, `/tmp/claude` and `claude-` names, and record no timing figures. Never use SSH.
- Never build test programs while `make.exe` runs. GCC builds belong to engineer sessions.
- A read-only Claude subagent may review each merged GCC change.
- Record findings on tickets or in `CURRENT_STATE.md`, and shareable ones in
  `docs/research/for-the-other-agent.md`.
- Raise ticket budgets under the owner's 2026-11-03 delegation (front matter plus a lead note),
  then ask the owner for the `decide`.
- Report to the owner plainly: proven, not proven, failed, and tokens from `STATUS.md`. Note that
  S3-15's failed first session is missing from the token totals.
- Never push unless the owner asks.
