#!/usr/bin/env python3
"""Compatibility wrapper for Arweave balance checks."""

from __future__ import annotations

from xion_ops.cli import main

if __name__ == "__main__":
    main(args=["balances", "--service", "arweave"])
