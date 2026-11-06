# Shared-card runner (S2-11)

`python tools/card_run PROGRAM [ARG ...]` runs a host-built executable on the
card. The owner rules on ticket S2-11 dated 2026-11-03 supersede S0-04's
foreign-process refusal and the old external workload lock.
Card jobs are lead-only; Codex sandbox accounts are refused before admission, so leave built binaries for the lead.

## Configuration

The default configuration is the main checkout's gitignored
`config/card.local.json`, including from `<main>/.work/<ticket>`. It is never
copied into a worktree. Required settings are `host`, `identity`, `knownHosts`
and `ledger`; `memoryMB` defaults to 128, `timeout` to 60 seconds and
`transportTimeout` to 10 seconds. `maxStageMiB` defaults to 64 and must be a
positive integer. It caps the total bytes staged: program, extra files, static
helper and watchdog script. Validation and size refusal happen before connection
or admission, since the card's filesystem uses RAM. `pinHelper` defaults to the main checkout's
`.work/_shared/claude-pin.mic` (a donor-built static executable), and `unpackHelper`
to `.work/_shared/claude-unpack.mic`. Limits must be finite and positive; memory
must be an integer from 1 through 10240 MB (`MEMORY_BUDGET_MIB`, owner 2026-11-04).

SSH uses the configured identity, strict known-host checking, batch mode,
`IdentitiesOnly=yes`, `HostKeyAlgorithms=ssh-ed25519`, no user SSH config,
and a five-second connection timeout. Workloads and uploads are never replayed.
After loss of the control session, the runner reconnects once to check the boot
ID and perform guarded cleanup only.
This also applies if the connection is lost during signalling or cleanup after
the final snapshot succeeded. The one recovery attempt repeats only boot
verification and guarded cleanup; a second connection failure stops recovery.
No reboot, MPSS, module, sysctl, huge-page or `/etc` changes are made.

Options before PROGRAM are `--config`, `--lock`, `--timeout`,
`--transport-timeout`, repeatable `--file PATH`, `--file-list LIST`, and `--receipt` (the existing spelling for the single
runtime result). `--external-lock` and `--baseline-name` remain parseable for
compatibility. External lock settings are ignored; baseline names only filter
which foreign processes are reported, never whether work may run.

Each `--file PATH` stages a regular host file beside `claude-program` under its
base name, using the same guarded raw SSH stdin stream. Source paths may include
directories; destination names must be plain names without `/`, `\\`, NUL, `.`
or `..`. Duplicate base names and runner names (`claude-program`, `claude-pin`,
`claude-watchdog.sh`, `claude-pinned`, `stdout`, `stderr`, `status`) are refused
before admission. Executable host files receive mode 700; other files receive
mode 600. Cleanup removes all extra files with the run directory. For example:
`python tools/card_run --file batch/test1.mic --file batch/input driver.mic`.
The driver's children inherit both core pinning and the job's per-process
address-space limit through `claude-pin`, so these settings apply to every
program the driver starts. The limit is not aggregate memory for the batch.
Host files the lead must read are never 0700: prepare card programs as 0755 and data files as 0644.

### One upload per job (S4-12)

`--file-list LIST` names one repo-relative path per line (CRLF and blank lines
ignored), added after any `--file`. With it, the job opens two upload
connections whatever the file count: the static `claude-unpack` helper
(`tools/claude-unpack.c`), then one stream holding `claude-program`, `claude-pin`,
`claude-watchdog.sh` and every listed file. There is no per-file chmod. The
stream is `claude-pack 1\n`, then per file `<600|700> <size> <name>\n` and the
bytes, then `end <count>\n`. The helper runs in the guarded job directory with
the exact stream length as its argument. It refuses the `staging_name` cases,
`claude-unpack`, `claude-pinned`, `stdout`, `stderr` and `status`; creates with
`O_EXCL|O_NOFOLLOW`, so duplicates and planted links fail; requires 700 for ELF
data and 600 otherwise; and on a short, long or malformed stream removes every
file it created and exits nonzero. Host checks (names, duplicates, size with
both helpers counted against `maxStageMiB`) still run before admission.

### Parallel torture batches (S2-18)

`claude-torture [-j N] [--limit-mb M] LIST` runs at most N programs at once;
N defaults to 1. Each program has its own two-second deadline and process
group. PASS/FAIL/TIMEOUT lines and saved diagnostics stay in list order even
when programs finish out of order. Each child's output is buffered separately
until its result can be emitted. Crashes and nonzero exits report FAIL.

Pass `--threads N` before PROGRAM for jobs whose layout is not fixed (default 1).
Admission claims ceil(N/4) free physical cores, from 59 downward, with all four
logical CPUs per core. `--cores 3,17` selects an explicit layout instead; core 60
is never used. Set the job configuration's `memoryMB` to at least N times M,
where M is the per-program address-space limit in MiB. For example, N=80 and
M=96 require `memoryMB: 7680`; stage the list and all its executables as usual,
then pass `-j 80 --limit-mb 96 LIST` after the driver executable in the
`tools/card_run` command. The 10240 MiB admission ceiling and free-memory
reserve still apply. Driver overhead and staged files also need free card RAM.

The driver reads the job budget from the inherited `RLIMIT_AS` set by
`claude-pin`, checks N times M against it before starting any program, and
sets each child's own `RLIMIT_AS` to M. No CPU affinity is changed. Without
`--limit-mb`, parallel runs divide the inherited budget equally among N
children; serial runs retain their existing inherited limits. Thus
`-j 80 LIST` with `memoryMB: 6400` also gives each program 80 MiB.
An unlimited inherited budget refuses parallel execution because it
cannot establish the declared reservation. Job timeout cleanup still applies
to all children; driver TERM/HUP/INT also kills and reaps active test groups.
Native validation belongs to the lead: rerun S2-08's 256-program batch at N=30
after S2-17, with later batches using the full execute suite.

## Enforcement

- Read the configured shared JSONL ledger before connecting and again at
  admission. Append complete JSON objects with one append syscall each; never
  rewrite or truncate the ledger. Malformed or missing ledgers fail closed.
  A start record precedes staging and includes `agent: "claude"`, job ID,
  physical cores, logical CPUs, memory MB, start and expected end. Every admitted
  job appends a finish record after cleanup, also on staging/program failure,
  timeout or card fault. The shared schema uses `event: start/finish`, `jobId`,
  `cores`, `logicalCpus`, `memoryLimitMiB`, `startTime`, `expectedEnd`,
  `endTime`, `outcome` and `timingValid: false`; finish carries the same job
  metadata. Other-agent `gpt61` lines use the same schema. Legacy runner
  `job_id`/`end` lines are readable without rewriting history. Ledger write
  errors are infrastructure failures, and an overlap scan failure does not
  suppress the finish append.
- Hold our local lock (default `<main>/.work/_state/card.lock`) and a mandatory
  `claude-admission.lock` beside the ledger through final ledger writes.
  The latter prevents callers with different `--lock` values from racing our
  admission checks. These locks serialize our invocations; other projects do
  not take them. Create atomically, refuse on existing/stale locks, and remove
  only locks this invocation created. No external/shared-card lock is taken.
- Parse the card's `/proc/cpuinfo` processor/core pairs. Claim free physical
  cores 0 through 59 using every project's open ledger claims, waiting within
  the admission timeout if too few are free. Pass that
  mapping through the run, including admission waits and cleanup reconnects.
  Read cpuinfo once, using one `awk` pass to emit only processor/core fields
  and block separators; subsequent snapshots skip cpuinfo. Pass the
  explicit CPU list to the static `claude-pin` helper. It calls
  `sched_setaffinity(0, ...)` before executing the program; a failed syscall
  prevents execution and names the failure. No eligible CPUs refuses admission.
  Affinity is inherited by the workload's children.
  Snapshots do not claim pinning succeeded. After affinity and memory limits
  succeed, the helper creates `claude-pinned` immediately before exec and removes
  it if exec fails. A completed launch without that marker is an infrastructure
  failure, with no program exit status; the ledger finish records that outcome.
  A marked program may itself return 125, 126 or 127 without being misclassified.
- Read `MemFree` from `/proc/meminfo` before staging using one `awk` invocation
  per snapshot. Reserve the declared memory against all
  active ledger entries of ours (`project: "gcc-knc"`, or no `project` and a
  `claude-` plus 32 hex digits job ID); other projects' rows do not count.
  Ended jobs release their reservation.
  Wait while the total exceeds 10240 MB or the reservation would leave less
  than 1536 MB of `MemFree`. Re-read both ledger and memory after each wait;
  the configured timeout bounds admission waiting. Expiration refuses without
  staging the executable. Expected-end estimates never expire reservations.
- Sharing with timed jobs (S5-04, S5-19). `--benchmark` requires an empty ledger,
  claims cores 0-59 and records `timingValid: true`. While waiting it appends a
  timed `queued` row with `queuedTime`; start or superseded closes that queue.
  Fresh timed queues (under three hours old) from other projects also hold back
  ordinary jobs so the ledger can drain. If the last timed finish was ours,
  another project's fresh queue makes benchmark admission refuse with "their turn"
  on timeout. Queues close on start, finish (including cancelled), or superseded;
  legacy queues without timingValid and queuedTime are ignored.
  Our start, finish and fault rows carry
  `"project": "gcc-knc"`. While any open row that is not ours has
  `"timingValid": true` (the PhiWeather tuning session's timed runs), card_run
  refuses before connecting, staging or writing a row (and again on each admission pass), naming the job and its
  `expectedEnd`; it never retries, so the caller waits and tries again.
  Staging must finish within `--stage-timeout` (default 120 s); a slower
  upload is stopped, cleaned up and finished as an infrastructure failure, so
  our start row never stays open through a slow upload. The S3-10 torture row
  stages its 1,680 files through `--file-list`, in one pack.
- The owner-reported card has no taskset, and its cgroup memory controller is
  disabled with no mounted controllers. Nothing is mounted or enabled. Instead,
  `claude-pin` sets both soft and hard `RLIMIT_AS` to the declared MiB before
  exec; failure prevents execution. Address space is stricter than resident
  memory for a single process, and includes mappings and reservations as well
  as resident pages. The limit survives fork/exec, but is per process, not an
  aggregate descendant memory controller. Ledger admission bounds the sum of
  our declared job limits to 10240 MiB; multi-process jobs must account for this
  per-process limitation. This is the backend explicitly selected by the owner.
- Stage exclusively in `/tmp/claude/claude-<random-id>/`, with executable
  `claude-program`, control shell name `claude-control`, and watchdog
  `claude-watchdog`. No ports are allocated. Short-lived system utilities
  retain their system utility names during control, transfer and cleanup. Each
  destructive operation checks the exact directory shape, its owner, physical cwd and original boot ID. The runner
  resolves `/tmp` with `cd /tmp && pwd -P` once per remote shell, since the
  card may link it to `/var/volatile/tmp`. The physical cwd must equal that
  exact resolved prefix plus `/claude/claude-<32 lowercase hex>`; a symlink
  for the job directory or a redirected `claude` parent cannot pass. Upload,
  watchdog, reconnect cleanup and stale recovery use the same guard. Each
  failed directory or boot guard prints the failed check to stderr.
  Process identity checks use the exact physical job path so a live process
  under symlinked `/tmp` prevents stale recovery and remains identifiable for
  guarded cleanup. Each snapshot also emits that physical path in a `RUNDIR`
  record, including before staging. The host excludes executable/cwd paths
  inside either the logical or physical job directory from foreign-process
  reports; matching includes a path boundary, so sibling directories stay
  foreign. Ownership
  uses the exact executable/cwd path, never a broad process name. A descendant
  that both execs outside our directory and changes cwd cannot be identified
  by this rule; the helper does not provide cgroup membership tracking.
- Report other users' processes in `foreign_processes`; leave them alone.
  Snapshots exclude the control shell's PID and its direct children by PPid,
  including before staging changes its cwd; foreign names do not grant exclusion.
  One shell pass reads process identities and skips kernel threads by PID/PPid.
  One numeric `ls` reads all user-process executable/cwd links and one `awk`
  joins them to identities. No snapshot forks `readlink` or a subshell per PID;
  the fake `/proc` test counts utility commands and shell read/printf calls
  with 300 kernel threads and 240 CPU blocks of 25 lines each.
  Cleanup and stale recovery also skip PID 2 and PPid 2 using shell reads
  before inspecting executable/cwd links. Kernel-thread links can exist as
  dangling symlinks, so their presence alone cannot identify a user process.
  Command-count tests cover all cleanup passes and stale recovery with 300
  such threads.
  Signals target only processes in our exact directory, rechecking identity after the boot guard, never by broad name/group.
  Guarded TERM/KILL cleanup removes our exact staging directory. Stdout/stderr are copied back in bounded chunks before normal
  cleanup. A separate HUP-ignoring watchdog applies the same guards after the
  program timeout plus `max(5 seconds, 2 * transportTimeout)` grace.
  After removing our job directory, `rmdir /tmp/claude` removes the RAM-backed
  parent only when empty, preserving any sibling job directories.
  Before admission is recorded or files are staged, stale recovery considers
  only `/tmp/claude/claude-<32 lowercase hex>` directories. The exact path,
  non-symlink, owner, physical cwd and original boot guards apply. Any live
  process with its executable or cwd in a candidate keeps it; stale recovery
  never signals processes. Foreign names and symlinks are left untouched.
- Recheck boot ID before execution, after execution and before any signal or
  removal. A changed boot or a failed connection on the one reconnect is an
  infrastructure failure: append `card-fault`, then finish. An ordinary remote
  command failure or a recovered connection on the same boot records only
  `infrastructure-failure` in the finish line. Do not signal/remove on an
  unknown or changed boot. A deadline during signalling or cleanup after a
  successful reconnect is infrastructure, without a `card-fault` line.
  A reconnected shell checks the original boot before
  entering the exact existing job directory to clean it; it never restages or
  executes the job. Report confirmed faults on the ticket so the lead can
  escalate. The watchdog also refuses destructive operations on another boot.

Required utility checks run before creating a remote staging directory. They
name every missing tool rather than returning an unexplained status 94. The
list is `readlink ls id cat dd chmod sleep mkdir rm rmdir awk` plus shell
builtins. The lead's probe reported `stat` and `base64` missing and `od`
available. Directory ownership now uses `LC_ALL=C ls -ldn` and `id -u`.
Program, static helper and watchdog bytes are uploaded on separate, bounded
SSH stdin streams to guarded `cat` commands, without an encoding tool. The
lead's 12:03 run found BusyBox 1.19.4 rejects `head -c` and `od -A`. Output now
uses separate bounded SSH stdout streams running guarded
`dd if=<stdout-or-stderr> bs=65536 skip=<block-offset> count=<1-or-2>`, with the actual
filename selected from those two names. An unaligned byte offset reads at most
two blocks; the host trims the prefix and delivers at most 64 KiB per chunk.
Status is checked immediately on the existing control session, then after
delays of 0.5, 1, 2, 4 and at most 5 seconds. While the job runs, stdout and
stderr each open one bounded download connection no more often than every
10 seconds; there is no initial download. Once status reports completion,
both streams are drained without poll delays until an empty pair is read.
A quiet 60-second job therefore needs at most 14 output connections,
including the final drain; larger completed output needs additional bounded
chunks. Execution deadlines still apply throughout polling and draining.
This avoids one-byte reads on the card. Raw reads preserve
binary stdout/stderr, trailing newlines and control-marker-like bytes, and
advance a separate byte offset per stream. Every control operation is labelled (`snapshot`, `stage-create`,
`stage-chmod`, `start-job`, `read-stdout`, `read-stderr`, `read-status`,
`stop_owned`, `cleanup`, `reap-stale`, plus connection setup steps). Command
stderr is merged before the completion marker so nonzero status reports include
the step name and diagnostics. Deadlines and ended sessions also name the step
and include captured partial output. Upload failures name the file and include
stderr; download failures name the stream and include stderr. A command's nonzero exit keeps the control protocol usable; a transport
failure invalidates that session. Admission happens before remote
mkdir or upload. The second SSH streams recheck the original boot and directory
owner/cwd; partial uploads remain in our directory for guarded cleanup.

## Build and native handoff

Run builds through `tools/run.py`. With the shared toolchain's `cross/bin` and
`cygwin/bin` on PATH, use that Cygwin's `python3.12` to run the wrapper. From a
Cygwin shell in this worktree, the donor build commands inside the wrapper are:

```sh
k1om-mpss-linux-gcc -O2 -static --sysroot=../_shared/toolchain/sysroot -L/cygdrive/c/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap/sysroot/usr/lib64 tools/claude-pin.c -o ../_shared/claude-pin.mic
k1om-mpss-linux-gcc -O2 -Wall -Wextra -Werror -static --sysroot=../_shared/toolchain/sysroot -L/cygdrive/c/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap/sysroot/usr/lib64 tools/claude-unpack.c -o ../_shared/claude-unpack.mic
k1om-mpss-linux-gcc -O2 --sysroot=../_shared/toolchain/sysroot tests/tools/card_hello.c -o ../_shared/claude-hello.mic
```

The shared sysroot lacks static `libc.a`. The helper link uses the original
bootstrap sysroot's static library in place with `-L`; no toolchain or library
is copied. Quote that entire `-L...` argument when invoking from PowerShell.

The static helper is host-built for KNC and is never executed on the host.
The main checkout can use its default helper path; `pinHelper` can name that
same shared artifact explicitly. The owner requires the interactive lead to
run every native job, using this branch's `tools/card_run` and the shared
configuration. Engineer sessions do not read the key or connect to the card.
The lead runs `python tools/card_run ../_shared/claude-hello.mic` from this
worktree and posts exit status, result path, ledger start/finish, boot IDs and
card minutes to S2-11. If the result reports a card fault, ask on the ticket;
the lead escalates. Never claim fake-transport or build success as native
execution.

## Result and fake seam

The single overwritten result defaults to `tests/out/card-result.json`; it is
runtime output, never committed. Fields include `result_class`, `exit_code`,
`program_exit_code`, both boot IDs, `card_minutes`, detail, job ID, staging path,
memory MB, selected logical CPUs, foreign processes and `overlapping_jobs`.
`reaped` lists stale job paths removed during admission; `stale_kept` lists
stale candidate paths retained because a live process uses their cwd or
executable. Both default to empty lists. Foreign names and symlinks are not
stale candidates and do not appear in either list.
Overlaps include jobs already active at admission and jobs starting during ours,
even when they also end during ours. Card minutes account only for execution;
there are no performance/timing claims. Classes are `program`, `refused`,
`timeout`, and `infrastructure`; runner exits are 125, 124, and 126 respectively.
The result class distinguishes program statuses that collide with those values.

`run` accepts program/argv, local and legacy external-lock/baseline arguments,
timeouts, result path, transport, ledger path, memory MB, optional `files`,
`max_stage_mib` (default 64) and an injectable
monotonic clock. A fake session provides `snapshot`, `stage`, `execute`,
`reap_stale`, `signal_owned`, `cleanup` and `close`. `snapshot` accepts
`include_cpuinfo` (default true); the runner requests it only for the first
snapshot, including across a cleanup reconnect. Snapshots contain boot ID,
processes, filtered cpuinfo/meminfo, and `physical_run_dir` when supplied by the
remote shell. They may report known pinning unavailability for early
refusal. SSH checks enforcement at execution through the helper marker.
`reap_stale` returns a mapping containing the `reaped` and `stale_kept` lists.
Execute receives the explicit
logical CPU list, memory MB, execution timeout and watchdog timeout.
`tests/tools/test_card_shared.py` tests the shared rules without SSH; its shell
fixture locates `sh` through PATH.

## Validation status

The original approved RED is ae87007. Owner-follow-up RED 0ec400e adds the
BusyBox replacements, helper syscall-order/failure seams and the gpt61 ledger
schema. The failing run is in
`.work/_state/logs/S2_11_owner_red-20261103-110522.log`; the legacy tests also
exposed their old fixture API and were migrated to the new shared policy.
The owner/lead's probe of 19cf929 returned 94 before staging: no native program
ran and no ledger start was written. Native acceptance of this revision belongs
to the lead under the owner's 11:02 decision. Final fake/build results are
recorded in the ticket submission.

The final fake run passed 32 of 34 tests; its two failing cases were a comment
matching the removed utility name and Cygwin CPU inspection macros requiring
a mutable mask. After those fixes the focused two-case run passed, without
repeating passing cases. Logs: `S2_11_owner_green-20261103-110731.log` and
`S2_11_owner_green_fixes-20261103-110926.log` in `.work/_state/logs/`.
The static donor helper build passed with the original bootstrap static libc:
`.work/_state/logs/S2_11_pin_build-20261103-110845.log`.

Review RED db52e6b and corrected fixture RED cc2afae cover the helper marker,
snapshot PID exclusions, removal of the constant pinning claim and empty-parent
cleanup. All five focused T0 cases passed in
`.work/_state/logs/S2_11_review_green-20261103-112036.log`. After changing the
missing-marker response to keep SSH usable for cleanup rather than report a
transport fault, the affected classification case passed in
`.work/_state/logs/S2_11_review_marker_green-20261103-112110.log`.
The updated static donor helper build passed in
`.work/_state/logs/S2_11_review_pin_build-20261103-112049.log`.
No card access was attempted; native donor hello remains with the lead.

Native-review RED e1e5cf8 covers snapshot command counts, named failures and
stderr, same-boot failure classification, one reconnect without job replay, and
guarded stale cleanup. Eight focused tests produced nine expected assertion
failures and no errors in `S2_11_native_review_red_fixture-20261103-112835.log`.
The card-related T0 suite passed all 46 cases in
`S2_11_native_review_green-20261103-113049.log` under `.work/_state/logs/`.
The lead's 11:25 run of 61a8a62 established ledger/core mapping/boot reporting
but did not execute hello; native hello acceptance still requires the lead's
rerun of this revision. No native result is inferred from these fake tests.
RED 8ef9669 additionally covers a session lost during cleanup after a successful
final snapshot (`S2_11_cleanup_reconnect_red-20261103-113215.log`, one expected
assertion failure). After extending the same recovery path to all finalization
steps, the five affected recovery/classification cases passed in
`S2_11_cleanup_reconnect_green-20261103-113229.log`; the other passing cases
were not repeated.

Eighth-round RED 6bbd99d reproduces physical-path process misclassification and
the native BusyBox output-option failures. Both cases failed as expected in
`S2_11_eighth_red-20261103-120214.log`. In
`S2_11_eighth_green-20261103-120347.log`, eight focused cases passed; the binary
case exposed slow one-byte `dd` reads and the timeout selector named the wrong
test class. Block reads with host-side byte trimming fixed the download. The
binary and corrected timeout cases then passed in
`S2_11_eighth_green_output-20261103-120439.log`; passing cases were not repeated.
All logs are under `.work/_state/logs/`. The interactive lead reruns donor hello
at the default 10-second transport timeout, checks native acceptance, and
confirms our watchdog/program are absent from foreign-process evidence.
