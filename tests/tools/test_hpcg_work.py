"""S11-28: recorded HPCG report fields and unequal-work rejection, host only."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import corpus

# Relevant fields recorded in S11-18/capture/026.stdout, HPCG 3.1.
REPORT = '''Spectral Convergence Tests::Result=PASSED
Departure from Symmetry |x'Ay-y'Ax|/(2*||x||*||A||*||y||)/epsilon::Result=PASSED
Iteration Count Information::Result=PASSED
Iteration Count Information::Reference CG iterations per set=50
Iteration Count Information::Optimized CG iterations per set=51
Iteration Count Information::Total number of reference iterations=50
Iteration Count Information::Total number of optimized iterations=51
Reproducibility Information::Result=PASSED
Final Summary::HPCG result is VALID with a GFLOP/s rating of=0.0860859
'''


class Work(unittest.TestCase):
    def test_recorded_report_and_controls(self):
        work = corpus.hpcg_work(REPORT)
        self.assertEqual(work, dict(sets=1, reference_per_set=50,
                                   optimized_per_set=51, reference_total=50,
                                   optimized_total=51))
        for old, new in [('Total number of optimized iterations=51', 'Total number of optimized iterations=52'),
                         ('Result=PASSED', 'Result=FAILED')]:
            with self.subTest(new=new), self.assertRaises(ValueError):
                corpus.hpcg_work(REPORT.replace(old, new))

    def test_collection_rejects_unequal_work(self):
        for report, expected in [(REPORT, 'pass'),
                (REPORT.replace('reference iterations=50', 'reference iterations=100')
                       .replace('optimized iterations=51', 'optimized iterations=102'), 'fail'),
                (REPORT.replace('Optimized CG iterations per set=51', 'Optimized CG iterations per set=52')
                       .replace('optimized iterations=51', 'optimized iterations=52'), 'fail')]:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                rows = []
                for compiler, text in [(corpus.DONOR, REPORT), (corpus.KNC, report)]:
                    rows.append(dict(program='HPCG', compiler=compiler, flags=['-O2'], run=0,
                        threads=1, input='fixture', profile='3100', variant='serial',
                        check='pass', time_seconds=1., hpcg_work=corpus.hpcg_work(text)))
                (root / 'plan.json').write_text(json.dumps(rows))
                (root / 'raw-results.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
                with redirect_stdout(io.StringIO()):
                    corpus.collect(SimpleNamespace(stage=root))
                results = [json.loads(s) for s in (root / 'results.jsonl').read_text().splitlines()]
                self.assertEqual(results[1]['check'], expected)


if __name__ == '__main__':
    unittest.main()
