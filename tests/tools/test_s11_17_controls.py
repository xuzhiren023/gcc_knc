"""T1 positive-control transformations; --variant base is deliberately red.

Run after tools/s11_17_controls.py stage/use. This reads actual KNC assembly;
absent assembly is an error, and absence of the requested optimization fails.
"""
import argparse
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from s11_17_controls import OUT

VARIANT = 'pgo'


def body(kernel):
    name = kernel + '_' + VARIANT
    asm = (OUT / kernel / VARIANT / (name + '.s')).read_text()
    start = asm.index('\n' + name + ':')
    # Include any compiler-created .cold portion before the function size.
    end = asm.index('\n\t.size\t' + name + ',', start)
    return asm[start:end], name


class PositiveControls(unittest.TestCase):
    def test_branch_hot_falls_through(self):
        asm, name = body('branch')
        self.assertRegex(asm, r'(?s)\ttestl\t[^\n]+\n\tjne\t[^\n]+\n(?:\t(?!j|call)[^\n]*\n)*\tcall\t' +
                         name + '_branch_hot', 'zero (99%) branch must fall through to hot call')

    def test_indirect_promoted_and_inlined(self):
        asm, name = body('indirect')
        self.assertRegex(asm, r'\$' + name + r'_first\b', 'dominant target must have a guarded direct path')
        self.assertNotRegex(asm, r'\tcall\t' + name + r'_first\b', 'promoted target must be inlined')
        self.assertRegex(asm, r'\tcall\t\*', 'rare indirect target must remain supported')

    def test_division_value_fast_path(self):
        asm, _ = body('division')
        self.assertRegex(asm, r'\tcmpl\t\$7,', 'value profile must guard the dominant divisor')
        self.assertRegex(asm, r'\t(?:imul|mul)[lq]\t', 'constant seven division needs a multiply fast path')
        self.assertRegex(asm, r'\tdivl\t', 'unseen divisors must retain exact division')

    def test_hot_call_inlined(self):
        asm, name = body('inline')
        self.assertNotRegex(asm, r'\tcall\t' + name + r'_hot\b', 'profile must inline the large hot callee')
        self.assertRegex(asm, r'\timull\t\$1664525,', 'hot callee arithmetic must be present in caller')
        self.assertRegex(asm, r'\tcall\t' + name + r'_cold\b', 'cold alternative must remain supported')

    def test_switch_dominant_case_peeled(self):
        asm, name = body('switch')
        # The first case test must send zero straight to case 0 before jump-table dispatch.
        self.assertRegex(asm, r'(?s)\t(?:testl\t[^\n]+|cmpl\t\$0,[^\n]+)\n\tjne\t[^\n]+\n'
                         r'(?:\t(?!j|call)[^\n]*\n)*\tcall\t' + name + '_case0',
                         'dominant case zero must bypass the jump table on fall-through')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=['base', 'pgo', 'pgox'], default='pgo')
    args, remaining = parser.parse_known_args()
    VARIANT = args.variant
    unittest.main(argv=[sys.argv[0], *remaining])
