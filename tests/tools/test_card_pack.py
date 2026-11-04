"""S4-12: a whole batch staged in one pack stream; fake card transport and a host-built helper only."""
from pathlib import Path
import runpy
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import uuid

ROOT = Path(__file__).resolve().parents[2]
ELF = b"\x7fELF"
BOOT = "test-boot"


def entry(name, data, mode=None):
    if mode is None:
        mode = b"700" if data.startswith(ELF) else b"600"
    name = name.encode() if isinstance(name, str) else name
    return mode + b" %d " % len(data) + name + b"\n" + data


def pack(*entries, count=None):
    return (b"claude-pack 1\n" + b"".join(entries) +
            b"end %d\n" % (len(entries) if count is None else count))


def posix_modes(directory):
    if sys.platform == "cygwin":
        # Keep inherited Windows ACLs out of POSIX-mode fixtures (as test_card_backend).
        subprocess.run([shutil.which("setfacl"), "-b", "-k", str(directory)],
                       check=True, capture_output=True)


class PackFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The card helper is never run on the host; this is the same source built for the host.
        cls.build = tempfile.TemporaryDirectory(dir=ROOT)
        cls.helper = Path(cls.build.name) / "claude-unpack-host.exe"
        compiled = subprocess.run([shutil.which("gcc"), "-Wall", "-Wextra", "-Werror", "-O2",
                                   str(ROOT / "tools/claude-unpack.c"), "-o", str(cls.helper)],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if compiled.returncode:
            cls.build.cleanup()
            raise AssertionError(compiled.stdout.decode(errors="replace"))

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def scratch(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        posix_modes(directory)
        return directory


class UnpackHelper(PackFixture):
    def unpack(self, stream, declared=None, link=False):
        parent = self.scratch()
        run = parent / "run"
        run.mkdir()
        outside = parent / "outside"
        outside.write_bytes(b"keep")
        if link:
            (run / "link").symlink_to(outside)
        before = sorted(p.name for p in run.iterdir())
        done = subprocess.run([str(self.helper), str(len(stream) if declared is None else declared)],
                              input=stream, cwd=run, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return done, parent, run, before

    def test_valid_stream_writes_exact_bytes_and_modes(self):
        files = {"claude-batch.mic": ELF + bytes(range(256)), "input ' data": b"\x00\xffdata\n",
                 "empty": b""}
        done, parent, run, _ = self.unpack(pack(*(entry(n, d) for n, d in files.items())))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(sorted(p.name for p in run.iterdir()), sorted(files))
        for name, data in files.items():
            self.assertEqual((run / name).read_bytes(), data)
            self.assertEqual((run / name).stat().st_mode & 0o777, 0o700 if data.startswith(ELF) else 0o600)

    def test_malformed_or_traversing_stream_refused_with_nothing_outside(self):
        good = entry("a", b"abc")
        cases = {
            "traversal": pack(entry("../escape", b"x")),
            "absolute": pack(entry(str(Path(tempfile.gettempdir()) / ("claude-abs-" + uuid.uuid4().hex)), b"x")),
            "backslash": pack(entry("..\\escape", b"x")),
            "dot": pack(entry(".", b"x")),
            "dotdot": pack(entry("..", b"x")),
            "empty name": pack(entry("", b"x")),
            "nul in name": pack(entry(b"a\x00b", b"x")),
            "long name": pack(entry("n" * 300, b"x")),
            "duplicate": pack(good, entry("a", b"other")),
            "reserved status": pack(good, entry("status", b"0\n")),
            "reserved marker": pack(entry("claude-pinned", b"")),
            "reserved stdout": pack(entry("stdout", b"")),
            "reserved helper": pack(entry("claude-unpack", ELF)),
            "bad magic": b"claude-pack 2\n" + good + b"end 1\n",
            "no magic": good + b"end 1\n",
            "short header": b"claude-pack 1\n600 3",
            "short body": (b"claude-pack 1\n" + good)[:-1],
            "no end record": b"claude-pack 1\n" + good,
            "count mismatch": pack(good, count=2),
            "trailing data": pack(good) + b"x",
            "ELF marked 600": pack(entry("p", ELF + b"x", b"600")),
            "data marked 700": pack(entry("p", b"data", b"700")),
            "other mode": pack(entry("p", b"data", b"644")),
            "signed size": b"claude-pack 1\n600 +3 a\nabcend 1\n",
            "leading zero": b"claude-pack 1\n600 03 a\nabcend 1\n",
            "huge size": b"claude-pack 1\n600 99999999999999999999999 a\nabcend 1\n",
            "size beyond stream": b"claude-pack 1\n600 900 a\nabcend 1\n",
        }
        for label, stream in cases.items():
            with self.subTest(label):
                done, parent, run, before = self.unpack(stream)
                self.assertNotEqual(done.returncode, 0, label)
                self.assertTrue(done.stderr.startswith(b"claude-unpack: "), done.stderr)
                self.assertEqual(sorted(p.name for p in parent.iterdir()), ["outside", "run"])
                self.assertEqual(sorted(p.name for p in run.iterdir()), before)
        for declared in (len(pack(good)) - 1, len(pack(good)) + 1, "-1", "", "12x"):
            with self.subTest(declared=declared):
                done, parent, run, before = self.unpack(pack(good), declared=declared)
                self.assertNotEqual(done.returncode, 0)
                self.assertEqual(sorted(p.name for p in run.iterdir()), before)
        self.assertFalse(list(Path(tempfile.gettempdir()).glob("claude-abs-*")))
        # A planted symlink must not redirect a write outside the run directory.
        done, parent, run, before = self.unpack(pack(entry("link", b"overwrite")), link=True)
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual((parent / "outside").read_bytes(), b"keep")
        self.assertEqual(sorted(p.name for p in run.iterdir()), before)


class PackedStage(PackFixture):
    def test_three_hundred_file_job_opens_one_pack_upload(self):
        runner = runpy.run_path(str(ROOT / "tools/card_run"))
        remote = (ROOT / "tools/card_run_remote.sh").read_text()
        directory = self.scratch()
        (directory / "tmp/claude").mkdir(parents=True)
        proc = directory / "proc"
        (proc / "sys/kernel/random").mkdir(parents=True)
        (proc / "sys/kernel/random/boot_id").write_text(BOOT + "\n")
        session = object.__new__(runner["SSHSession"])
        session.run_dir = "/tmp/claude/claude-" + uuid.uuid4().hex
        session.boot_id, session.transport_timeout = BOOT, 1
        session.command = ["fake-ssh", "exec sh"]
        program = directory / "driver"
        program.write_bytes(ELF + b"driver")
        session.pin_helper = directory / "pin"
        session.pin_helper.write_bytes(ELF + b"pin")
        session.unpack_helper = self.helper
        batch = directory / "batch"
        batch.mkdir()
        files = []
        for index in range(300):
            path = batch / ("t%03d.mic" % index if index % 2 else "t%03d.list" % index)
            path.write_bytes((ELF if index % 2 else b"") + b"%d" % index * (index + 1))
            files.append(path)
        run_dir = directory / session.run_dir.lstrip("/")

        def translate(script):
            script = script.replace("mkdir -p /tmp/claude", "mkdir -p tmp/claude")
            return script.replace("/tmp", str(directory / "tmp")).replace("/proc/", str(proc) + "/")

        rpcs = []

        def rpc(script, timeout, **kwargs):
            rpcs.append(kwargs.get("step"))
            setup = remote + '\nrun_dir=%s\nboot_id=%s\n' % (shlex.quote(session.run_dir), BOOT)
            if not script.startswith("boot_id="):
                setup += 'cd -- "$run_dir" || exit 91\n'
            answer = subprocess.run([shutil.which("sh"), "-c", translate(setup + script)],
                                    cwd=directory, capture_output=True, timeout=60)
            self.assertEqual(answer.returncode, 0, answer.stdout + answer.stderr)
            return answer.stdout.rstrip(b"\n")

        session.rpc = rpc
        uploads = []
        actual_popen = subprocess.Popen

        def popen(command, **kwargs):
            self.assertEqual(command[0], "fake-ssh")
            uploads.append(command[-1])
            kwargs["cwd"] = directory
            return actual_popen([shutil.which("sh"), "-c", translate(shlex.split(command[-1])[-1])],
                                **kwargs)

        with mock.patch.object(runner["subprocess"], "Popen", side_effect=popen):
            session.stage(session.run_dir, program, files=files, timeout=60, packed=True)
        # Today: 303 upload connections and 301 chmod round trips. Packed: the
        # helper's own upload, then one stream for every other staged file.
        self.assertEqual(len(uploads), 2, uploads)
        self.assertIn("cat > claude-unpack", uploads[0])
        self.assertIn("./claude-unpack", uploads[1])
        self.assertLessEqual(len(rpcs), 3, rpcs)
        expected = {"claude-program": (program.read_bytes(), 0o700),
                    "claude-pin": (session.pin_helper.read_bytes(), 0o700),
                    "claude-watchdog.sh": (runner["watchdog_bytes"](), 0o600)}
        for path in files:
            data = path.read_bytes()
            expected[path.name] = (data, 0o700 if data.startswith(ELF) else 0o600)
        staged = {p.name for p in run_dir.iterdir()} - {"claude-unpack"}
        self.assertEqual(staged, set(expected))
        for name, (data, mode) in expected.items():
            self.assertEqual((run_dir / name).read_bytes(), data, name)
            self.assertEqual((run_dir / name).stat().st_mode & 0o777, mode, name)
        session.cleanup(session.run_dir, BOOT, timeout=30)
        self.assertFalse(run_dir.exists())


if __name__ == "__main__":
    unittest.main()
