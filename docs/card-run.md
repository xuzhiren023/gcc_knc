# S0-04 card runner

Source: `docs/DEVELOPMENT_CYCLE.md`, section 9, and the S0-04 lead answer
of 2026-11-02 10:39. The spec and RED tests were approved on 2026-11-02.
Native acceptance remains subject to the owner's card hold.

## Entry point and configuration

`python tools/card_run PROGRAM [ARG ...]` stages a host-built card executable
and runs it once. Options select the configuration, own lock, external locks,
baseline daemon names, execution limit, transport limit, and result JSON path.
All limits must be finite and positive. No automatic retry is permitted.

The owner supplies gitignored `config/card.local.json` with `host`, `identity`,
and `knownHosts`. Commit only an example with placeholders. Never read the
PhiWeather configuration or put key material in git. Connection arguments are:

```
C:/Windows/System32/OpenSSH/ssh.exe -F NUL -i <identity>
  -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes
  -o GlobalKnownHostsFile=NUL -o UserKnownHostsFile=<knownHosts>
  -o HostKeyAlgorithms=ssh-ed25519 -o ConnectTimeout=5 root@<host>
```

Copy `config/card.example.json` to the local file and fill in the owner paths.
Configure `externalLocks` with every other project's lock for this card and
`baselineNames` with reviewed system daemon/kernel thread names. The empty
allowlist in the example fails closed. Do not allow general job/interpreter
names such as `sh`. Optional `ownLock` must be inside this worktree (default
`.card.lock`); existing locks require owner intervention. CLI options are
`--config`, `--lock`, repeated `--external-lock` and `--baseline-name`,
`--timeout`, `--transport-timeout`, and `--receipt`, before PROGRAM.
The default overwritten result is `tests/out/card-result.json`.

The remote card needs a POSIX `sh`, Linux `/proc`, and standard utilities
`readlink`, `stat`, `id`, `cat`, `base64`, `chmod`, `tail`, `head`, `sleep`,
`mkdir`, and `rm`. No remote Python or installed runner is required. Inputs
are base64 chunks over the control session. Program output is read in bounded
chunks from private files, decoded and written to the corresponding host
stdout/stderr stream without text conversion. Their interleaving is not kept.
If transport becomes unavailable, the result reports incomplete cleanup;
it does not claim the remote program stopped.

Host file paths and remote arguments must be passed without shell interpolation.
The production transport must bound connecting, snapshots, staging, execution,
signalling, and cleanup. An expired SSH operation is an infrastructure failure;
an expired program limit is a timeout. Disconnecting SSH alone does not establish
that the remote program stopped.

## Locks, process policy, and lifecycle

1. Exclusively create the configured own lock inside our tree. If already
   present, report and refuse, including when stale. Do not remove a lock this
   invocation did not acquire. Hold an acquired lock through cleanup and release
   it on all exit paths.
2. Stat every configured external lock. A present lock means refuse. An
   unreadable/indeterminate check fails closed. External paths are configuration,
   not hardcoded PhiWeather paths; never open for writing, remove, or refresh
   them. No remote access is needed when a local lock prevents the run.
3. Use one SSH control session for the initial process/boot snapshot, staging,
   pre-execution snapshot, and execution. Allocate a fresh private directory
   matching exactly `/var/volatile/tmp/gcc-knc-[0-9a-f]{32}`. All input files,
   job control files, and runner-owned card processes belong there. Control
   helpers must also satisfy the ownership rule. The connection may create this
   empty directory and enter it for its control shell before the first process
   check; no program inputs are staged until that check passes. Clean up this
   directory even if the first process check refuses. Do not install system files.
4. Before staging inputs and again immediately before execution, check all card
   processes. A process is ours only if its resolved exe or cwd is inside that
   exact directory (component boundary required). Otherwise it must have a name
   in the configured baseline allowlist of system daemons. Missing/unknown
   identity is foreign. Report offending PIDs/names and refuse. Never signal or
   otherwise act on a foreign process. A process appearing after staging still
   prevents execution. The pre-execution check and launch share the SSH session.
5. Record the initial boot ID. Recheck before execution and after execution,
   and before any signal or removal. Reboot and unreachable card are
   infrastructure failures, not program failures. Do not retry. A subsequent
   invocation chooses a fresh directory and stages inputs again.
6. On timeout, stop only processes whose exe or cwd is inside this invocation's
   exact directory. Never kill by name or broad process group. Bounded TERM/KILL
   escalation may target only those processes while the boot ID still matches.
7. Clean up that exact directory on success and failure, but only on the
   original boot. Validate directory shape and ownership before every destructive
   operation; the boot check must also be enforced by the remote operation.
   If boot changed or cannot be read, do not signal or remove anything. Report
   incomplete cleanup as infrastructure failure. Close the session and release
   our own local lock even if remote cleanup is impossible.

## Results

Return and write one small JSON result at the configured output path, overwritten
on the next invocation. This is runtime output, kept out of git, not a provenance
artifact. Fields are `result_class`, `exit_code`, `program_exit_code`,
`boot_id_before`, `boot_id_after`, `card_minutes`, and `detail`. Unknown boot IDs
are null. Card minutes are monotonic wall time around program execution divided
by 60, including execution until timeout; staging and lock waits are excluded.

Classes are `program` (including a nonzero program exit), `refused`, `timeout`,
and `infrastructure`. Preserve the program's status and stdout/stderr. Export
three distinct nonzero constants `REFUSED_EXIT`, `TIMEOUT_EXIT`, and `INFRA_EXIT`
for runner failures. `program_exit_code` is null if no program status was
obtained. Infrastructure takes precedence if boot changed or cleanup failed.
A process exit status alone cannot distinguish all 256 program statuses from
runner errors; `result_class` is authoritative when the numbers overlap.
The lead approved this status-collision policy before GREEN.

## Fake transport seam for T0

`tools/card_run` exposes the following Python function, also used by its CLI:

```
run(program, argv, *, lock_path, external_locks, baseline_names,
    timeout, transport_timeout, receipt_path, transport, monotonic) -> dict
```

Paths are `pathlib.Path` objects on the host. `monotonic` is a callable defaulting
to `time.monotonic`; the injected test clock avoids sleeps. The return value
matches the result JSON. The CLI constructs the production transport; T0 never
constructs it or needs connection configuration.

`transport.connect(run_dir, timeout=...)` creates the empty control directory,
enters it, and returns a single session supporting:

- `snapshot(timeout=...)`: dict with `boot_id` and `processes`; each process has
  `pid`, `name`, `exe`, `cwd` (identity fields may be null).
- `stage(run_dir, program, timeout=...)`: copies the input into the private dir.
- `execute(run_dir, argv, timeout=...)`: returns the program's integer status;
  streams output; raises `TimeoutError` only for the program deadline.
- `signal_owned(run_dir, boot_id, timeout=...)`: stops only owned processes,
  enforcing the boot guard remotely too.
- `cleanup(run_dir, boot_id, timeout=...)`: removes only that directory, enforcing
  the boot guard remotely too.
- `close()`: releases the control session locally.

Other transport errors raise `OSError`. Operations are bounded by
`transport_timeout`, except execution, which uses `timeout`. The transport
must not add retries. Snapshots and destructive operations fail closed.

T0's seven cases cover existing own/external locks, foreign processes before
staging and before execution, timeout, unreachable card, reboot during a run,
nonzero program exit, and cleanup after staging failure. Assertions inspect
operation order, boundaries, boot IDs, lock release, result JSON, and card time.
At RED, missing `tools/card_run` was the expected failure.

After review and GREEN, when the card is free, run donor-built `m1_affine` and
`hello` through `tools/run.py` and this runner at T3. `m1_affine` must print
`ACCEPT-PASS`; that is the fixture/runner/guard-page check on actual hardware.
Do not describe a fake result as native evidence.
