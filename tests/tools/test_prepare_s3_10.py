"""S4-08: S3-10 ABI expected files use the card's %La spelling for long double."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import prepare_s3_10

CARD = ROOT.parent / '_shared/tmp/claude-s3-10-m1/claude-abi-O0-0.mic.actual.txt'
# What the host libc printed for knc-abi-gaps (the old expected file).
HOST = (
    'S3-15 complex ABI PASS: float=(1.75,-3.75) double=(-2.25,3.75) '
    'long-double=(0x1.c00000000000001p+0,-0x1.e000000000000008p+1)\n'
    'S3-15 rounding nearest PASS: p=0x1p+0 n=-0x1p+0\n')


class CardSpellingTest(unittest.TestCase):
    def test_expected_matches_card_output(self):
        card = ''.join(CARD.read_text().splitlines(True)[:-1])  # drop the job-record line
        expected = prepare_s3_10.card_spelling(HOST)
        self.assertEqual(expected.splitlines()[0], card.splitlines()[0])

    def test_trailing_zero_and_other_values(self):
        f = prepare_s3_10.card_spelling
        self.assertEqual(f('long-double=(0x1.8p+1,-0x1p+0)'), 'long-double=(0xc p-2,-0x8p-3)'.replace(' ', ''))
        self.assertEqual(f('double=(0x1.8p+1,0x1p+0)'), 'double=(0x1.8p+1,0x1p+0)')


if __name__ == '__main__':
    unittest.main()
