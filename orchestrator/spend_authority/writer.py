"""Default-path writer for ``ledgers/SPEND_AUTHORITY_LEDGER.jsonl`` (Phase 6.8 F5)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.spend_authority.ledger import SpendAuthorityRecord, append

DEFAULT_LEDGER_REL = Path("ledgers") / "SPEND_AUTHORITY_LEDGER.jsonl"


def default_ledger_path(repo_root: Path) -> Path:
    return repo_root / DEFAULT_LEDGER_REL


def append_to_repo_ledger(
    repo_root: Path,
    record: SpendAuthorityRecord,
    *,
    ledger_path: Path | None = None,
) -> dict[str, Any]:
    path = ledger_path if ledger_path is not None else default_ledger_path(repo_root)
    return append(path, record)


__all__ = ["DEFAULT_LEDGER_REL", "append_to_repo_ledger", "default_ledger_path"]
