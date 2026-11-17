"""S13-04: source-release host portability; no SSH process or card job.

Exercise the real transport setup with only the SSH session replaced. A POSIX
host is simulated on Windows, so this is not a native Linux validation.
"""
import os
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]


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


if __name__ == "__main__":
    unittest.main()
