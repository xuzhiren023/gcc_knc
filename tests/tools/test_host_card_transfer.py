"""S11-01 acceptance: host loopback, real corruption rejection, FIPS abc vector."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import host_card_transfer as transfer


class TransferIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        transfer.build(host_only=True)

    def test_loopback_and_integrity(self):
        exe = str(transfer.OUT / 'transfer-host.exe')
        known = subprocess.run([exe, 'selftest'], env=transfer.ENV, capture_output=True, text=True)
        self.assertEqual(known.returncode, 0, known.stderr)
        self.assertIn('abc: match', known.stdout)
        for method in ('pipe', 'tcp', 'fake-write', 'fake-read', 'fake-vwrite', 'fake-mmap'):
            for direction in ('up', 'down'):
                with self.subTest(method=method, direction=direction):
                    rows = transfer.loopback(method, direction, 1048705)
                    self.assertEqual(len(rows), 2)
                    for row in rows:
                        self.assertEqual(row['integrity'], 'match')
                        self.assertEqual(len(row['sha256']), 64)
                        self.assertEqual(row['bytes'], 1048705)
                        self.assertGreater(row['seconds'], 0)
                        self.assertGreaterEqual(row['host_cpu_seconds'], 0)
                        self.assertGreaterEqual(row['card_cpu_seconds'], 0)
        with self.assertRaisesRegex(RuntimeError, 'mismatch'):
            transfer.loopback('tcp', 'up', 4096, corrupt=True)

    def test_lease_directory_shapes(self):
        valid = ('/tmp/claude/claude-' + 'a' * 32,
                 '/var/volatile/tmp/claude/claude-' + '0f' * 16)
        invalid = ('/tmp/claude/claude-' + 'a' * 31,
                   '/tmp/claude/claude-' + 'A' * 32,
                   '/tmp/other/claude-' + 'a' * 32,
                   '/tmp/claude/claude-' + 'a' * 32 + '"',
                   '/var/volatile/other/claude/claude-' + 'a' * 32)
        for directory in valid:
            with self.subTest(directory=directory):
                self.assertTrue(transfer.LEASE_DIRECTORY.fullmatch(directory))
        for directory in invalid:
            with self.subTest(directory=directory):
                self.assertIsNone(transfer.LEASE_DIRECTORY.fullmatch(directory))


if __name__ == '__main__':
    unittest.main()
