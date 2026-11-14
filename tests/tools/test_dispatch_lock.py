"""S12-28: isolated host dispatchers with a fake session command."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
import os, subprocess, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import dispatch
root, lane, marker, release, interrupt = sys.argv[2:]
class Board:
    policy = {}
    def __init__(self): self.root = root
    def state_dir(self):
        path = dispatch.storage.state_dir(root)
        os.makedirs(path, exist_ok=True)
        return path
    def tickets(self): return []
dispatch.pm.Board = Board
dispatch.pm.next_action = lambda board, lane: ('engineer', object())
dispatch.pm.cmd_board = lambda *args: None
dispatch.storage.check = lambda *args: ('ok', '')
def session(*args):
    subprocess.run([sys.executable, '-c',
        'from pathlib import Path; import sys,time; '
        'Path(sys.argv[1]).touch(); '
        'exec("while not Path(sys.argv[2]).exists(): time.sleep(0.02)")',
        marker, release], check=True)
    if interrupt == 'yes': raise KeyboardInterrupt
    return True
dispatch.run_session = session
sys.exit(dispatch.main(['--lane', lane, '--max-sessions', '1']))
'''


class DispatcherLock(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.processes = []
        self.addCleanup(self.stop_processes)

    def stop_processes(self):
        for process, marker, release in self.processes:
            release.touch()
        for process, marker, release in self.processes:
            try:
                process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()

    def start(self, lane, interrupt=False):
        index = len(self.processes)
        marker = self.root / ('ready%d' % index)
        release = self.root / ('release%d' % index)
        process = subprocess.Popen(
            [sys.executable, '-c', DRIVER, str(ROOT / 'tools'), str(self.root),
             lane, str(marker), str(release), 'yes' if interrupt else 'no'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.processes.append((process, marker, release))
        return process, marker, release

    def ready(self, process, marker):
        deadline = time.monotonic() + 10
        while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(marker.exists(), 'dispatcher did not start fake session')

    def finish(self, process, release):
        release.touch()
        output, _ = process.communicate(timeout=10)
        return process.returncode, output

    def test_same_lane_refuses_with_holder_pid(self):
        first, marker, release = self.start('corpus2')
        self.ready(first, marker)
        second, second_marker, second_release = self.start('corpus2')
        try:
            output, _ = second.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            self.fail('second dispatcher started a session on the occupied lane')
        self.assertNotEqual(second.returncode, 0, output)
        self.assertIn(str(first.pid), output)
        self.assertFalse(second_marker.exists())
        locks = list((self.root / '.work' / '_state').glob('dispatch*.lock'))
        self.assertEqual(len(locks), 1)
        record = locks[0].read_text()
        self.assertIn(str(first.pid), record)
        self.assertGreater(len(record.splitlines()), 1, 'lock must record start time')
        self.assertEqual(self.finish(first, release)[0], 0)
        self.assertFalse(locks[0].exists(), 'normal exit must release lock')

    def test_different_lanes_run_together(self):
        for lane in ('corpus2', 'tools'):
            process, marker, release = self.start(lane)
            self.ready(process, marker)
        for process, marker, release in self.processes:
            self.assertIsNone(process.poll())
            self.assertEqual(self.finish(process, release)[0], 0)

    def test_dead_holder_takeover_and_keyboard_interrupt_release(self):
        first, marker, release = self.start('corpus2')
        self.ready(first, marker)
        locks = list((self.root / '.work' / '_state').glob('dispatch*.lock'))
        self.assertEqual(len(locks), 1)
        first.kill()
        first.communicate(timeout=10)
        release.touch()
        second, marker, release = self.start('corpus2', interrupt=True)
        self.ready(second, marker)
        self.assertIn(str(second.pid), locks[0].read_text())
        self.assertNotEqual(self.finish(second, release)[0], 0)
        self.assertFalse(locks[0].exists(), 'Ctrl-C must release lock')


if __name__ == '__main__':
    unittest.main()
