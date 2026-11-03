"""S2-11 owner-reported BusyBox replacements; local fake transport only."""
import io
from pathlib import Path
import runpy
import shlex
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
import uuid

from test_card_shared import BOOT, SharedTransport

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

    def test_extra_files_raw_upload_modes_and_cleanup_with_card_sized_proc(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as name:
            directory = Path(name)
            proc = directory / "proc"
            (directory / "tmp").mkdir()
            (proc / "sys/kernel/random").mkdir(parents=True)
            (proc / "sys/kernel/random/boot_id").write_text(self.session.boot_id + "\n")
            (proc / "cpuinfo").write_text("\n\n".join(
                "processor : %d\ncore id : %d\n" % (cpu, cpu // 4 + 1) +
                "\n".join("unused : ignored" for _ in range(23)) for cpu in range(240)))
            (proc / "meminfo").write_text("MemFree: 4000000 kB\n")
            for pid in range(100, 400):
                thread = proc / str(pid)
                thread.mkdir()
                (thread / "status").write_text("PPid: 2\n")
            program = directory / "driver"
            program.write_bytes(b"driver")
            extra = directory / "claude-batch.mic"
            extra.write_bytes(bytes(range(256)))
            extra.chmod(0o700)
            data = directory / "input ' data"
            data.write_bytes(b"\x00\xffdata\n")
            data.chmod(0o600)
            self.session.pin_helper = program
            self.session.command = ["fake-ssh", "exec sh"]
            run_dir = directory / self.session.run_dir.lstrip("/")

            def translate(script):
                return script.replace("/tmp", str(directory / "tmp")).replace(
                    "/proc/", str(proc) + "/")

            def rpc(script, timeout, **kwargs):
                setup = self.remote + '\nrun_dir=%s\nboot_id=%s\n' % (
                    shlex.quote(self.session.run_dir), shlex.quote(self.session.boot_id))
                answer = subprocess.run([shutil.which("sh"), "-c", translate(setup + script)],
                                        capture_output=True, timeout=timeout)
                self.assertEqual(answer.returncode, 0, answer.stderr)
                return answer.stdout.rstrip(b"\n")

            self.session.rpc = rpc
            actual_popen = subprocess.Popen

            def popen(command, **kwargs):
                if command[0] == "fake-ssh":
                    command = [shutil.which("sh"), "-c", translate(shlex.split(command[-1])[-1])]
                return actual_popen(command, **kwargs)

            with mock.patch.object(self.runner["subprocess"], "Popen", side_effect=popen):
                self.session.snapshot(timeout=5)
                self.session.stage(self.session.run_dir, program, files=[extra, data], timeout=10)
            for source, mode in ((extra, 0o700), (data, 0o600)):
                staged = run_dir / source.name
                self.assertEqual(staged.read_bytes(), source.read_bytes())
                self.assertEqual(staged.stat().st_mode & 0o777, mode)
            self.session.cleanup(self.session.run_dir, self.session.boot_id, timeout=5)
            self.assertFalse(run_dir.exists())
            with mock.patch.object(self.runner["subprocess"], "Popen") as spawn:
                for unsafe in ("sub/file", "../escape", "..", "claude-../escape"):
                    with self.subTest(name=unsafe), self.assertRaises(OSError):
                        self.session.send_file(unsafe, b"", 1)
                spawn.assert_not_called()

    def test_output_binary_roundtrip_rejects_busybox_head_c_and_od_A(self):
        directory = Path(self.session.run_dir)
        directory.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, directory)
        data = bytes(range(256)) * 513 + b"\x00\xff\n"
        errors = b"stderr\x00\xff\n\n"
        (directory / "expected.stdout").write_bytes(data)
        (directory / "expected.stderr").write_bytes(errors)
        boot_file = directory / "boot_id"
        boot_file.write_text(self.session.boot_id + "\n")
        # Real local shell transport, with the two native-reported unsupported
        # options rejected. Raw download SSH commands use this same fake card.
        busybox = '''
head() { [ "$1" != -c ] || { echo 'head: invalid option -- c' >&2; return 94; }; command head "$@"; }
od() { case "$*" in *-A*) echo 'od: invalid option -- A' >&2; return 94;; esac; command od "$@"; }
'''
        setup = (self.remote + busybox + '\nrun_dir=%s\nboot_id=%s\ncd -- "$run_dir"\n' %
                 (shlex.quote(self.session.run_dir), shlex.quote(self.session.boot_id)))
        setup += ('start_job() { cp expected.stdout stdout; cp expected.stderr stderr; '
                  ': > claude-pinned; echo 0 > status; };\n')

        def rpc(script, timeout, **kwargs):
            answer = subprocess.run([shutil.which("sh"), "-c", (setup + script).replace(
                "/proc/sys/kernel/random/boot_id", str(boot_file))],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            if answer.returncode:
                raise OSError(answer.stderr.decode("utf8", "replace"))
            return answer.stdout.rstrip(b"\n")

        self.session.rpc = rpc
        self.session.command = ["fake-ssh", "exec sh"]
        actual_popen = subprocess.Popen
        downloads = []

        def popen(command, **kwargs):
            if command[0] != "fake-ssh":
                return actual_popen(command, **kwargs)
            script = shlex.split(command[-1])[-1]
            downloads.append(script)
            script = script.replace("/proc/sys/kernel/random/boot_id", str(boot_file))
            return actual_popen([shutil.which("sh"), "-c", busybox + script], **kwargs)

        stdout, stderr = io.BytesIO(), io.BytesIO()
        status, failure = None, None
        with mock.patch.object(self.runner["subprocess"], "Popen", side_effect=popen), \
                mock.patch("sys.stdout", mock.Mock(buffer=stdout)), \
                mock.patch("sys.stderr", mock.Mock(buffer=stderr)):
            try:
                status = self.session.execute(self.session.run_dir, [], timeout=10, card_timeout=15,
                                              cpus=[4, 13, 91], memory_mb=128)
            except OSError as error:
                failure = str(error)
        self.assertEqual(status, 0, failure)
        self.assertEqual(stdout.getvalue(), data)
        self.assertEqual(stderr.getvalue(), errors)
        self.assertTrue(downloads, "output must use a separate binary SSH stream")
        for script in downloads:
            self.assertIn("guard_boot", script)
            self.assertNotIn("head -c", script)
            self.assertNotIn("od -A", script)

    def test_helper_launch_replaces_taskset_and_unmounted_cgroups(self):
        self.assertIn('./claude-pin "$job_cpus" "$job_memory"', self.remote)

    def test_sixty_second_job_uses_at_most_fifteen_output_connections(self):
        self.session.command = ["fake-ssh", "exec sh"]
        now = 0.0
        payloads = {"stdout": b"hello\x00\xff\n", "stderr": b"diagnostic\n"}

        def sleep(seconds):
            nonlocal now
            now += seconds

        def rpc(script, timeout, *, step):
            if step == "start-job":
                return b""
            self.assertEqual(step, "read-status")
            return b"0" if now >= 60 else b"running"

        def popen(command, **kwargs):
            self.assertEqual(command[0], "fake-ssh")
            script = shlex.split(command[-1])[-1]
            name = "stdout" if "dd if=stdout " in script else "stderr"
            data = payloads[name] if now >= 60 else b""
            child = mock.Mock(returncode=0)
            child.communicate.return_value = (data, b"")
            return child

        self.session.rpc = rpc
        stdout, stderr = io.BytesIO(), io.BytesIO()
        with mock.patch.object(self.runner["time"], "monotonic", side_effect=lambda: now), \
                mock.patch.object(self.runner["time"], "sleep", side_effect=sleep), \
                mock.patch.object(self.runner["subprocess"], "Popen", side_effect=popen) as spawn, \
                mock.patch("sys.stdout", mock.Mock(buffer=stdout)), \
                mock.patch("sys.stderr", mock.Mock(buffer=stderr)):
            status = self.session.execute(self.session.run_dir, [], timeout=70, card_timeout=75,
                                          cpus=[4, 13, 91], memory_mb=128)
        self.assertLessEqual(spawn.call_count, 15)
        self.assertEqual(status, 0)
        self.assertEqual(stdout.getvalue(), payloads["stdout"])
        self.assertEqual(stderr.getvalue(), payloads["stderr"])
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
            tested = subprocess.run([str(executable)], cwd=name,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertEqual(tested.returncode, 0, tested.stdout.decode(errors="replace"))

    def test_missing_helper_marker_is_infrastructure_and_finish_records_it(self):
        # Run the real execution protocol against local fake remote files. No
        # executable is launched: start_job supplies the helper/program status.
        with tempfile.TemporaryDirectory(dir=ROOT) as name:
            directory = Path(name)
            ledger = directory / "jobs.jsonl"
            ledger.write_text("", encoding="utf8")
            for marker, status in ((False, 125), (False, 126), (False, 127),
                                   (True, 125), (True, 126), (True, 127)):
                with self.subTest(marker=marker, status=status):
                    fixture = directory / ("marked" if marker else "unmarked")
                    fixture.mkdir(exist_ok=True)
                    session = self.session
                    session.boot_id = BOOT
                    setup = ('guard_boot() { :; }; guard_dir() { :; }; '
                             'start_job() { : > stdout; : > stderr; '
                             'printf "%s\\n" > status; %s; };\n' %
                             (status, ': > claude-pinned' if marker else ':'))

                    def rpc(script, timeout, **kwargs):
                        answer = subprocess.run([shutil.which("sh"), "-c", setup + script],
                                                cwd=fixture, stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE, timeout=timeout)
                        if answer.returncode:
                            raise OSError(answer.stderr.decode("utf8", "replace"))
                        return answer.stdout.rstrip(b"\n")

                    session.rpc = rpc
                    session.read_output = lambda name, offset, timeout: (
                        fixture / name).read_bytes()[offset:offset + 65536]
                    transport = SharedTransport()
                    transport.ledger = ledger

                    def execute(run_dir, argv, **kwargs):
                        session.run_dir = run_dir
                        return session.execute(run_dir, argv, **kwargs)

                    transport.execute = execute
                    result = self.runner["run"](
                        fixture / "unused.mic", [], lock_path=directory / "card.lock",
                        external_locks=[], baseline_names=set(), timeout=5,
                        transport_timeout=1, receipt_path=directory / "result.json",
                        transport=transport, ledger_path=ledger)
                    finish = transport.read_ledger()[-1]
                    if marker:
                        self.assertEqual(result["result_class"], "program", result)
                        self.assertEqual(result["program_exit_code"], status)
                        self.assertEqual(finish["outcome"], "program-failure")
                    else:
                        self.assertEqual(result["result_class"], "infrastructure", result)
                        self.assertIsNone(result["program_exit_code"])
                        self.assertIn("claude-pinned", result["detail"])
                        self.assertEqual(finish["outcome"], "infrastructure-failure")
                    self.assertEqual(finish["event"], "finish")

    def test_snapshot_excludes_control_pid_and_children_by_identity(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as name:
            proc = Path(name) / "proc"
            (proc / "sys/kernel/random").mkdir(parents=True)
            (proc / "sys/kernel/random/boot_id").write_text(BOOT + "\n")
            (proc / "cpuinfo").write_text("processor : 91\ncore id : 30\n")
            (proc / "meminfo").write_text("MemFree: 4000000 kB\n")
            script = self.remote.replace("/proc/", str(proc) + "/")
            script += '''
readlink() { cat "$1"; }
fixture_proc=$1
run_dir=/tmp/claude/claude-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
for fixture_pid in "$$" 98765 42; do
    mkdir "$fixture_proc/$fixture_pid"
    printf '/bin/sh\\n' > "$fixture_proc/$fixture_pid/exe"
    printf '/outside\\n' > "$fixture_proc/$fixture_pid/cwd"
    printf 'claude-control\\n' > "$fixture_proc/$fixture_pid/comm"
    fixture_ppid=1
    [ "$fixture_pid" != 98765 ] || fixture_ppid=$$
    printf 'PPid:\\t%s\\n' "$fixture_ppid" > "$fixture_proc/$fixture_pid/status"
done
snapshot
'''
            answer = subprocess.run([shutil.which("sh"), "-c", script, "claude-test", str(proc)],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(answer.returncode, 0, answer.stderr)
            self.session.rpc = mock.Mock(return_value=answer.stdout.rstrip(b"\n"))
            snapshot = self.session.snapshot(timeout=1)
            # A foreign process with our control name must still be reported.
            self.assertEqual([p["pid"] for p in snapshot["processes"]], ["42"])

    def test_snapshot_does_not_claim_untested_pinning(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as name:
            proc = Path(name) / "proc"
            (proc / "sys/kernel/random").mkdir(parents=True)
            (proc / "sys/kernel/random/boot_id").write_text(BOOT + "\n")
            (proc / "cpuinfo").write_text("processor : 91\ncore id : 30\n")
            (proc / "meminfo").write_text("MemFree: 4000000 kB\n")
            script = self.remote.replace("/proc/", str(proc) + "/")
            script += "\nrun_dir=/tmp/claude/claude-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
            answer = subprocess.run([shutil.which("sh"), "-c", script + "\nsnapshot\n"],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(answer.returncode, 0, answer.stderr)
            self.assertNotIn(b"PIN\tyes\n", answer.stdout,
                             "affinity is established by the staged helper, not snapshot")

    def test_cleanup_removes_parent_only_when_empty(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as name:
            parent = Path(name) / "claude"
            for sibling in (False, True):
                with self.subTest(sibling=sibling):
                    job = parent / ("claude-" + "a" * 32)
                    job.mkdir(parents=True, exist_ok=True)
                    other = parent / "claude-other-job"
                    if sibling:
                        other.mkdir()
                        (other / "output").write_text("keep")
                    script = self.remote.replace("/tmp/claude", str(parent))
                    script += ('\ncheck_boot() { :; }; stop_owned() { :; }; '
                               'guard_boot() { :; }; run_dir=$1; cleanup\n')
                    answer = subprocess.run([shutil.which("sh"), "-c", script,
                                             "claude-test", str(job)],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    self.assertEqual(answer.returncode, 0, answer.stderr)
                    self.assertFalse(job.exists())
                    if sibling:
                        self.assertEqual((other / "output").read_text(), "keep")
                    else:
                        self.assertFalse(parent.exists(), "empty staging parent remains in RAM")


if __name__ == "__main__":
    unittest.main()
