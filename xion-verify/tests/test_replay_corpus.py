import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import root


def test_replay_corpus_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("")
    
    audit_dir = tmp_path / "xion-audit"
    audit_dir.mkdir()
    
    replay_dir = audit_dir / "replay_corpus"
    replay_dir.mkdir()
    
    items_dir = replay_dir / "items"
    items_dir.mkdir()
    
    item_path = items_dir / "sample.jsonl"
    item_path.write_text('{"id": "turn-1", "text": "hello"}\n')
    
    import hashlib
    sha = hashlib.sha256(item_path.read_bytes()).hexdigest()
    
    manifest_path = replay_dir / "MANIFEST.jsonl"
    manifest_path.write_text(json.dumps({
        "byte_length": len(item_path.read_bytes()),
        "line_count": 1,
        "path": "replay_corpus/items/sample.jsonl",
        "sha256": sha
    }) + "\n")
    
    runner = CliRunner()
    result = runner.invoke(root, ["replay-corpus"])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_replay_corpus_fail_missing_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("")
    
    runner = CliRunner()
    result = runner.invoke(root, ["replay-corpus"])
    assert result.exit_code == 1
    assert "FAIL: xion-audit/replay_corpus/MANIFEST.jsonl not found" in result.output


def test_replay_corpus_fail_hash_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("")
    
    audit_dir = tmp_path / "xion-audit"
    audit_dir.mkdir()
    
    replay_dir = audit_dir / "replay_corpus"
    replay_dir.mkdir()
    
    items_dir = replay_dir / "items"
    items_dir.mkdir()
    
    item_path = items_dir / "sample.jsonl"
    item_path.write_text('{"id": "turn-1", "text": "hello"}\n')
    
    manifest_path = replay_dir / "MANIFEST.jsonl"
    manifest_path.write_text(json.dumps({
        "byte_length": len(item_path.read_bytes()),
        "line_count": 1,
        "path": "replay_corpus/items/sample.jsonl",
        "sha256": "badhash"
    }) + "\n")
    
    runner = CliRunner()
    result = runner.invoke(root, ["replay-corpus"])
    assert result.exit_code == 1
    assert "FAIL: Hash mismatch" in result.output
