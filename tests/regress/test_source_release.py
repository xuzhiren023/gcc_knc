"""S13-04: source-release host portability; no SSH process or card job.

Exercise the real transport setup with only the SSH session replaced. A POSIX
host is simulated on Windows, so this is not a native Linux validation.
"""
import os
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]


class SourceRelease(unittest.TestCase):
    """CLI contract for tools/source_release.py, using disposable repositories.

    audit --repo REPO --ref REF --json emits {"excluded": [{"path": ...,
    "reason": ...}]} and fails if a tracked path is unsuitable for release.
    export adds --base TAG --output DIR and writes source.bundle plus
    patches/0001-knc-squashed.patch. Published history is retained and reported;
    only the tip must be clean (lead decision 2026-11-17).
    """

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.repo = self.directory / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Source release fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "commit.gpgsign", "false")
        self.git("checkout", "-q", "-b", "main")
        self.write(".gitignore", "ignored/\n.work/\n*.o\n*.exe\n")
        self.write("src/example.c", "int example(void) { return 0; }\n")
        self.commit("fixture upstream")
        self.base = "releases/gcc-16.2.0"
        self.git("tag", self.base)
        self.write("src/example.c", "int example(void) { return 1; }\n")
        self.commit("fixture source change")
        self.write("src/extra.c", "int extra(void) { return 2; }\n")
        self.commit("fixture additional source")

    def git(self, *args, cwd=None):
        result = subprocess.run(["git", *map(str, args)], cwd=cwd or self.repo,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def write(self, name, contents):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf8")

    def commit(self, message):
        self.git("add", "-f", ".")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-qm", message)

    def release(self, action, *args):
        tool = ROOT / "tools/source_release.py"
        self.assertTrue(tool.is_file(), "missing source export/audit CLI: " + str(tool))
        return subprocess.run([sys.executable, str(tool), action,
                               "--repo", str(self.repo), "--ref", "main", *args],
                              text=True, capture_output=True)

    def test_audit_rejects_each_tracked_exclusion_with_reason(self):
        forbidden = {
            "ignored/forced.txt": ("ignored fixture\n", r"ignor"),
            ".work/card-output.txt": ("workspace fixture\n", r"work|workspace"),
            "obj/example.o": ("object fixture\n", r"artifact|object|binary"),
            "large.txt": ("x" * (1024 * 1024 + 1), r"size|large|limit|1.?m"),
            "vendor/intel-manual.pdf": ("synthetic document fixture\n", r"vendor|document|pdf"),
            "vendor/intrinsics-guide.xml": ("<synthetic-fixture/>\n", r"vendor|intrinsics|xml"),
        }
        for path, (contents, _) in forbidden.items():
            self.write(path, contents)
        self.commit("fixture forbidden tracked files")
        result = self.release("audit", "--json")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        reasons = {}
        for entry in report["excluded"]:
            reasons.setdefault(entry["path"], []).append(entry["reason"])
        for path, (_, reason) in forbidden.items():
            with self.subTest(path=path):
                self.assertIn(path, reasons)
                self.assertRegex(" ".join(reasons[path]).lower(), reason)

    def test_clean_tracked_tree_passes_audit(self):
        self.write("src/handwritten.S", ".text\n")
        self.write(".gitignore", "ignored/\n.work/\n*.o\n*.exe\n*.s\n")
        self.commit("fixture case-sensitive source assembly")
        result = self.release("audit", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["excluded"], [])

    def test_exports_clean_tip_with_history_and_squashed_merge_diff(self):
        expected = {".gitignore", "src/example.c", "src/extra.c"}
        self.write("old.o", "historical synthetic artifact\n")
        self.commit("fixture historical artifact")
        (self.repo / "old.o").unlink()
        self.commit("fixture remove historical artifact")
        self.git("checkout", "-qb", "side", self.base)
        self.write("src/side.c", "int side(void) { return 3; }\n")
        self.commit("fixture side")
        self.git("checkout", "-q", "main")
        self.git("merge", "--no-ff", "-qm", "fixture merge", "side")
        expected.add("src/side.c")
        # These exist on disk but must never enter either export.
        for path in ("ignored/local.txt", ".work/card-output.txt", "obj/local.o",
                     "tool.exe", "vendor/intel-manual.pdf", "untracked.txt"):
            self.write(path, "synthetic local fixture\n")
        self.write("large.txt", "x" * (1024 * 1024 + 1))
        output = self.directory / "export"
        result = self.release("export", "--base", self.base, "--output", str(output))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        bundle = output / "source.bundle"
        self.git("bundle", "verify", bundle)
        clone = self.directory / "clone"
        self.git("clone", "-q", "--branch", "main", bundle, clone)
        # A source bundle must preserve history and the upstream tag.
        self.assertEqual(self.git("rev-parse", "main", cwd=clone),
                         self.git("rev-parse", "main"))
        self.assertEqual(self.git("rev-parse", self.base, cwd=clone),
                         self.git("rev-parse", self.base))
        for revision in self.git("rev-list", "main", cwd=clone).splitlines():
            paths = set(self.git("ls-tree", "-r", "--name-only", revision,
                                 cwd=clone).splitlines())
            self.assertTrue(paths <= expected | {"old.o"}, paths - expected)
        self.assertEqual(set(self.git("ls-tree", "-r", "--name-only", "main",
                                      cwd=clone).splitlines()), expected)
        patches = sorted((output / "patches").glob("*.patch"))
        self.assertEqual(len(patches), 1)
        readme = (output / "README.txt").read_text()
        self.assertIn("old.o: build artifact", readme)
        self.assertIn(self.git("rev-parse", "main").strip(), readme)
        self.git("checkout", "-q", self.base, cwd=clone)
        for number, patch in enumerate(patches, 1):
            self.assertRegex(patch.name, rf"^{number:04d}-.+\.patch$")
            self.git("apply", "--check", "--index", patch, cwd=clone)
            self.git("apply", "--index", patch, cwd=clone)
            paths = set(self.git("ls-files", cwd=clone).splitlines())
            self.assertTrue(paths <= expected, paths - expected)
        self.assertEqual(set(self.git("ls-files", cwd=clone).splitlines()), expected)
        self.git("diff", "--exit-code", "main", "--", cwd=clone)


class LinuxCardTransport(unittest.TestCase):
    def setUp(self):
        self.runner = runpy.run_path(str(ROOT / "tools/card_run"))
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.pin = self.directory / "claude-pin.mic"
        self.pin.write_bytes(b"fixture; never executed")
        self.config = dict(host="card.invalid", identity="/home/owner/.ssh/card",
                           knownHosts="/home/owner/.ssh/known_hosts",
                           pinHelper=str(self.pin))

    def connect(self, platform, **config):
        transport_type = self.runner["SSHTransport"]
        # Replace only this script's os binding, not pathlib's host platform.
        host_os = SimpleNamespace(**vars(os))
        host_os.name = platform
        host_os.devnull = "/dev/null" if platform == "posix" else "nul"
        session_factory = mock.Mock()
        with mock.patch.dict(transport_type.connect.__globals__,
                             os=host_os, SSHSession=session_factory):
            transport = transport_type(dict(self.config, **config), 5, transfer="ssh")
            session = transport.connect("/tmp/claude/claude-" + "a" * 32, timeout=5)
        command = session_factory.call_args.args[0]
        return command, session

    def test_posix_ssh_uses_native_executable_and_null_device(self):
        command, _ = self.connect("posix")
        self.assertEqual(Path(command[0]).name, "ssh", command)
        self.assertNotIn("C:", command[0])
        self.assertEqual(command[command.index("-F") + 1], "/dev/null")
        self.assertIn("GlobalKnownHostsFile=/dev/null", command)
        for option in ("IdentitiesOnly=yes", "BatchMode=yes",
                       "StrictHostKeyChecking=yes",
                       "UserKnownHostsFile=" + self.config["knownHosts"]):
            self.assertIn(option, command)
        self.assertEqual(command[command.index("-i") + 1], self.config["identity"])
        self.assertEqual(command[-2:], ["root@card.invalid", "exec sh"])

    def test_posix_host_transfer_helper_has_native_name(self):
        _, session = self.connect("posix")
        self.assertEqual(session.host_helper.name, "claude-transfer")
        self.assertTrue(session.helper_free)

    def test_explicit_posix_transfer_helper_is_preserved(self):
        helper = str(self.directory / "custom-transfer")
        _, session = self.connect("posix", transferHost=helper)
        self.assertEqual(session.host_helper, Path(helper))

    def test_windows_transport_still_uses_windows_openssh(self):
        command, session = self.connect("nt")
        self.assertEqual(command[0], "C:/Windows/System32/OpenSSH/ssh.exe")
        self.assertEqual(command[command.index("-F") + 1].lower(), "nul")
        self.assertIn("globalknownhostsfile=nul", [part.lower() for part in command])
        self.assertEqual(session.host_helper.name, "claude-transfer.exe")


class LinuxHostTools(unittest.TestCase):
    def test_native_check_tools_and_x86_configuration(self):
        sys.path.insert(0, str(ROOT / "tools"))
        self.addCleanup(sys.path.pop, 0)
        host_os = SimpleNamespace(**vars(os))
        host_os.name = "posix"
        with mock.patch("sys.platform", "linux"):
            runner = runpy.run_path(str(ROOT / "tools/check.py"))["Runner"]
            with mock.patch.dict(runner.tool.__globals__, os=host_os):
                instance = object.__new__(runner)
                instance.tc = Path("toolchain")
                self.assertEqual(instance.tool("as").as_posix(),
                                 "toolchain/cross/bin/k1om-mpss-linux-as")
            # runpy uses the real os; patch only the module binding at import.
            with mock.patch.dict(sys.modules, os=host_os):
                portability = runpy.run_path(str(ROOT / "tools/portability.py"))
        self.assertEqual(portability["EXE_SUFFIX"], "")
        self.assertFalse(any("cygwin" in flag for flag in portability["CONFIGURE_ARGS"]))
        with mock.patch("subprocess.check_output", return_value="python3\nmake\n") as ps:
            self.assertTrue(portability["make_is_running"]())
        ps.assert_called_once_with(["ps", "-eo", "comm="], text=True,
                                   stderr=subprocess.STDOUT)
        with mock.patch("subprocess.check_output", return_value="python3\n"):
            self.assertFalse(portability["make_is_running"]())


if __name__ == "__main__":
    unittest.main()
