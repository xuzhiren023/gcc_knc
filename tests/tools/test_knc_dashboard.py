import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import knc_dashboard as d


class DashboardTests(unittest.TestCase):
    def test_ledger(self):
        now = dt.datetime(2026, 11, 16, 12, tzinfo=dt.timezone.utc)
        def row(event, job, **kw):
            return dict(event=event, jobId=job, timingValid=True,
                        queuedTime='2026-11-16T11:50:00Z', **kw)
        rows = [row('start', 'old', startTime='2026-11-16T10:00:00Z', purpose='p'),
                row('finish', 'old', endTime='2026-11-16T10:02:00Z'),
                row('start', 'run', expectedEnd='2026-11-16T11:59:00Z'),
                row('queued', 'known', purpose='p'), row('queued', 'unknown'),
                row('queued', 'cancel'), row('owner-cancel-request', 'cancel'),
                row('queued', 'sup'), row('superseded', 'sup'),
                row('queued', 'stale', firstQueuedTime='2026-11-16T08:00:00Z')]
        rows[-1]['queuedTime'] = '2026-11-16T08:00:00Z'
        rows += [row('queued', 'claude-turn-x', cores=[]),
                 row('queued', 'claude-turn-x', cores=[], firstQueuedTime='2026-11-16T11:00:00Z'),
                 row('queued', 'later')]
        result = d.ledger_status('\n'.join(map(json.dumps, rows)) + '\ninvalid', now)
        self.assertEqual(result['running'][0]['remaining_seconds'], -60)
        self.assertEqual([r['jobId'] for r in result['queue']], ['known', 'unknown', 'later'])
        self.assertEqual(result['turns'][0]['jobId'], 'claude-turn-x')
        self.assertEqual(result['order'][0], 'claude-turn-x')
        self.assertEqual(result['queue'][0]['duration_seconds'], 120)
        self.assertEqual(result['queue'][0]['basis'], 'purpose')
        self.assertEqual(result['queue'][0]['estimated_start'], '2026-11-16T12:00:00+00:00')
        self.assertIsNone(result['queue'][1]['duration_seconds'])
        self.assertEqual(result['queue'][1]['estimated_start'], '2026-11-16T12:02:00+00:00')
        self.assertIsNone(result['queue'][2]['estimated_start'])
        rows[2]['expectedEnd'] = '2026-11-16T12:10:00Z'
        rows[0].update(project='x', agent='a')
        rows[3].update(purpose='other', project='x', agent='a')
        result = d.ledger_status('\n'.join(map(json.dumps, rows)), now)
        self.assertEqual(result['running'][0]['remaining_seconds'], 600)
        self.assertEqual(result['queue'][0]['basis'], 'project and agent')
        self.assertEqual(result['queue'][0]['estimated_start'], '2026-11-16T12:10:00+00:00')

    def test_sensors(self):
        text = '''mic0 (temp):
   Cpu Temp: ...... 72.00 C
   Memory Temp: ... 60.00 C
mic0 (cores):
   Device Utilization: User: 45.03%, System: 3.74%, Idle: 51.23%
      Core #1: User: 40.00%, System: 5.00%, Idle: 55.00%
mic1 (temp):
   Cpu Temp: ...... 70.00 C'''
        devices = d.parse_micsmc(text)
        self.assertEqual(devices['mic0']['temperatures']['Cpu Temp'], 72)
        self.assertEqual(devices['mic0']['cores']['1']['idle'], 55)
        self.assertIn('mic1', devices)
        with self.assertRaises(ValueError):
            d.parse_micsmc('ERROR: device unavailable')
        self.assertEqual(d.parse_host_cpu('[20,40]'), 30)

    def test_history_and_page(self):
        history = {'active': {'1': {'subcommand': 'predict', 'start_epoch': 0}},
                   'durations': {'predict': [10, 30]}}
        updated, runs = d.update_history(history, [], 20)
        self.assertEqual(updated['durations']['predict'], [10, 30, 20])
        updated, runs = d.update_history(updated, [dict(key='2', subcommand='predict', start_epoch=15)], 25)
        self.assertEqual(runs[0]['remaining_seconds'], 10)
        server = d.ThreadingHTTPServer(('127.0.0.1', 0), d.handler(None))
        worker = threading.Thread(target=server.serve_forever)
        worker.start()
        try:
            with urlopen('http://127.0.0.1:%d/' % server.server_port) as response:
                page = response.read().decode('utf-8')
            for name in ('Card job', 'Card queue', 'Twin work', 'Card sensors', 'Host CPU'):
                self.assertIn(name, page)
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

    def test_twin_ticket_sessions(self):
        now = dt.datetime(2026, 11, 16, 12).astimezone(dt.timezone.utc)
        with tempfile.TemporaryDirectory() as root:
            logs = Path(root) / '.work/_state/logs'
            logs.mkdir(parents=True)
            ticket = SimpleNamespace(id='S14-01', state='doing',
                                     fields={'lane': 'twin-model', 'title': 'Twin work'})
            board = SimpleNamespace(root=root, policy={'session_timeout_minutes': 30},
                                    tickets=lambda: [ticket])
            def check(start, remaining, status):
                row = d.twin_tickets(board, now)[0]
                self.assertEqual(row['session_start'], start)
                self.assertEqual(row['remaining_seconds'], remaining)
                self.assertEqual(row['session_status'], status)
            check(None, None, 'no live session')
            old = logs / 'S14-01-engineer-2026-11-16T110000.jsonl'
            latest = logs / 'S14-01-lead-2026-11-16T115000.jsonl'
            for path in (old, latest):
                path.write_text('fixture', encoding='utf-8')
                os.utime(str(path), (now.timestamp(), now.timestamp()))
            start = dt.datetime(2026, 11, 16, 11, 50).astimezone(dt.timezone.utc).isoformat()
            check(start, 1200, 'live')
            # A newer session name wins even if an older log was modified later.
            stale = now.timestamp() - 31 * 60
            os.utime(str(latest), (stale, stale))
            check(None, None, 'no live session')


if __name__ == '__main__':
    unittest.main()
