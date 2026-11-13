"""S11-02 red contract: transfer policy with fake endpoints, never card jobs.

The proposed card_dma.transfer_file API takes source/destination names, the
declared size, direction (up/down), method (auto/ssh/dma), threshold_bytes,
and backends keyed by method. A backend stages into a private destination and
returns bytes, seconds and file_complete. Only the policy
may call publish(private, destination) after checking that evidence.

TransferFailure carries kind, data_started and cleanup_confirmed. These are
endpoint observations, never guesses from a timeout or process exit. The fake
models file visibility and reported cleanup; it does not emulate SCIF lifetime,
registration, DMA completion, or native throughput.
"""
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys
import unittest
from unittest.mock import Mock, patch
import runpy
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
SPEC = importlib.util.find_spec("card_dma")
if SPEC is not None:
    import card_dma

MIB = 1024 * 1024
SOURCE = "/source/claude-payload"
DESTINATION = "/destination/claude-payload"


class FakeEndpoint:
    def __init__(self, method, data, events, visible, *, failure=None,
                 completed=True, count_delta=0, seconds=2.0):
        self.method, self.data = method, data
        self.events, self.visible = events, visible
        self.failure = failure
        self.completed, self.count_delta = completed, count_delta
        self.seconds = seconds
        self.private = {}

    def stage(self, source, private, *, size, direction):
        self.events.append((self.method, "stage", source, private, size, direction))
        if private == DESTINATION:
            raise AssertionError("transfer wrote the published name before validation")
        if PurePosixPath(private).parent != PurePosixPath(DESTINATION).parent:
            raise AssertionError("private file must be beside destination for rename")
        if not PurePosixPath(private).name.startswith("claude-"):
            raise AssertionError("private transfer names must retain claude- ownership")
        if self.visible[DESTINATION] != b"previous complete file":
            raise AssertionError("staging changed the published destination")
        if self.failure:
            kind, started, cleaned = self.failure
            if started:
                self.private[private] = self.data[:17]
            if cleaned:
                self.private.clear()
                self.events.append((self.method, "cleanup-confirmed"))
            raise card_dma.TransferFailure(
                "injected " + kind, kind=kind, data_started=started,
                cleanup_confirmed=cleaned)
        received = self.data
        self.private[private] = received
        result = dict(bytes=len(received) + self.count_delta, seconds=self.seconds,
                      file_complete=self.completed)
        self.events.append((self.method, "evidence", result))
        return result

    def publish(self, private, destination):
        self.events.append((self.method, "publish", private, destination))
        self.visible[destination] = self.private.pop(private)


class TransferPolicy(unittest.TestCase):
    def test_mode_before_publish_and_lf_validation_program(self):
        # The old fake modeled bytes only; it never ran the publication shell
        # or the generated script, so it could not catch modes or CRLF shebangs.
        import host_card_transfer as build
        runner = runpy.run_path(str(ROOT / "tools/card_run"))
        with tempfile.TemporaryDirectory(dir=build.SHARED) as temp:
            root = Path(temp)
            build.stage_production_validation(root)
            self.assertEqual((root / "claude-check.sh").read_bytes(),
                             b"#!/bin/sh\ntest -f claude-payload\n")
            for method in ("dma", "ssh"):
                for name, data, mode in (("claude-program", b"#!/bin/sh\n", "700"),
                                         ("claude-pin", b"elf", "700"),
                                         ("claude-unpack", b"elf", "700"),
                                         ("claude-extra", b"\x7fELF", "700"),
                                         ("claude-payload", b"data", "600")):
                    with self.subTest(method=method, name=name):
                        source = root / name
                        source.write_bytes(data)
                        session = object.__new__(runner["SSHSession"])
                        session.helper_free = False
                        session.transfer_method, session.threshold_bytes = method, 1
                        session.transfers, session.rpc = [], Mock()
                        session.file_helpers = Mock(return_value=dict(
                            bytes=len(data), seconds=0.01, file_complete=True))
                        session.send_path(name, source, 10)
                        command = session.rpc.call_args.args[0]
                        self.assertRegex(command, r"^guard_boot && chmod " + mode +
                                         r" -- (claude-part-[0-9a-f]+) && mv -- \1 " + name + r"$")
                        row = session.transfers[0]
                        self.assertGreaterEqual(row["wall_seconds"], row["publish_seconds"])

    def test_native_window_offsets(self):
        # The policy fake never executes registration or the C transfer loop.
        # Compile that actual loop with fake SCIF/file IO: no endpoint, card,
        import host_card_transfer as build
        source = (ROOT / "tools/transfer_bench.c").read_text()
        start = source.index("static int transfer_file(")
        end = source.index("static int file_payload(", start)
        function = source[start:end].replace("read(fd,", "read_file_fake(fd,")
        function = function.replace("close(fd)", "close_file_fake(fd)")
        mocks = r'''
#include <assert.h>
static uint64_t total, moved, peer, base;
static unsigned calls, registrations, releases, completions, file_closed;
static int sending, close_result;
static int *errno_fake(void) {return &errno;}
static int64_t reg_fake(endpoint e,void *p,size_t n,int64_t o,int prot,int flags) {
  assert(!o && !flags && n==67108864 && prot==(sending?1:2));
  registrations++;return (int64_t)base;
}
static int read_fake(endpoint e,int64_t local,size_t n,int64_t remote,int flags) {
  size_t expected=total-moved>67108864?67108864:(size_t)(total-moved);
  assert((uint64_t)local==base && (uint64_t)remote==peer && flags==4);
  assert(n==((expected+63)&~(size_t)63) && n<=window_size);calls++;return 0;
}
static int unreg_fake(endpoint e,int64_t offset,size_t n) {
  assert((uint64_t)offset==base && n==window_size && moved==total);
  assert(completions==2 && file_closed);releases++;return 0;
}
static int close_fake(endpoint e) {return close_result;}
static int recv_fake(endpoint e,void *p,int n,int flags) {errno=ECONNRESET;return -1;}
static int stat_fake(int fd,struct stat *s) {s->st_mode=S_IFREG;s->st_size=total;return 0;}
static void exact_fake(void *p,size_t n,int send) {
  if(n==8 && !send)memcpy(p,&peer,8);
}
static void token_fake(char c,int send) {
  if(c=='V') {assert(moved==total && file_closed);completions++;}
}
#define open(...) 7
#define close_file_fake(...) (file_closed=1,0)
#define read_file_fake(...) 0
#define fstat stat_fake
#define connect_transport(...) (opened=1)
#define exact exact_fake
#define token token_fake
#define file_io(fd,p,n,w) (moved+=(n))
'''
        main = r'''
int main(int argc,char **argv) {
  if(!strcmp(argv[1],"cleanup")) {
    cancelled=opened=registered=1;sc.close=close_fake;close_result=atoi(argv[2]);
    cleanup();return 0;
  }
  total=strtoull(argv[1],0,0);peer=strtoull(argv[2],0,0);
  base=(UINT64_C(1)<<62)+4096;sending=atoi(argv[3]);
  sc.reg=reg_fake;sc.read=read_fake;sc.unreg=unreg_fake;
  sc.close=close_fake;sc.recv=recv_fake;
  native_errno=errno_fake;
  transfer_file(1,"scif-read","0",0,"01234567890123456789012345678901",
                total,sending?"up":"down","unused");
  assert(registrations==1 && releases==1 && moved==total);
  assert(calls==(sending?0:(total+67108863)/67108864));return 0;
}
'''
        with tempfile.TemporaryDirectory(dir=build.SHARED, prefix="offset-test-") as temp:
            path = Path(temp) / "offset.c"
            path.write_text(source[:start] + mocks + function + main)
            exe = path.with_suffix(".exe")
            subprocess.run([str(build.TC / "cygwin/bin/gcc.exe"), "-O0", "-std=gnu11",
                            "-I" + str(ROOT / "tools"), str(path), "-o", str(exe)],
                           env=build.ENV, check=True, capture_output=True)
            for size in (1073741824, 1073741841):
                for peer in (4096, (1 << 62) + 4096, (1 << 63) - 67108864):
                    for sender in (0, 1):
                        result = subprocess.run([str(exe), str(size), str(peer), str(sender)],
                                                env=build.ENV, capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, (size, peer, sender, result.stderr))
                        row = json.loads(result.stderr)
                        self.assertEqual(set(row), {"file_complete", "bytes", "cleanup_confirmed",
                                                    "seconds", "wall_seconds", "io_seconds"})
                        self.assertEqual(row["bytes"], size)
                        self.assertIs(row["file_complete"], True)
                        self.assertGreaterEqual(row["wall_seconds"], row["io_seconds"])
            for peer in (4097, (1 << 63) - 4096, 1 << 63):
                result = subprocess.run([str(exe), "1073741824", str(peer), "0"],
                                        env=build.ENV, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
            for failed in (0, 1):
                result = subprocess.run([str(exe), "cleanup", str(failed)],
                                        env=build.ENV, capture_output=True, text=True)
                self.assertEqual('"endpoint_closed":true' in result.stderr, not failed)
                self.assertEqual(result.returncode, 2 if failed else 0)

    def test_error_cleanup_requires_both_close_reports_and_exits(self):
        before = {"boot": "same", "bugcheckRecord": 123}
        for missing, live, changed, guard_error in ((False, False, False, False),
                (True, False, False, False), (False, True, False, False),
                (False, False, True, False), (False, False, False, True)):
            session = Mock()
            pair = card_dma.HelperPair(session, 10)
            pair.procs = [Mock(returncode=2), Mock(returncode=None if live else 2)]
            pair.rows = {"host": [{"endpoint_closed": True}],
                         "card": [] if missing else [{"endpoint_closed": True}]}
            if guard_error:
                session.rpc.side_effect = OSError("boot guard refused")
            with patch("host_card_transfer.event_log", return_value={} if changed else before):
                if changed or guard_error:
                    with self.assertRaises(OSError):
                        pair.release_dma(before)
                else:
                    self.assertEqual(pair.release_dma(before), not (missing or live))
            self.assertEqual(session.dma_latch.unlink.call_count,
                             int(not (missing or live or changed or guard_error)))
            if not (missing or live or changed):
                self.assertEqual(session.rpc.call_args.args[0],
                                 "guard_boot && rm -- claude-dma-active")

    def test_helper_free_ssh(self):
        runner = runpy.run_path(str(ROOT / "tools/card_run"))
        for method, present in (("ssh", False), ("ssh", True), ("auto", False)):
            with patch.object(Path, "is_file", return_value=present):
                transport = runner["SSHTransport"]({}, 10, transfer=method)
            with patch.object(Path, "stat", return_value=Mock(st_size=123)) as stat:
                overhead = transport.stage_overhead()
            self.assertEqual((transport.helper_free, stat.call_count, overhead),
                             (True, 1, 123 + len(runner["watchdog_bytes"]())))
            session = object.__new__(runner["SSHSession"])
            session.helper_free, session.transfer_method, session.transfers = True, method, []
            session.upload, session.rpc = Mock(), Mock(return_value="3")
            session.send_file("claude-payload", b"abc", 10)
            command = session.upload.call_args.args[1]
            self.assertRegex(command, r"^cat > claude-part-[0-9a-f]+$")
            self.assertEqual(session.upload.call_args.args[2], b"abc")
            self.assertIn(" && mv -- " + command[6:] + " claude-payload",
                          session.rpc.call_args.args[0])
            row = session.transfers[0]
            self.assertEqual((row["method"], row["bytes"], row["file_complete"]), ("ssh", 3, True))
            self.assertEqual(row["fallback"], dict(method="dma", reason="dma unavailable: helper missing")
                             if method == "auto" else None)
        with patch.object(Path, "is_file", return_value=False):
            for options in (dict(transfer="dma"), dict(collect=["claude-payload"])):
                with self.assertRaises(runner["Refused"]):
                    runner["SSHTransport"]({}, 10, **options)

    def setUp(self):
        self.assertIsNotNone(
            SPEC, "S11-02: tools/card_dma.py shared transfer policy is not implemented")

    def fixture(self, size=MIB, **dma_options):
        self.data = (bytes(range(256)) * ((size + 255) // 256))[:size]
        self.events = []
        self.visible = {DESTINATION: b"previous complete file"}
        self.backends = {
            "dma": FakeEndpoint("dma", self.data, self.events, self.visible, **dma_options),
            "ssh": FakeEndpoint("ssh", self.data, self.events, self.visible),
        }

    def transfer(self, direction="up", **options):
        return card_dma.transfer_file(
            SOURCE, DESTINATION, size=len(self.data), direction=direction,
            backends=self.backends, **options)

    def attempts(self):
        return [event[0] for event in self.events if event[1] == "stage"]

    def assert_receipt(self, receipt, method, fallback=None):
        self.assertEqual(receipt["method"], method)
        self.assertEqual(receipt["bytes"], len(self.data))
        self.assertEqual(receipt["seconds"], 2.0)
        self.assertAlmostEqual(receipt["mib_per_second"], len(self.data) / MIB / 2)
        self.assertIs(receipt["file_complete"], True)
        self.assertEqual(set(receipt), {"method", "bytes", "seconds", "file_complete", "fallback",
                                       "mib_per_second", "publish_seconds", "wall_seconds"})
        self.assertEqual(receipt["fallback"], fallback)
        self.assertEqual(self.visible[DESTINATION], self.data)

    def test_default_auto_threshold_in_both_directions(self):
        for direction in ("up", "down"):
            for size, expected in ((0, "ssh"), (MIB - 1, "ssh"),
                                   (MIB, "dma"), (MIB + 1, "dma")):
                with self.subTest(direction=direction, size=size):
                    self.fixture(size)
                    receipt = self.transfer(direction)
                    self.assertEqual(self.attempts(), [expected])
                    self.assert_receipt(receipt, expected)
                    self.assertEqual(self.events[0][-1], direction)

    def test_configurable_threshold_and_explicit_choice(self):
        for options, expected in ((dict(threshold_bytes=2 * MIB), "ssh"),
                                  (dict(threshold_bytes=MIB // 2), "dma"),
                                  (dict(method="ssh"), "ssh")):
            with self.subTest(options=options):
                self.fixture()
                self.assert_receipt(self.transfer(**options), expected)
                self.assertEqual(self.attempts(), [expected])
        self.fixture(17)
        self.assert_receipt(self.transfer(method="dma"), "dma")
        self.assertEqual(self.attempts(), ["dma"])

    def test_safe_fallback_records_reason_and_never_retries_dma(self):
        for direction in ("up", "down"):
            for failure in (("unavailable", False, False), ("io", True, True)):
                with self.subTest(direction=direction, failure=failure):
                    self.fixture(failure=failure)
                    receipt = self.transfer(direction)
                    self.assertEqual(self.attempts(), ["dma", "ssh"])
                    self.assert_receipt(receipt, "ssh", {
                        "method": "dma", "reason": "injected " + failure[0]})
                    self.assertFalse(self.backends["dma"].private)
                    if failure[1]:
                        cleanup = self.events.index(("dma", "cleanup-confirmed"))
                        ssh = next(i for i, e in enumerate(self.events) if e[:2] == ("ssh", "stage"))
                        self.assertLess(cleanup, ssh)

    def test_unsafe_failure_stops_without_fallback_or_publish(self):
        failures = (("unavailable", True, False), ("io", True, False),
                    ("io", False, False), ("integrity", True, True),
                    ("integrity", False, True), ("bugcheck", False, True),
                    ("bugcheck", True, False), ("uncertain_cleanup", True, True))
        for direction in ("up", "down"):
            for failure in failures:
                with self.subTest(direction=direction, failure=failure):
                    self.fixture(failure=failure)
                    with self.assertRaises(card_dma.TransferFailure):
                        self.transfer(direction)
                    self.assertEqual(self.attempts(), ["dma"])
                    self.assertFalse(any(e[1] == "publish" for e in self.events))
                    self.assertEqual(self.visible[DESTINATION], b"previous complete file")

    def test_fallback_failure_does_not_loop(self):
        self.fixture(failure=("unavailable", False, False))
        self.backends["ssh"].failure = ("io", True, True)
        with self.assertRaises(card_dma.TransferFailure):
            self.transfer()
        self.assertEqual(self.attempts(), ["dma", "ssh"])
        self.assertEqual(self.visible[DESTINATION], b"previous complete file")

    def test_completion_and_exact_length_are_required_before_publish(self):
        for direction in ("up", "down"):
            for method in ("dma", "ssh"):
                for corruption in ("incomplete", "short", "long"):
                    with self.subTest(direction=direction, method=method, corruption=corruption):
                        self.fixture()
                        endpoint = self.backends[method]
                        endpoint.completed = corruption != "incomplete"
                        endpoint.count_delta = {"incomplete": 0, "short": -1, "long": 1}[corruption]
                        with self.assertRaises(card_dma.TransferFailure) as caught:
                            self.transfer(direction, method=method)
                        self.assertEqual(caught.exception.kind, "integrity")
                        self.assertEqual(self.attempts(), [method])
                        self.assertFalse(any(e[1] == "publish" for e in self.events))
                        self.assertEqual(self.visible[DESTINATION], b"previous complete file")

    def test_private_stage_then_evidence_then_publish(self):
        for direction in ("up", "down"):
            for method in ("dma", "ssh"):
                with self.subTest(direction=direction, method=method):
                    self.fixture()
                    self.assert_receipt(self.transfer(direction, method=method), method)
                    self.assertEqual([e[1] for e in self.events], ["stage", "evidence", "publish"])
                    staged, _, published = self.events
                    self.assertEqual(staged[2], SOURCE)
                    self.assertEqual(staged[3], published[2])
                    self.assertNotEqual(staged[3], DESTINATION)
                    self.assertEqual(published[3], DESTINATION)
                    self.assertFalse(self.backends[method].private)


if __name__ == "__main__":
    unittest.main()
