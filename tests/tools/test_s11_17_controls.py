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


def body(kernel, suffix=''):
    unit = kernel + '_' + VARIANT
    name = unit + suffix
    asm = (OUT / kernel / VARIANT / (unit + '.s')).read_text()
    start = asm.index('\n' + name + ':')
    # Include any compiler-created .cold portion before the function size.
    end = asm.index('\n\t.size\t' + name + ',', start)
    return asm[start:end], name


class PositiveControls(unittest.TestCase):
    def test_branch_hot_falls_through(self):
        asm, name = body('branch')
        self.assertRegex(asm, r'\ttestl\t[^\n]+\n\tjne\t([^\n]+)\n'
                         r'(?:\t(?!j|call)[^\n]*\n)*\tleal\t1\(',
                         'zero (99%) branch must fall through to hot arithmetic')
        self.assertRegex(asm, r'\tcall\t' + name + r'_cold\b', 'cold alternative must remain supported')

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

    def test_short_loop_peeled(self):
        asm, _ = body('loop', '_trip')
        # Three recurrence bodies before the first back edge demonstrate peeling,
        # rather than merely a changed register choice or branch direction.
        labels = {}
        multiplies = 0
        for i, line in enumerate(asm.splitlines()):
            if line.startswith('.L') and line.endswith(':'):
                labels[line[:-1]] = i
            if re.search(r'\timull\t\$1664525,', line):
                multiplies += 1
            jump = re.match(r'\tj\w+\t(\.L\w+)$', line)
            if jump and jump[1] in labels:
                break
        self.assertGreaterEqual(multiplies, 3, 'short trip profile must peel at least three recurrence bodies')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=['base', 'pgo', 'pgox'], default='pgo')
    args, remaining = parser.parse_known_args()
    VARIANT = args.variant
    unittest.main(argv=[sys.argv[0], *remaining])
