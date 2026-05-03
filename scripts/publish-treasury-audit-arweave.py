#!/usr/bin/env python3
"""Compatibility wrapper for treasury-audit Arweave publish."""

from __future__ import annotations

import sys

from xion_ops.cli import main

if __name__ == "__main__":
    args = ["arweave", "publish-treasury-audit", *sys.argv[1:]]
    main(args=args)
