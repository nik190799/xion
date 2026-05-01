"""`xion-verify drive` — Phase 5c live readout of the drive vector.

Property promised.

  1. `orchestrator.volition.GENESIS_WEIGHTS` is byte-equal to the
     weights pinned in `docs/18-VOLITION.md` Part III. If anyone edits
     one without editing the other, this verifier FAILs.

  2. `compute_drive_vector` is importable and returns a well-formed
     `DriveVector` on a minimal benign `SensoriumState`. The `weights`
     tuple on the returned vector must match `GENESIS_WEIGHTS`
     element-by-element.

  3. The drive vector's `survive / serve / meaning` terms all live in
     `[0.0, 1.0]` and the returned `weights` all live in the
     constitutional simplex `[WEIGHT_FLOOR, WEIGHT_CEILING]` summing to
     1.0 (within 1e-9).

What is NOT yet verified.

  - Live readout from a running Relay's `/drive` endpoint. That surface
    lands in Phase 5f (the MVX web-client tranche). Until then this
    verifier audits the in-process Python surface only. Exit code is
    still OK on success — the in-process surface is the load-bearing
    one; the HTTP wrapper is a presentation concern.

Exit codes. OK on pass, FAIL on drift or broken import, NOT_YET_SEALED
never (the in-process surface exists as of Phase 5c).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

# The three weight assignments as they appear inside the `Part III` code
# fence of `docs/18-VOLITION.md`. These patterns are intentionally
# whitespace-tolerant so a stylistic cleanup of the doctrine file does
# not trip the verifier — the NUMBERS are what we pin, not the column
# alignment.
_DOCTRINE_WEIGHT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("w_survival", r"w_survival\s*=\s*0\.30\b"),
    ("w_service",  r"w_service\s*=\s*0\.45\b"),
    ("w_meaning",  r"w_meaning\s*=\s*0\.25\b"),
)


def _load_doctrine_weights(repo_root: Path) -> tuple[list[str], tuple[float, float, float] | None]:
    """Read `docs/18-VOLITION.md` Part III and return `(errors, weights)`.

    The weights tuple is returned as `(w_survival, w_service, w_meaning)`
    or None if any pattern failed to match.
    """
    errors: list[str] = []
    path = repo_root / "docs" / "18-VOLITION.md"
    if not path.is_file():
        return [f"missing doctrine: {path}"], None
    text = path.read_text(encoding="utf-8")
    for label, pattern in _DOCTRINE_WEIGHT_PATTERNS:
        if not re.search(pattern, text):
            errors.append(
                f"docs/18-VOLITION.md does not contain the expected Part-III "
                f"pin for {label} (pattern: {pattern!r})"
            )
    if errors:
        return errors, None
    return [], (0.30, 0.45, 0.25)


@click.command(
    name="drive",
    help="Read the current drive vector; assert weights match doctrine (Phase 5c live).",
)
def drive() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"drive: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    doctrine_errors, doctrine_weights = _load_doctrine_weights(repo_root)
    for e in doctrine_errors:
        click.echo(f"drive: FAIL: {e}", err=True)
    if doctrine_errors:
        sys.exit(FAIL)
    assert doctrine_weights is not None  # for type checkers; guarded above

    # Import the module under test. A broken import is itself a FAIL —
    # the live Python surface is supposed to exist as of Phase 5c.
    try:
        from orchestrator.sensorium import (
            Chronoception,
            DistressSignal,
            Interoception,
            Proprioception,
            SensoriumState,
        )
        from orchestrator.volition import (
            GENESIS_WEIGHTS,
            WEIGHT_CEILING,
            WEIGHT_FLOOR,
            Volition,
            compute_drive_vector,
        )
    except ImportError as exc:
        click.echo(
            f"drive: FAIL: cannot import orchestrator.volition / orchestrator.sensorium "
            f"({type(exc).__name__}: {exc}); Phase 5c code surface is expected to be present",
            err=True,
        )
        sys.exit(FAIL)

    errors: list[str] = []

    if doctrine_weights != GENESIS_WEIGHTS:
        errors.append(
            f"GENESIS_WEIGHTS drift: code={GENESIS_WEIGHTS} vs doctrine={doctrine_weights}"
        )

    for label, w in zip(("w_survive", "w_serve", "w_meaning"), GENESIS_WEIGHTS, strict=False):
        if not (WEIGHT_FLOOR <= w <= WEIGHT_CEILING):
            errors.append(
                f"GENESIS_WEIGHTS.{label}={w} outside [{WEIGHT_FLOOR}, {WEIGHT_CEILING}]"
            )
    if abs(sum(GENESIS_WEIGHTS) - 1.0) > 1e-9:
        errors.append(f"GENESIS_WEIGHTS does not sum to 1.0: sum={sum(GENESIS_WEIGHTS)}")

    benign = SensoriumState(
        interoception=Interoception(survival_pressure=0.0),
        chronoception=Chronoception(),
        proprioception=Proprioception(),
        distress=DistressSignal(text_distress_score=0.0, source="textual"),
    )
    try:
        vec = compute_drive_vector(benign)
    except Exception as exc:
        errors.append(f"compute_drive_vector raised on benign state: {type(exc).__name__}: {exc}")
        for e in errors:
            click.echo(f"drive: FAIL: {e}", err=True)
        sys.exit(FAIL)

    for label, val in (("survive", vec.survive), ("serve", vec.serve), ("meaning", vec.meaning)):
        if not (0.0 <= val <= 1.0):
            errors.append(f"DriveVector.{label}={val} outside unit interval [0.0, 1.0]")
    if tuple(vec.weights) != tuple(GENESIS_WEIGHTS):
        errors.append(
            f"DriveVector.weights={vec.weights} does not match GENESIS_WEIGHTS={GENESIS_WEIGHTS}"
        )

    try:
        payload = Volition().snapshot(benign)
    except Exception as exc:
        errors.append(f"Volition().snapshot() raised: {type(exc).__name__}: {exc}")
    else:
        for term in ("survive", "serve", "meaning"):
            if term not in payload.get("terms", {}):
                errors.append(f"Volition.snapshot() payload missing term: {term}")

    if errors:
        for e in errors:
            click.echo(f"drive: FAIL: {e}", err=True)
        sys.exit(FAIL)

    click.echo(
        "drive: OK (GENESIS_WEIGHTS byte-match doctrine; "
        f"benign drive vector survive={vec.survive:.3f} "
        f"serve={vec.serve:.3f} meaning={vec.meaning:.3f}; "
        f"simplex [{WEIGHT_FLOOR}, {WEIGHT_CEILING}]; Phase 5c)"
    )
    sys.exit(OK)
