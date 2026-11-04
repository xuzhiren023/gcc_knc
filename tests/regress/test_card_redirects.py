"""S3-19 T0: silence stderr before opening a potentially vanished input."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]


class CardRedirects(unittest.TestCase):
    def test_stderr_redirect_precedes_input(self):
        script = (ROOT / "tools/card_run_remote.sh").read_text()
        # Include continued launch commands as well as the status-read loops.
        script = script.replace("\\\n", " ")
        self.assertNotRegex(script, re.compile(r'(?m)^[^#\n]*<[^\n]*\b2>'),
                            "redirect stderr before input so open errors use it")


if __name__ == "__main__":
    unittest.main()
