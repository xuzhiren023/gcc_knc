"""S2-19 T0: keep remote awk unambiguous for BusyBox as well as GNU awk."""
from pathlib import Path
import re
import shlex
import unittest


ROOT = Path(__file__).resolve().parents[2]
# Control statements also take a parenthesized expression. Other identifiers
# followed by whitespace and '(' can be mistaken for function calls by BusyBox.
PAREN_NAMES = set("""
    if for while print printf getline
    atan2 cos sin exp log sqrt int rand srand
    gsub sub index length match split sprintf substr tolower toupper
    close system fflush mktime strftime systime
""".split())
AWK_TOKENS = re.compile(
    r'"(?:\\.|[^"\\])*"|\#[^\n]*|/(?:\\.|[^/\\\n])*/'
    r'|\b(?P<name>[A-Za-z_][A-Za-z_0-9]*)\s+\('
)


class CardAwk(unittest.TestCase):
    def test_all_remote_awk_programs_have_unambiguous_parentheses(self):
        words = shlex.split((ROOT / "tools/card_run_remote.sh").read_text(), comments=True)
        programs = [words[i + 1] for i, word in enumerate(words) if word == "awk"]
        self.assertTrue(programs, "no remote awk programs found")
        for number, program in enumerate(programs, 1):
            # Current invocations put the inline program immediately after awk.
            # Fail explicitly if options are added, so no program escapes this check.
            self.assertFalse(program.startswith("-"), "update awk program extraction for options")
            for token in AWK_TOKENS.finditer(program):
                name = token.group("name")
                if name is not None:
                    line = program.count("\n", 0, token.start()) + 1
                    with self.subTest(program=number, line=line, name=name):
                        self.assertIn(name, PAREN_NAMES,
                                      "BusyBox may parse identifier + whitespace + '(' as a call")


if __name__ == "__main__":
    unittest.main()
