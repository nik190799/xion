"""Operational automation layer for Xion deployments.

`xion_ops` is intentionally separate from `orchestrator`: it wraps external
operator substrates (Akash, Arweave, Chutes, Base EVM) behind service classes
and composes those classes into deployment lifecycles. The same methods are
called by scripts, CLI, HTTP routes, and future runtime callers.
"""

from __future__ import annotations

__version__ = "0.1.0"

