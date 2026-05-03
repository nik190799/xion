#!/usr/bin/env python3
"""Compatibility wrapper for Chutes module import verification."""

from __future__ import annotations

import sys

from xion_ops.cli import main

if __name__ == "__main__":
    main(args=["chutes", "verify-import", *sys.argv[1:]])
