"""Entry point for `python -m xion_verify`."""

from __future__ import annotations

import sys

from xion_verify.cli import main

if __name__ == "__main__":
    sys.exit(main())
