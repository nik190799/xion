"""Exit codes used across every subcommand.

Consistency is load-bearing: CI and third-party auditors script against these.
Never renumber. Append only.
"""

from __future__ import annotations

OK = 0
FAIL = 1
NOT_YET_SEALED = 2
TAMPERED = 3

_NAMES: dict[int, str] = {
    OK: "OK",
    FAIL: "FAIL",
    NOT_YET_SEALED: "NOT_YET_SEALED",
    TAMPERED: "TAMPERED",
}


def name(code: int) -> str:
    """Human-readable label for an exit code."""
    return _NAMES.get(code, f"UNKNOWN({code})")


def exit_code_to_system_exit(code: int) -> int:
    """Map verifier exit code to the process return code (identity)."""
    return code
