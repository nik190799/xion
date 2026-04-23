"""`xion-verify --self-test` — defend against a tampered local copy.

Property promised. Before xion-verify is trusted to tell the truth about any
other artifact, it must be able to prove that its own source has not been
altered since the pin was committed. A tampered copy is caught before any
constitutional check runs; a legitimate change requires the pin to be updated
in the same commit (CI enforces this).

Algorithm. `tree_hash` over every `*.py` file under `src/xion_verify/`, sorted
by POSIX relpath, excluding `PINNED_HASH.txt` itself (a file cannot contain
its own hash). Compared byte-for-byte against `PINNED_HASH.txt`.

Updating the pin. `xion-verify --self-test --update --i-understand` writes the
current tree hash to `PINNED_HASH.txt`. Both flags are required to defeat a
casual re-pin by a compromised operator: `--update` alone errors; only the
pair executes. CI uses neither.
"""

from __future__ import annotations

from pathlib import Path

from xion_verify.exit_codes import FAIL, OK, TAMPERED
from xion_verify.hashing import tree_hash

_PIN_FILENAME = "PINNED_HASH.txt"
_PACKAGE_PATTERNS: tuple[str, ...] = ("**/*.py",)


def _package_root() -> Path:
    """Return the installed xion_verify package directory."""
    return Path(__file__).resolve().parent.parent


def pin_path() -> Path:
    return _package_root() / _PIN_FILENAME


def compute_self_hash() -> str:
    root = _package_root()
    exclude = frozenset({pin_path().resolve()})
    return tree_hash(root, _PACKAGE_PATTERNS, exclude=exclude)


def run_self_test(update: bool, i_understand: bool) -> tuple[int, str]:
    """Return (exit_code, message)."""
    current = compute_self_hash()
    pp = pin_path()

    if update:
        if not i_understand:
            return (
                FAIL,
                "--self-test --update requires --i-understand (refuse casual re-pin; see commands/self_test.py)",
            )
        pp.write_text(current + "\n", encoding="utf-8")
        return OK, f"--self-test: pin updated to {current}"

    if not pp.is_file():
        return (
            TAMPERED,
            f"--self-test: TAMPERED — no pin at {pp}. Run with --update --i-understand to create one (only from a trusted commit).",
        )

    expected = pp.read_text(encoding="utf-8").strip()
    if not expected:
        return TAMPERED, f"--self-test: TAMPERED — empty pin at {pp}"

    if expected != current:
        return (
            TAMPERED,
            (
                "--self-test: TAMPERED — package source hash does not match pin.\n"
                f"  expected: {expected}\n"
                f"  actual:   {current}\n"
                "  This may mean: (a) your local copy has been modified, or (b) the pin has not been\n"
                "  regenerated after an intentional source change. Re-pin only from a clean, trusted\n"
                "  commit via: xion-verify --self-test --update --i-understand"
            ),
        )

    return OK, f"--self-test: OK (source hash matches pin: {current})"
