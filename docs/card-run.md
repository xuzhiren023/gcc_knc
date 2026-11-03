# Shared-card runner (S2-11)

`python tools/card_run PROGRAM [ARG ...]` runs a host-built executable on the
card. The owner rules on ticket S2-11 dated 2026-11-03 supersede S0-04's
foreign-process refusal and the old external workload lock.

## Configuration

The default configuration is the main checkout's gitignored
`config/card.local.json`, including from `<main>/.work/<ticket>`. It is never
copied into a worktree. Required settings are `host`, `identity`, `knownHosts`
and `ledger`; `memoryMB` defaults to 128, `timeout` to 60 seconds and
`transportTimeout` to 10 seconds. Limits must be finite and positive; memory
must be an integer from 1 through 7168 MB.

SSH uses the configured identity, strict known-host checking, batch mode,
`IdentitiesOnly=yes`, `HostKeyAlgorithms=ssh-ed25519`, no user SSH config,
and a five-second connection timeout. There are no automatic retries.
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
  job appends an end record after cleanup, also on staging/program failure,
  timeout or card fault. Ledger write errors are infrastructure failures.
- Hold our local lock (default `<main>/.work/_state/card.lock`) and a mandatory
  `claude-admission.lock` beside the ledger through final ledger writes.
  The latter prevents callers with different `--lock` values from racing our
  admission checks. These locks serialize our invocations; other projects do
  not take them. Create atomically, refuse on existing/stale locks, and remove
  only locks this invocation created. No external/shared-card lock is taken.
- Parse the card's `/proc/cpuinfo` processor/core pairs. Select only logical
  CPUs belonging to physical cores 30 through 59; never core 60. Pass that
  explicit CPU list to `taskset -c` at launch. Missing pinning or eligible CPUs
  refuses execution. Affinity is inherited by the workload's children.
- Read `/proc/meminfo` before staging. Reserve the declared memory against all
  active `agent: "claude"` ledger entries; ended jobs release their reservation.
  Wait while the total exceeds 7168 MB or the reservation would leave less
  than 1536 MB of `MemFree`. Re-read both ledger and memory after each wait;
  the configured timeout bounds admission waiting. Expiration refuses without
  staging the executable. Expected-end estimates never expire reservations.
- The production memory backend requires an already-mounted cgroup v1 memory
  controller. It creates only a private `claude-<job-id>` group under that
  controller, writes `memory.limit_in_bytes`, enables hierarchy within our group,
  and moves the workload shell into it before exec. The limit covers the
  workload and descendants. There is no controller mount or global setting
  change. Missing/unusable enforcement stops launch with a named diagnostic.
  Its compatibility with the actual card remains unverified (see below).
- Stage exclusively in `/tmp/claude/claude-<random-id>/`, with executable
  `claude-program`, control shell name `claude-control`, and watchdog
  `claude-watchdog`. No ports are allocated. Short-lived system utilities
  currently retain their system process names; full naming compliance remains
  pending native tool discovery. Each destructive operation checks the exact
  directory shape, its owner, physical cwd and original boot ID. Ownership
  includes the workload's cgroup members, so changing cwd does not evade cleanup.
- Report other users' processes in `foreign_processes`; leave them alone.
  Signals target only processes in our exact directory or private resource
  group, rechecking identity after the boot guard, never by broad name/group.
  Guarded TERM/KILL cleanup removes our empty resource group and exact staging
  directory. Stdout/stderr are copied back in bounded chunks before normal
  cleanup. A separate HUP-ignoring watchdog applies the same guards after the
  program timeout plus `max(5 seconds, 2 * transportTimeout)` grace.
- Recheck boot ID before execution, after execution and before any signal or
  removal. A changed boot or unreachable card mid-run is an infrastructure
  failure: append `card-fault`, then end; do not signal/remove on an unknown or
  changed boot, and do not reconnect. Report the fault on the ticket so the lead
  can escalate. The independent watchdog also refuses destructive operations
  on another boot.

Required utility checks run before creating a remote staging directory. They
name every missing tool rather than returning an unexplained status 94. The
current list is `readlink stat id cat base64 chmod tail head sleep mkdir rmdir
rm`; `taskset` is checked separately as the pinning capability. Replacements
must be selected from the actual card's tools after the permitted hello probe.

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
`signal_owned`, `cleanup` and `close`. Snapshots contain boot ID, processes,
raw cpuinfo/meminfo and pinning availability. Execute receives the explicit
logical CPU list, memory MB, execution timeout and watchdog timeout.
`tests/tools/test_card_shared.py` tests the shared rules without SSH; its shell
fixture locates `sh` through PATH.

## Validation status

The approved RED is ae87007. The 18 shared-policy T0 cases passed during GREEN
implementation, before subsequent resource-group cleanup and admission-lock
hardening. The donor built `tests/tools/card_hello.c` with the shared sysroot.
The native hello probe was blocked before connecting: the session could not
read the configured SSH identity and SSH connection permission was denied.
No card tools were discovered and no native job ran. Required BusyBox
replacements and their T0 cases, final backend validation, and native acceptance
remain pending the ticket's access blocker. Old S0-04 fake expectations for
foreign refusal/external locks and the old staging path are superseded; that
legacy test module has not yet been migrated.
