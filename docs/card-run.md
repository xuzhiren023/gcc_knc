# Shared-card runner (S2-11)

`python tools/card_run PROGRAM [ARG ...]` runs a host-built executable on the
card. The owner rules on ticket S2-11 dated 2026-11-03 supersede S0-04's
foreign-process refusal and the old external workload lock.

## Configuration

The default configuration is the main checkout's gitignored
`config/card.local.json`, including from `<main>/.work/<ticket>`. It is never
copied into a worktree. Required settings are `host`, `identity`, `knownHosts`
and `ledger`; `memoryMB` defaults to 128, `timeout` to 60 seconds and
`transportTimeout` to 10 seconds. `pinHelper` defaults to the main checkout's
`.work/_shared/claude-pin.mic` (a donor-built static executable). Limits must be finite and positive; memory
must be an integer from 1 through 7168 MB.

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
`--transport-timeout`, and `--receipt` (the existing spelling for the single
runtime result). `--external-lock` and `--baseline-name` remain parseable for
compatibility. External lock settings are ignored; baseline names only filter
which foreign processes are reported, never whether work may run.

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
- Parse the card's `/proc/cpuinfo` processor/core pairs. Select only logical
  CPUs belonging to physical cores 30 through 59; never core 60. Pass that
  explicit CPU list to the static `claude-pin` helper. It calls
  `sched_setaffinity(0, ...)` before executing the program; a failed syscall
  prevents execution and names the failure. No eligible CPUs refuses admission.
  Affinity is inherited by the workload's children.
  Snapshots do not claim pinning succeeded. After affinity and memory limits
  succeed, the helper creates `claude-pinned` immediately before exec and removes
  it if exec fails. A completed launch without that marker is an infrastructure
  failure, with no program exit status; the ledger finish records that outcome.
  A marked program may itself return 125, 126 or 127 without being misclassified.
- Read `/proc/meminfo` before staging. Reserve the declared memory against all
  active `agent: "claude"` ledger entries; ended jobs release their reservation.
  Wait while the total exceeds 7168 MB or the reservation would leave less
  than 1536 MB of `MemFree`. Re-read both ledger and memory after each wait;
  the configured timeout bounds admission waiting. Expiration refuses without
  staging the executable. Expected-end estimates never expire reservations.
- The owner-reported card has no taskset, and its cgroup memory controller is
  disabled with no mounted controllers. Nothing is mounted or enabled. Instead,
  `claude-pin` sets both soft and hard `RLIMIT_AS` to the declared MiB before
  exec; failure prevents execution. Address space is stricter than resident
  memory for a single process, and includes mappings and reservations as well
  as resident pages. The limit survives fork/exec, but is per process, not an
  aggregate descendant memory controller. Ledger admission bounds the sum of
  our declared job limits to 7 GiB; multi-process jobs must account for this
  per-process limitation. This is the backend explicitly selected by the owner.
- Stage exclusively in `/tmp/claude/claude-<random-id>/`, with executable
  `claude-program`, control shell name `claude-control`, and watchdog
  `claude-watchdog`. No ports are allocated. Short-lived system utilities
  retain their system utility names during control, transfer and cleanup. Each
  destructive operation checks the exact directory shape, its owner, physical cwd and original boot ID. Ownership
  uses the exact executable/cwd path, never a broad process name. A descendant
  that both execs outside our directory and changes cwd cannot be identified
  by this rule; the helper does not provide cgroup membership tracking.
- Report other users' processes in `foreign_processes`; leave them alone.
  Snapshots exclude the control shell's PID and its direct children by PPid,
  including before staging changes its cwd; foreign names do not grant exclusion.
  One shell pass reads process identities and skips kernel threads by PID/PPid.
  One numeric `ls` reads all user-process executable/cwd links and one `awk`
  joins them to identities. No snapshot forks `readlink` or a subshell per PID;
  the fake `/proc` test counts external commands with 300 kernel threads.
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
list is `readlink ls id cat od chmod tail head sleep mkdir rm rmdir awk` plus shell
builtins. The lead's probe reported `stat` and `base64` missing and `od`
available. Directory ownership now uses `LC_ALL=C ls -ldn` and `id -u`.
Program, static helper and watchdog bytes are uploaded on separate, bounded
SSH stdin streams to guarded `cat` commands, without an encoding tool. Output
uses `od -An -v -tx1` and host-side hexadecimal decoding, preserving binary
stdout/stderr. Every control operation is labelled (`snapshot`, `stage-create`,
`stage-chmod`, `start-job`, `read-stdout`, `read-stderr`, `read-status`,
`stop_owned`, `cleanup`, `reap-stale`, plus connection setup steps). Command
stderr is merged before the completion marker so nonzero status reports include
the step name and diagnostics. Deadlines and ended sessions also name the step
and include captured partial output. Upload failures name the file and include
stderr. A command's nonzero exit keeps the control protocol usable; a transport
failure invalidates that session. Admission happens before remote
mkdir or upload. The second SSH streams recheck the original boot and directory
owner/cwd; partial uploads remain in our directory for guarded cleanup.

## Build and native handoff

Run builds through `tools/run.py`. With the shared toolchain's `cross/bin` and
`cygwin/bin` on PATH, use that Cygwin's `python3.12` to run the wrapper. From a
Cygwin shell in this worktree, the donor build commands inside the wrapper are:

```sh
k1om-mpss-linux-gcc -O2 -static --sysroot=../_shared/toolchain/sysroot -L/cygdrive/c/Users/xuzhi/Documents/PhiWeather/.tools/knc-bootstrap/sysroot/usr/lib64 tools/claude-pin.c -o ../_shared/claude-pin.mic
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
Overlaps include jobs already active at admission and jobs starting during ours,
even when they also end during ours. Card minutes account only for execution;
there are no performance/timing claims. Classes are `program`, `refused`,
`timeout`, and `infrastructure`; runner exits are 125, 124, and 126 respectively.
The result class distinguishes program statuses that collide with those values.

`run` accepts program/argv, local and legacy external-lock/baseline arguments,
timeouts, result path, transport, ledger path, memory MB and an injectable
monotonic clock. A fake session provides `snapshot`, `stage`, `execute`,
`reap_stale`, `signal_owned`, `cleanup` and `close`. Snapshots contain boot ID, processes,
raw cpuinfo/meminfo, and may report known pinning unavailability for early
refusal. SSH checks enforcement at execution through the helper marker.
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
