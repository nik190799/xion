from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from xion_audit.replay import replay


def test_replay_chutes_requires_chutes_key(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("XION_CHUTES_API_KEY", raising=False)
    candidate = "benign candidate"
    candidate_path = tmp_path / "candidate.txt"
    candidate_path.write_text(candidate, encoding="utf-8")
    ledger_path = tmp_path / "SAFETY_LEDGER.jsonl"
    row = {
        "schema_version": 2,
        "seq": 0,
        "prev_hash": "0" * 64,
        "this_hash": "1" * 64,
        "timestamp_utc_ns": 1,
        "correlation_id": "cid",
        "candidate_sha256": hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
        "verdict": "ok",
        "summary": "ok",
        "llm_verdict": {
            "provider_id": "chutes-llm-judge",
            "model_id": "deepseek-ai/DeepSeek-V3.2",
            "provider_version": 1,
            "latency_ms": 1,
            "decision": "ok",
            "summary": "ok",
            "raw_output_sha256": "2" * 64,
            "principle_id": None,
            "confidence": 0.0,
        },
    }
    ledger_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    result = CliRunner().invoke(
        replay,
        [
            "--ledger",
            str(ledger_path),
            "--seq",
            "0",
            "--candidate-file",
            str(candidate_path),
        ],
    )

    assert result.exit_code == 2
    assert "XION_CHUTES_API_KEY not set" in result.output
