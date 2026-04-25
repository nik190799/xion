from __future__ import annotations

import hashlib
import json
from pathlib import Path

from xion_verify.commands.model_promotion_discipline import check_model_promotion_discipline


def _repo(tmp_path: Path) -> tuple[Path, str]:
    (tmp_path / "genesis").mkdir()
    (tmp_path / "ledgers").mkdir()
    pin = tmp_path / "genesis" / "PINNED_HASH.txt"
    pin.write_text("pin\n", encoding="utf-8")
    return tmp_path, hashlib.sha256(pin.read_bytes()).hexdigest()


def _write(repo: Path, rows: list[dict]) -> Path:
    ledger = repo / "ledgers" / "MODEL_REGISTRY_LEDGER.jsonl"
    ledger.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
    return ledger


def _seed(slug: str, evidence: str, **overrides) -> dict:
    row = {
        "event": "genesis_seed",
        "provider": "chutes",
        "model_slug": slug,
        "from_state": None,
        "to_state": "primary",
        "evidence_bundle_hash": evidence,
        "cost_delta": 0.0,
        "quality_delta": 0.0,
        "refusal_delta": 0.0,
        "approver": "operator-genesis-signature",
    }
    row.update(overrides)
    return row


def _promotion(slug: str, from_state, to_state: str, evidence: str = "e" * 64) -> dict:
    return {
        "event": "promotion",
        "provider": "chutes",
        "model_slug": slug,
        "from_state": from_state,
        "to_state": to_state,
        "evidence_bundle_hash": evidence,
        "cost_delta": 1.0,
        "quality_delta": 1.0,
        "refusal_delta": 0.0,
        "approver": "operator",
    }


def test_accepts_genesis_seed_then_promotion_chain(tmp_path: Path) -> None:
    repo, evidence = _repo(tmp_path)
    ledger = _write(
        repo,
        [
            _seed("moonshotai/Kimi-K2.6-TEE", evidence),
            _promotion("new/model", None, "audition"),
            _promotion("new/model", "audition", "canary"),
            _promotion("new/model", "canary", "primary"),
        ],
    )

    assert check_model_promotion_discipline(repo, ledger) == ([], [])


def test_rejects_seed_row_after_first_row_for_slug(tmp_path: Path) -> None:
    repo, evidence = _repo(tmp_path)
    ledger = _write(repo, [_seed("m", evidence), _seed("m", evidence)])

    errors, _ = check_model_promotion_discipline(repo, ledger)
    assert any("genesis_seed must be first row" in error for error in errors)


def test_rejects_seed_row_with_wrong_hash(tmp_path: Path) -> None:
    repo, evidence = _repo(tmp_path)
    ledger = _write(repo, [_seed("m", evidence="bad" + evidence)])

    errors, _ = check_model_promotion_discipline(repo, ledger)
    assert any("evidence hash mismatch" in error for error in errors)


def test_rejects_seed_row_with_wrong_approver(tmp_path: Path) -> None:
    repo, evidence = _repo(tmp_path)
    ledger = _write(repo, [_seed("m", evidence, approver="operator")])

    errors, _ = check_model_promotion_discipline(repo, ledger)
    assert any("approver mismatch" in error for error in errors)


def test_rejects_promotion_row_with_from_state_mismatch(tmp_path: Path) -> None:
    repo, evidence = _repo(tmp_path)
    ledger = _write(repo, [_promotion("m", "audition", "canary", evidence)])

    errors, _ = check_model_promotion_discipline(repo, ledger)
    assert any("from_state mismatch" in error for error in errors)
