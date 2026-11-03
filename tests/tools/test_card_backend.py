"""S2-11 owner-reported BusyBox replacements; local fake transport only."""
import io
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
import uuid

ROOT = Path(__file__).resolve().parents[2]


class CardBackend(unittest.TestCase):
    def setUp(self):
        self.runner = runpy.run_path(str(ROOT / "tools/card_run"))
        self.remote = (ROOT / "tools/card_run_remote.sh").read_text()
        self.session = object.__new__(self.runner["SSHSession"])
        self.session.run_dir = "/tmp/claude/claude-" + uuid.uuid4().hex
        self.session.boot_id = "test-boot"
        self.session.transport_timeout = 1
        self.session.rpc = mock.Mock(return_value=b"")

    def test_stat_replaced_by_numeric_ls_owner_guard(self):
        # Exercise the real guard on a local directory; stat is deliberately absent.
        directory = Path(self.session.run_dir)
        directory.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, directory)
        script = self.remote + '\nstat() { echo missing-stat >&2; return 94; }\n'
        script += 'run_dir="$1"\ncd "$run_dir" && guard_dir\n'
        answer = subprocess.run([shutil.which("sh"), "-c", script, "claude-test", str(directory)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(answer.returncode, 0, answer.stderr)

    def test_base64_staging_replaced_with_binary_stream_for_both_executables(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as name:
            program = Path(name) / "program"
            program.write_bytes(bytes(range(256)))
            self.session.send_file = mock.Mock()
            self.session.pin_helper = program
            self.session.stage(self.session.run_dir, program, timeout=5)
            uploads = self.session.send_file.call_args_list
            self.assertEqual([c.args[0] for c in uploads],
                             ["claude-program", "claude-pin", "claude-watchdog.sh"])
            self.assertEqual(uploads[0].args[1], bytes(range(256)))
            self.assertEqual(uploads[1].args[1], bytes(range(256)))
            self.assertNotIn("base64", "\n".join(c.args[0] for c in self.session.rpc.call_args_list))

    def test_binary_stream_uses_separate_guarded_ssh_and_preserves_bytes(self):
        self.session.command = ["fake-ssh", "exec sh"]
        child = mock.Mock(returncode=0)
        child.communicate.return_value = (b"", b"")
        data = bytes(range(256)) + b"\ncard_rc=0\x00\xff"
        with mock.patch.object(self.runner["subprocess"], "Popen", return_value=child) as spawn:
            self.assertTrue(hasattr(self.session, "send_file"), "raw SSH upload must be implemented")
            self.session.send_file("claude-program", data, 2)
        self.assertEqual(child.communicate.call_args.kwargs["input"], data)
        command = spawn.call_args.args[0]
        self.assertEqual(command[0], "fake-ssh")
        self.assertIn("guard_boot", command[-1])
        self.assertIn("cat > claude-program", command[-1])
        self.assertNotIn("base64", command[-1])

    def test_base64_output_replaced_with_od_hex_binary_roundtrip(self):
        data = bytes(range(256)) + b"\x00\xff\n"
        self.session.rpc.side_effect = [b"", data.hex().encode(), b"", b"0", b"", b""]
        stdout, stderr = io.BytesIO(), io.BytesIO()
        with mock.patch("sys.stdout", mock.Mock(buffer=stdout)), \
                mock.patch("sys.stderr", mock.Mock(buffer=stderr)):
            status = self.session.execute(self.session.run_dir, [], timeout=5, card_timeout=10,
                                          cpus=[4, 13, 91], memory_mb=128)
        self.assertEqual(status, 0)
        self.assertEqual(stdout.getvalue(), data)
        self.assertEqual(stderr.getvalue(), b"")
        scripts = "\n".join(c.args[0] for c in self.session.rpc.call_args_list)
        self.assertIn("od -An -v -tx1", scripts)
        self.assertNotIn("base64", scripts)

    def test_helper_launch_replaces_taskset_and_unmounted_cgroups(self):
        self.assertIn('./claude-pin "$job_cpus" "$job_memory"', self.remote)
        self.assertNotIn("taskset", self.remote)
        self.assertNotIn("memory.limit_in_bytes", self.remote)
        self.assertNotIn("/proc/mounts", self.remote)

    def test_static_helper_enforces_before_exec_and_fails_closed(self):
        self.assertTrue((ROOT / "tools/claude-pin.c").is_file(), "donor helper source is required")
        with tempfile.TemporaryDirectory(dir=ROOT) as name:
            executable = Path(name) / "claude-pin-test.exe"
            compiled = subprocess.run([shutil.which("gcc"), "-Wall", "-Wextra", "-Werror",
                                       str(ROOT / "tests/tools/card_pin_test.c"), "-o", str(executable)],
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertEqual(compiled.returncode, 0, compiled.stdout.decode(errors="replace"))
            tested = subprocess.run([str(executable)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertEqual(tested.returncode, 0, tested.stdout.decode(errors="replace"))


if __name__ == "__main__":
    unittest.main()
