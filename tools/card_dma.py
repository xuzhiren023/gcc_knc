"""S11-02 file transfer policy and guarded card_run adapters.

Only receiver-pull synchronous RMA is used. Helpers reuse S11-01's SCIF ABI
and SHA implementation. Timing separates payload movement from wall time
(which includes file IO, hashing, startup and teardown).
"""
import json
import math
import os
from pathlib import Path
import queue
import re
import secrets
import shlex
import subprocess
import threading
import time


class TransferFailure(OSError):
    def __init__(self, message, *, kind, data_started, cleanup_confirmed):
        super().__init__(message)
        self.kind = kind
        self.data_started = data_started
        self.cleanup_confirmed = cleanup_confirmed


def transfer_file(source, destination, *, size, direction, backends,
                  method="auto", threshold_bytes=1048576):
    if (method not in ("auto", "dma", "ssh") or direction not in ("up", "down")
            or not isinstance(size, int) or size < 0
            or not isinstance(threshold_bytes, int) or threshold_bytes < 0):
        raise ValueError("invalid file transfer selection, direction or length")
    chosen = ("dma" if size >= threshold_bytes else "ssh") if method == "auto" else method
    # POSIX separators also work for the absolute Windows destinations passed
    # by card_run. A new private name is used for the single permitted fallback.
    def attempt(backend):
        parent, _, _name = str(destination).replace("\\", "/").rpartition("/")
        private = (parent + "/" if parent else "") + "claude-part-" + secrets.token_hex(16)
        evidence = backend.stage(source, private, size=size, direction=direction)
        digest = evidence.get("source_sha256")
        if (evidence.get("bytes") != size or not isinstance(digest, str)
                or not re.fullmatch("[0-9a-f]{64}", digest)
                or evidence.get("received_sha256") != digest):
            raise TransferFailure("exact length or digest mismatch", kind="integrity",
                                  data_started=True, cleanup_confirmed=False)
        seconds = evidence.get("seconds")
        if not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
            raise TransferFailure("invalid transfer timing", kind="io",
                                  data_started=True, cleanup_confirmed=False)
        backend.publish(private, destination)
        return dict(evidence, method=chosen, digest_match=True,
                    mib_per_second=size / 1048576 / seconds if seconds else 0,
                    fallback=fallback)

    fallback = None
    try:
        return attempt(backends[chosen])
    except TransferFailure as error:
        safe = (error.kind not in ("integrity", "bugcheck", "uncertain_cleanup")
                and (error.cleanup_confirmed or
                     (error.kind == "unavailable" and not error.data_started)))
        if chosen != "dma" or method != "auto" or not safe:
            raise
        fallback = dict(method="dma", reason=str(error))
        chosen = "ssh"
        try:
            return attempt(backends[chosen])
        except TransferFailure as fallback_error:
            fallback_error.fallback = fallback
            raise


class Endpoint:
    """One helper pair; the SSHSession owns boot/path guards and publication."""
    def __init__(self, session, method, timeout):
        self.session, self.method, self.timeout = session, method, timeout
        self.direction = None

    def stage(self, source, private, *, size, direction):
        self.direction = direction
        return self.session.file_helpers(source, private, size, direction, self.method, self.timeout)

    def publish(self, private, destination):
        if self.direction == "up":
            self.session.rpc("guard_boot && mv -- %s %s" %
                             (shlex.quote(private), shlex.quote(destination)),
                             self.timeout, step="transfer-publish")
        else:
            self.session.rpc("guard_boot", self.timeout, step="collect-publish-guard")
            os.replace(private, destination)


def cygpath(path):
    path = Path(path).resolve().as_posix()
    return "/cygdrive/" + path[0].lower() + path[2:] if len(path) > 1 and path[1] == ":" else path


class HelperPair:
    """Drain both helpers without ever force-killing a SCIF process.

    The durable active marker requires two explicit close reports and exits,
    including error exits. A timeout or lost report leaves it for the lead;
    process exit alone is not proof of safe cleanup. No native action at import time.
    """
    def __init__(self, session, timeout):
        self.session = session
        self.deadline = time.monotonic() + timeout
        self.events = queue.Queue()
        self.rows = {"host": [], "card": []}
        self.errors = []
        self.procs = []

    def start(self, side, command, **kwargs):
        proc = subprocess.Popen(command, stderr=subprocess.PIPE, **kwargs)
        self.procs.append(proc)

        def drain():
            for line in iter(proc.stderr.readline, b""):
                try:
                    row = json.loads(line)
                except (ValueError, UnicodeError):
                    row = {"error": line.decode("utf8", "replace")[-1000:]}
                self.events.put((side, row))
            self.events.put((side, {"eof": True}))

        threading.Thread(target=drain, daemon=True).start()
        return proc

    def next(self):
        try:
            side, row = self.events.get(timeout=max(0.001, self.deadline - time.monotonic()))
        except queue.Empty as error:
            raise TransferFailure("helper deadline; endpoint cleanup uncertain", kind="uncertain_cleanup",
                                  data_started=True, cleanup_confirmed=False) from error
        if "error" in row:
            self.errors.append(row["error"])
        self.rows[side].append(row)
        return side, row

    def release_dma(self, before):
        # A successful scif_close report plus process exit keeps pinned pages
        # alive through endpoint teardown. Missing evidence must retain both
        # latches, even if a process listing happens to be empty.
        if (len(self.procs) != 2 or any(p.returncode is None for p in self.procs)
                or not all(any(r.get("endpoint_closed") is True or
                               (r.get("file_complete") is True and r.get("cleanup_confirmed") is True)
                               for r in rows) for rows in self.rows.values())):
            return False
        from host_card_transfer import event_log
        if event_log() != before:
            raise TransferFailure("host boot/bugcheck state changed", kind="bugcheck",
                                  data_started=True, cleanup_confirmed=False)
        self.session.rpc("guard_boot && rm -- claude-dma-active", self.left(), step="dma-release")
        self.session.dma_latch.unlink()
        return True

    def run(self, source, private, size, direction, method):
        s = self.session
        dma = method == "dma"
        if dma and not s.dma_enabled:
            raise TransferFailure("DMA disabled by dmaEnabled setting", kind="unavailable",
                                  data_started=False, cleanup_confirmed=False)
        if not s.host_helper.is_file():
            raise TransferFailure("host file helper missing: " + str(s.host_helper), kind="unavailable",
                                  data_started=False, cleanup_confirmed=False)
        nonce = secrets.token_hex(16)
        protocol = "scif-read" if dma else "pipe"
        remote_path = private if direction == "up" else source
        local_path = source if direction == "up" else private
        card_args = ["./claude-transfer", "file", "card", protocol, "0", "0", nonce,
                     str(size), direction, str(remote_path)]
        host_args = [str(s.host_helper), "file", "host", protocol, "0", "0", nonce,
                     str(size), direction, cygpath(local_path)]
        env = dict(os.environ, PATH=str(s.cygwin_bin) + os.pathsep + os.environ["PATH"])
        before = None
        if dma:
            from host_card_transfer import event_log
            try:
                probe = subprocess.run([str(s.host_helper), "scif-probe"], env=env,
                                       capture_output=True, timeout=self.left())
                before = event_log()
            except (OSError, subprocess.SubprocessError, ValueError) as error:
                # No endpoint exists yet. Failure to establish the required
                # host health baseline makes DMA unavailable for this file.
                raise TransferFailure("DMA preflight unavailable: " + str(error), kind="unavailable",
                                      data_started=False, cleanup_confirmed=False) from error
            if probe.returncode:
                raise TransferFailure("host SCIF ABI unavailable: " +
                                      probe.stderr.decode("utf8", "replace")[-500:],
                                      kind="unavailable", data_started=False, cleanup_confirmed=False)
            probe = s.rpc("guard_boot && if ./claude-transfer scif-probe; then echo available; "
                          "else echo unavailable; fi", self.left(), step="dma-probe")
            if probe.splitlines()[-1:] != [b"available"]:
                raise TransferFailure("card SCIF ABI unavailable", kind="unavailable",
                                      data_started=False, cleanup_confirmed=False)
            # Create before opening endpoints, so even a host bugcheck retains
            # a stop latch. No automatic recovery of this file is permitted.
            s.dma_latch.parent.mkdir(parents=True, exist_ok=True)
            with s.dma_latch.open("x", encoding="utf8") as latch:
                json.dump(dict(run_dir=s.run_dir, boot_id=s.boot_id, host_state=before), latch)
            s.rpc("guard_boot && (set -C; : > claude-dma-active)", self.left(), step="dma-protect")
        try:
            if dma:
                card = self.start("card", s.file_command(shlex.join(card_args)),
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                while True:
                    side, row = self.next()
                    if row.get("ready"):
                        host_args[4:6] = [str(row["node"]), str(row["port"])]
                        break
                    if row.get("eof"):
                        raise OSError("card DMA startup failed")
                host = self.start("host", host_args, env=env,
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            else:
                host = self.start("host", host_args, env=env,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                card = self.start("card", s.file_command(shlex.join(card_args)),
                                  stdin=host.stdout, stdout=host.stdin)
                host.stdout.close()
                host.stdin.close()
            while not all(any(r.get("eof") for r in rows) for rows in self.rows.values()):
                self.next()
            for proc in self.procs:
                proc.wait(timeout=self.left())
            reports = {side: next((r for r in rows if r.get("file_complete")), None)
                       for side, rows in self.rows.items()}
            if any(p.returncode for p in self.procs) or not all(reports.values()):
                detail = "; ".join(self.errors)[-2000:]
                cleaned = ("cleanup uncertain" not in detail and self.release_dma(before)) if dma else True
                raise TransferFailure("file helper failed: " + detail,
                                      kind="integrity" if "integrity" in detail else
                                      ("io" if cleaned else "uncertain_cleanup"),
                                      data_started=True, cleanup_confirmed=cleaned)
            a, b = reports["host"], reports["card"]
            if (a["bytes"] != size or b["bytes"] != size or a["sha256"] != b["sha256"]
                    or not all(r.get("digest_match") and r.get("cleanup_confirmed") for r in (a, b))):
                raise TransferFailure("helper evidence mismatch", kind="integrity",
                                      data_started=True, cleanup_confirmed=False)
            if dma:
                self.release_dma(before)
            receiver = b if direction == "up" else a
            return dict(bytes=size, source_sha256=a["sha256"], received_sha256=b["sha256"],
                        seconds=receiver["seconds"], wall_seconds=receiver["wall_seconds"],
                        timing_scope="payload; wall_seconds includes IO, hashing and handshake")
        except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as error:
            if dma:
                s.transfer_stop = True
            if isinstance(error, TransferFailure):
                raise
            raise TransferFailure("helper failure; cleanup uncertain: " + str(error),
                                  kind="uncertain_cleanup", data_started=True,
                                  cleanup_confirmed=False) from error
        except BaseException:
            # In particular, do not kill, terminate, send a signal, or infer
            # cleanup from a process return code here. The marker also blocks
            # card_run's watchdog and future stale recovery on this directory.
            if dma:
                s.transfer_stop = True
            raise

    def left(self):
        left = self.deadline - time.monotonic()
        if left <= 0:
            raise TransferFailure("helper deadline; cleanup uncertain", kind="uncertain_cleanup",
                                  data_started=True, cleanup_confirmed=False)
        return left
