#!/usr/bin/env python3
"""knc-twin command-line entry point. Standard library only; Python 3.8+.

Run `python knc_twin.py capabilities` first. Bundled profiles, schemas, fixtures and tests
are resolved relative to this file, not to the current directory.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from knc_model.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
