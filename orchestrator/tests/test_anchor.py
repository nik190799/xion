"""Tests for `orchestrator.safety.anchor` — cadence policy, writer,
submitter ABC, chain verifier, and cross-check to the main ledger.

The Arweave submitter's live path is not tested here; it requires
network + a real JWK. Phase 5 integration tests cover that end-to-end.
This file exercises every path that runs offline, including the
failure modes of a misconfigured ArweaveSubmitter.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.safety import gate
from orchestrator.safety.anchor import (
    SCHEMA_VERSION,
    AnchorChainBroken,
    AnchorCrossCheckFailed,
    AnchorReceipt,
    AnchorSubmitter,
    ArweaveSubmitter,
    CadencePolicy,
    LocalOnlySubmitter,
    cross_check_anchors_against_ledger,
    iter_anchor_rows,
    run_anchor_once,
    should_anchor,
    verify_anchor_chain,
    write_anchor,
)
from orchestrator.safety.ledger import ZERO_HASH, chain_tip


@pytest.fixture
def anchors_path(tmp_path: Path) -> Path:
    return tmp_path / "SAFETY_LEDGER_ANCHORS.jsonl"


def _populate_ledger(ledger_path: Path, n: int) -> None:
    """Drive `gate()` n times to append OK rows to the ledger."""
    for i in range(n):
        gate(f"benign {i}", correlation_id=f"c-{i}", ledger_path=ledger_path)


# ================================================================ AnchorReceipt


def test_receipt_arweave_requires_tx_and_wallet():
    with pytest.raises(ValueError, match="ar_tx_id"):
        AnchorReceipt(submitted_to="arweave", ar_tx_id=None, wallet_address="addr")
    with pytest.raises(ValueError, match="wallet_address"):
        AnchorReceipt(submitted_to="arweave", ar_tx_id="tx", wallet_address=None)


def test_receipt_local_forbids_arweave_fields():
    with pytest.raises(ValueError, match="local"):
        AnchorReceipt(submitted_to="local", ar_tx_id="tx", wallet_address=None)


def test_receipt_invalid_submitted_to_rejected():
    with pytest.raises(ValueError):
        AnchorReceipt(submitted_to="nowhere")


# ============================================================= AnchorSubmitter


def test_submitter_cannot_be_instantiated():
    with pytest.raises(TypeError):
        AnchorSubmitter()  # type: ignore[abstract]


def test_concrete_submitter_missing_id_rejected():
    with pytest.raises(TypeError, match="submitter_id"):

        class _NoId(AnchorSubmitter):
            submitter_version = 1

            def submit(self, body):
                return AnchorReceipt(submitted_to="local")


def test_local_only_submitter_receipt_shape():
    r = LocalOnlySubmitter().submit({})
    assert r.submitted_to == "local"
    assert r.ar_tx_id is None
    assert r.wallet_address is None


# ============================================================ CadencePolicy


def test_should_anchor_empty_ledger(ledger_path: Path, anchors_path: Path):
    # No ledger rows yet -> no anchor.
    d = should_anchor(anchors_path=anchors_path, ledger_path=ledger_path)
    assert d.should_anchor is False
    assert "empty" in d.reason


def test_should_anchor_startup_fires_on_first_call(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 1)
    d = should_anchor(anchors_path=anchors_path, ledger_path=ledger_path)
    assert d.should_anchor is True
    assert d.trigger == "startup"


def test_should_anchor_respects_startup_opt_out(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 1)
    policy = CadencePolicy(startup_anchor_required=False)
    d = should_anchor(anchors_path=anchors_path, ledger_path=ledger_path, policy=policy)
    assert d.should_anchor is False


def test_should_anchor_row_count_trigger(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 3)
    # Seed an anchor that covers 1 row.
    write_anchor(
        anchors_path,
        ledger_path=ledger_path,  # will capture current tip (3 rows) but we'll rewrite
        cadence_trigger="startup",
    )
    # Wipe and hand-craft an anchor that claims only 1 row covered,
    # so delta_rows = 3-1 = 2.
    row = next(iter(iter_anchor_rows(anchors_path)))
    row["ledger_row_count"] = 1
    anchors_path.write_bytes(
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        + b"\n"
    )
    policy = CadencePolicy(row_count_threshold=2, wall_time_threshold_s=10**9)
    d = should_anchor(
        anchors_path=anchors_path,
        ledger_path=ledger_path,
        policy=policy,
        now_utc_ns=row["timestamp_utc_ns"] + 1_000_000_000,
    )
    assert d.should_anchor is True
    assert d.trigger == "row_count"


def test_should_anchor_wall_time_trigger(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 2)
    write_anchor(anchors_path, ledger_path=ledger_path, cadence_trigger="startup")
    row = next(iter(iter_anchor_rows(anchors_path)))
    # No new ledger rows; advance time past the wall-time threshold.
    policy = CadencePolicy(row_count_threshold=10_000, wall_time_threshold_s=60)
    now = row["timestamp_utc_ns"] + 61 * 1_000_000_000
    d = should_anchor(
        anchors_path=anchors_path,
        ledger_path=ledger_path,
        policy=policy,
        now_utc_ns=now,
    )
    assert d.should_anchor is True
    assert d.trigger == "wall_time"


def test_should_anchor_no_trigger(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 2)
    write_anchor(anchors_path, ledger_path=ledger_path, cadence_trigger="startup")
    row = next(iter(iter_anchor_rows(anchors_path)))
    policy = CadencePolicy(row_count_threshold=10_000, wall_time_threshold_s=10**9)
    d = should_anchor(
        anchors_path=anchors_path,
        ledger_path=ledger_path,
        policy=policy,
        now_utc_ns=row["timestamp_utc_ns"] + 1,
    )
    assert d.should_anchor is False
    assert "no trigger" in d.reason


# ================================================================= write_anchor


def test_write_anchor_first_row_shape(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 5)
    lc, ltip = chain_tip(ledger_path)
    row = write_anchor(
        anchors_path,
        ledger_path=ledger_path,
        cadence_trigger="startup",
    )
    assert row["seq"] == 0
    assert row["prev_hash"] == ZERO_HASH
    assert row["schema_version"] == SCHEMA_VERSION
    assert row["ledger_name"] == "SAFETY_LEDGER"
    assert row["ledger_row_count"] == lc
    assert row["ledger_tip_hash"] == ltip
    assert row["cadence_trigger"] == "startup"
    assert row["submitted_to"] == "local"
    assert row["ar_tx_id"] is None
    assert row["wallet_address"] is None
    assert row["submitter_id"] == "local_only_v1"
    assert row["submitter_version"] == 1
    assert len(row["this_hash"]) == 64


def test_write_anchor_chain_links(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 3)
    r0 = write_anchor(anchors_path, ledger_path=ledger_path, cadence_trigger="startup")
    _populate_ledger(ledger_path, 2)  # 5 total rows
    r1 = write_anchor(anchors_path, ledger_path=ledger_path, cadence_trigger="row_count")
    assert r1["seq"] == 1
    assert r1["prev_hash"] == r0["this_hash"]
    count, tip = verify_anchor_chain(anchors_path)
    assert count == 2
    assert tip == r1["this_hash"]


def test_write_anchor_rejects_bad_trigger(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 1)
    with pytest.raises(ValueError, match="cadence_trigger"):
        write_anchor(anchors_path, ledger_path=ledger_path, cadence_trigger="bad")


def test_write_anchor_submitter_raise_does_not_write(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 1)

    class _Broken(AnchorSubmitter):
        submitter_id = "broken"
        submitter_version = 1

        def submit(self, body):
            raise RuntimeError("no network")

    with pytest.raises(RuntimeError, match="no network"):
        write_anchor(
            anchors_path,
            ledger_path=ledger_path,
            cadence_trigger="startup",
            submitter=_Broken(),
        )
    assert not anchors_path.exists()
    # Honest record: zero anchors because zero anchors succeeded.


# =========================================================== run_anchor_once


def test_run_anchor_once_startup(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 2)
    result = run_anchor_once(anchors_path=anchors_path, ledger_path=ledger_path)
    assert result.anchored is True
    assert result.trigger == "startup"
    assert result.row is not None
    count, _ = verify_anchor_chain(anchors_path)
    assert count == 1


def test_run_anchor_once_skip_when_not_due(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 2)
    run_anchor_once(anchors_path=anchors_path, ledger_path=ledger_path)
    # Second call: cadence does not fire.
    policy = CadencePolicy(row_count_threshold=10_000, wall_time_threshold_s=10**9)
    result = run_anchor_once(
        anchors_path=anchors_path, ledger_path=ledger_path, policy=policy
    )
    assert result.anchored is False
    assert result.row is None


def test_run_anchor_once_force_bypasses_cadence(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 2)
    run_anchor_once(anchors_path=anchors_path, ledger_path=ledger_path)
    policy = CadencePolicy(row_count_threshold=10_000, wall_time_threshold_s=10**9)
    result = run_anchor_once(
        anchors_path=anchors_path,
        ledger_path=ledger_path,
        policy=policy,
        force=True,
    )
    assert result.anchored is True
    count, _ = verify_anchor_chain(anchors_path)
    assert count == 2


def test_run_anchor_once_empty_ledger_skips_even_with_force(ledger_path: Path, anchors_path: Path):
    result = run_anchor_once(
        anchors_path=anchors_path,
        ledger_path=ledger_path,
        force=True,
    )
    assert result.anchored is False
    assert "empty" in result.reason
    assert not anchors_path.exists()


# ================================================================ verify_anchor_chain


def test_verify_anchor_empty_returns_zero(anchors_path: Path):
    count, tip = verify_anchor_chain(anchors_path)
    assert (count, tip) == (0, ZERO_HASH)


def test_verify_anchor_single_row_ok(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 1)
    write_anchor(anchors_path, ledger_path=ledger_path, cadence_trigger="startup")
    count, tip = verify_anchor_chain(anchors_path)
    assert count == 1
    assert len(tip) == 64


def test_verify_anchor_tamper_detected(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 1)
    write_anchor(anchors_path, ledger_path=ledger_path, cadence_trigger="startup")
    raw = anchors_path.read_bytes().splitlines()
    row = json.loads(raw[0])
    row["ledger_tip_hash"] = "ff" * 32
    # Do NOT re-hash; tamper should be caught by the this_hash recompute.
    raw[0] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    anchors_path.write_bytes(b"\n".join(raw) + b"\n")
    with pytest.raises(AnchorChainBroken) as ei:
        verify_anchor_chain(anchors_path)
    assert "this_hash" in str(ei.value)


def test_verify_anchor_missing_field_detected(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 1)
    write_anchor(anchors_path, ledger_path=ledger_path, cadence_trigger="startup")
    raw = anchors_path.read_bytes().splitlines()
    row = json.loads(raw[0])
    del row["ledger_tip_hash"]
    raw[0] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    anchors_path.write_bytes(b"\n".join(raw) + b"\n")
    with pytest.raises(AnchorChainBroken) as ei:
        verify_anchor_chain(anchors_path)
    assert "ledger_tip_hash" in str(ei.value)


def test_verify_anchor_local_with_arweave_fields_rejected(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 1)
    write_anchor(anchors_path, ledger_path=ledger_path, cadence_trigger="startup")
    from orchestrator.safety.anchor import (
        _canonical_bytes_excluding_this_hash,
        _sha256_hex,
    )

    raw = anchors_path.read_bytes().splitlines()
    row = json.loads(raw[0])
    row["ar_tx_id"] = "forged"
    row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
    raw[0] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    anchors_path.write_bytes(b"\n".join(raw) + b"\n")
    with pytest.raises(AnchorChainBroken) as ei:
        verify_anchor_chain(anchors_path)
    assert "local" in str(ei.value) and "ar_tx_id" in str(ei.value)


# ================================================= cross_check_anchors_against_ledger


def test_cross_check_clean(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 3)
    write_anchor(anchors_path, ledger_path=ledger_path, cadence_trigger="startup")
    _populate_ledger(ledger_path, 2)  # 5 rows total
    write_anchor(anchors_path, ledger_path=ledger_path, cadence_trigger="row_count")
    n, covered = cross_check_anchors_against_ledger(anchors_path, ledger_path)
    assert n == 2
    assert covered == 5


def test_cross_check_detects_ledger_truncation(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 3)
    write_anchor(anchors_path, ledger_path=ledger_path, cadence_trigger="startup")
    # Truncate the ledger to 2 rows.
    raw = ledger_path.read_bytes().splitlines()
    ledger_path.write_bytes(b"\n".join(raw[:2]) + b"\n")
    with pytest.raises(AnchorCrossCheckFailed) as ei:
        cross_check_anchors_against_ledger(anchors_path, ledger_path)
    # Depending on exactly how, we detect either "no row at seq" or tip mismatch.
    msg = str(ei.value)
    assert "ledger" in msg and ("truncated" in msg or "does not match" in msg)


def test_cross_check_detects_ledger_rewrite(ledger_path: Path, anchors_path: Path):
    _populate_ledger(ledger_path, 2)
    write_anchor(anchors_path, ledger_path=ledger_path, cadence_trigger="startup")
    # Silently rewrite the last ledger row's correlation_id.
    raw = ledger_path.read_bytes().splitlines()
    row = json.loads(raw[-1])
    row["correlation_id"] = "attacker-replaced"
    # Re-hash so the ledger itself still passes verify_chain.
    from orchestrator.safety.ledger import (
        _canonical_bytes_excluding_this_hash,
        _sha256_hex,
    )
    row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
    raw[-1] = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ledger_path.write_bytes(b"\n".join(raw) + b"\n")
    # The ledger's internal chain no longer links (seq 1's prev_hash no longer
    # matches seq 0's this_hash — but here we rewrote the LAST row, so chain
    # still links). The anchor however caught the earlier tip; now the real
    # tip differs. Cross-check must fail.
    with pytest.raises(AnchorCrossCheckFailed) as ei:
        cross_check_anchors_against_ledger(anchors_path, ledger_path)
    assert "does not match" in str(ei.value) or "rewritten" in str(ei.value)


# ============================================================= ArweaveSubmitter


def test_arweave_submitter_without_arweave_package_or_jwk_raises(monkeypatch):
    """Without `arweave-python-client` installed, or with the env unset,
    the submitter MUST raise at submit() time (never silently succeed).
    We can rely on one of the two failure paths — whichever applies in
    this test environment."""
    monkeypatch.delenv("XION_ANCHOR_WALLET_JWK_PATH", raising=False)
    s = ArweaveSubmitter()
    with pytest.raises(RuntimeError):
        s.submit({
            "schema_version": 1,
            "timestamp_utc_ns": 0,
            "ledger_name": "SAFETY_LEDGER",
            "ledger_row_count": 1,
            "ledger_tip_hash": "0" * 64,
            "cadence_trigger": "startup",
            "submitter_id": "arweave_v1",
            "submitter_version": 1,
        })
