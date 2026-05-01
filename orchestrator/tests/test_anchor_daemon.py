"""Tests for the AnchorDaemon."""

import json
from pathlib import Path

from orchestrator.anchor.daemon import AnchorDaemon
from orchestrator.anchor.sink import AnchorReceipt, AnchorSink


class MemorySink(AnchorSink):
    def __init__(self):
        self.submissions = []

    def submit(self, period_start_unix, period_end_unix, ledger_kind, batch_root_sha256, batch_size, leaf_correlation_ids):
        self.submissions.append({
            "period_start_unix": period_start_unix,
            "period_end_unix": period_end_unix,
            "ledger_kind": ledger_kind,
            "batch_root_sha256": batch_root_sha256,
            "batch_size": batch_size,
            "leaf_correlation_ids": leaf_correlation_ids
        })
        return AnchorReceipt("local_only")

def test_anchor_daemon_tick(tmp_path: Path):
    request_path = tmp_path / "REQUEST.jsonl"
    payment_path = tmp_path / "PAYMENT.jsonl"
    safety_path = tmp_path / "SAFETY.jsonl"
    anchor_path = tmp_path / "ANCHOR.jsonl"

    # 09:00 -> 32400
    # 10:00 -> 36000
    # We will pretend the daemon ticks at 10:05 (36300), window is [32400, 36000]

    row1 = {"correlation_id": "c1", "request_arrived_utc_ns": 33000 * 1000000000, "final_outcome": "ok"}
    request_path.write_text(json.dumps(row1) + "\n")

    # One outside the window
    row2 = {"correlation_id": "c2", "request_arrived_utc_ns": 37000 * 1000000000, "final_outcome": "ok"}
    with request_path.open("a") as f:
        f.write(json.dumps(row2) + "\n")

    sink = MemorySink()
    daemon = AnchorDaemon(
        sink=sink,
        anchor_ledger_path=anchor_path,
        request_ledger_path=request_path,
        payment_ledger_path=payment_path,
        safety_ledger_path=safety_path,
        window_size_seconds=3600
    )

    daemon.tick(36300)

    assert len(sink.submissions) == 1
    sub = sink.submissions[0]
    assert sub["ledger_kind"] == "request"
    assert sub["period_start_unix"] == 32400
    assert sub["period_end_unix"] == 36000
    assert sub["batch_size"] == 1
    assert sub["leaf_correlation_ids"] == ["c1"]

    # Re-tick -> idempotent
    # To be idempotent, we need to actually write to the anchor ledger.
    # The MemorySink didn't write to anchor_path. Let's manually write.
    from orchestrator.anchor.ledger import append
    append(anchor_path, sub["period_start_unix"], sub["period_end_unix"], sub["ledger_kind"], sub["batch_root_sha256"], sub["batch_size"], sub["leaf_correlation_ids"])

    daemon.tick(36300)
    assert len(sink.submissions) == 1  # unchanged
