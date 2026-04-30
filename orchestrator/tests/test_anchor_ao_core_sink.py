import subprocess
from pathlib import Path
from types import SimpleNamespace

from orchestrator.anchor.ledger import read_chain
from orchestrator.anchor.sink_ao_core import AOCoreSink


def test_ao_core_sink_records_message_id(tmp_path: Path, monkeypatch):
    anchor_path = tmp_path / "ANCHOR_LEDGER.jsonl"

    def fake_run(*args, **kwargs):
        assert "ao-send-anchor-batch.cjs" in str(args[0][1])
        assert args[0][2] == "proc-1"
        assert args[0][3] == "wallet.json"
        return SimpleNamespace(stdout="ao-message-1\n")

    monkeypatch.setattr(subprocess, "run", fake_run)

    receipt = AOCoreSink(
        anchor_ledger_path=str(anchor_path),
        ao_gateway_url="http://localhost:4004",
        ao_process_id="proc-1",
        ao_signer_jwk_path="wallet.json",
    ).submit(
        period_start_unix=1,
        period_end_unix=2,
        ledger_kind="request",
        batch_root_sha256="a" * 64,
        batch_size=1,
        leaf_correlation_ids=["c1"],
    )

    records = list(read_chain(anchor_path))
    assert receipt.kind == "ao_core"
    assert receipt.ao_message_id == "ao-message-1"
    assert records[0].ao_message_id == "ao-message-1"
    assert records[0].degraded_to_local is None


def test_ao_core_sink_degrades_to_local_on_send_failure(tmp_path: Path, monkeypatch):
    anchor_path = tmp_path / "ANCHOR_LEDGER.jsonl"

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=args[0])

    monkeypatch.setattr(subprocess, "run", fake_run)

    receipt = AOCoreSink(
        anchor_ledger_path=str(anchor_path),
        ao_gateway_url="http://localhost:4004",
        ao_process_id="proc-1",
        ao_signer_jwk_path="wallet.json",
    ).submit(
        period_start_unix=1,
        period_end_unix=2,
        ledger_kind="request",
        batch_root_sha256="b" * 64,
        batch_size=1,
        leaf_correlation_ids=["c1"],
    )

    records = list(read_chain(anchor_path))
    assert receipt.kind == "local_only"
    assert receipt.ao_message_id is None
    assert records[0].ao_message_id is None
    assert records[0].degraded_to_local is True
