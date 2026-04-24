"""`xion-verify inference-sovereignty` — per-format dispatch (Phase 5g-viii).

The first test pair runs against the actual repo checkout; the rest of
this file uses synthetic temp-dir manifests so we can exercise every
branch of the per-format dispatch (sentinel / provenance-record /
model-blob) without depending on a 5 GB GGUF being present in CI.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import root
from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK


# ---------------------------------------------------------------------------
# Real-repo smoke tests
# ---------------------------------------------------------------------------


def _repo_root_from_test_file() -> Path:
    return Path(__file__).resolve().parents[2]


def _has_real_manifest() -> bool:
    here = _repo_root_from_test_file()
    return (here / "orchestrator" / "inference_router" / "open_weights_manifest.json").is_file()


def test_real_repo_manifest_returns_not_yet_sealed_when_gguf_unset(monkeypatch):
    """Default posture in CI: GGUF env var unset -> model-blob is NOT_YET_SEALED."""
    if not _has_real_manifest():
        pytest.skip("not a Xion repo checkout")
    here = _repo_root_from_test_file()
    monkeypatch.delenv("XION_OPEN_WEIGHTS_GGUF_PATH", raising=False)
    monkeypatch.chdir(here)
    runner = CliRunner()
    r = runner.invoke(root, ["inference-sovereignty"], catch_exceptions=False)
    assert r.exit_code == NOT_YET_SEALED, r.output
    assert "NOT_YET_SEALED" in r.output
    assert "sentinel OK" in r.output
    assert "provenance-record OK" in r.output
    assert "model-blob NOT_YET_SEALED" in r.output


def test_real_repo_manifest_with_bad_gguf_path_returns_not_yet_sealed(monkeypatch, tmp_path):
    """Env var pointing at a non-existent path is also NOT_YET_SEALED, not FAIL.

    Rationale: an absent local artifact is a Witness-side gap, not a
    structural floor failure. A typo in the env var is the same shape
    as never having set it.
    """
    if not _has_real_manifest():
        pytest.skip("not a Xion repo checkout")
    here = _repo_root_from_test_file()
    monkeypatch.setenv("XION_OPEN_WEIGHTS_GGUF_PATH", str(tmp_path / "does-not-exist.gguf"))
    monkeypatch.chdir(here)
    runner = CliRunner()
    r = runner.invoke(root, ["inference-sovereignty"], catch_exceptions=False)
    assert r.exit_code == NOT_YET_SEALED, r.output
    assert "does not resolve to a regular file" in r.output


# ---------------------------------------------------------------------------
# Synthetic temp-repo helpers
# ---------------------------------------------------------------------------


def _make_synthetic_repo(tmp_path: Path) -> Path:
    """Build a minimal directory tree that satisfies `find_repo_root`."""
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("synthetic", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("synthetic", encoding="utf-8")
    (tmp_path / "orchestrator" / "inference_router").mkdir(parents=True)
    return tmp_path


def _write_manifest(repo: Path, entries: list[dict]) -> None:
    mpath = repo / "orchestrator" / "inference_router" / "open_weights_manifest.json"
    mpath.write_text(
        json.dumps({"schema_version": 1, "open_weights": entries}, indent=2),
        encoding="utf-8",
    )


def _write_blob(path: Path, contents: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contents)
    return hashlib.sha256(contents).hexdigest()


def _run(repo: Path, monkeypatch) -> "tuple[int, str]":
    monkeypatch.chdir(repo)
    runner = CliRunner()
    r = runner.invoke(root, ["inference-sovereignty"], catch_exceptions=False)
    return r.exit_code, r.output


# ---------------------------------------------------------------------------
# Sentinel format
# ---------------------------------------------------------------------------


def test_synthetic_sentinel_only_returns_ok(tmp_path, monkeypatch):
    repo = _make_synthetic_repo(tmp_path)
    sentinel_rel = "orchestrator/inference_router/sentinel.txt"
    sha = _write_blob(repo / sentinel_rel, b"hello sentinel\n")
    _write_manifest(repo, [
        {
            "id": "sentinel-x",
            "category": "open_weights_self_hostable",
            "format": "sentinel",
            "sentinel_path": sentinel_rel,
            "sha256": sha,
        }
    ])
    code, out = _run(repo, monkeypatch)
    assert code == OK, out
    assert "sentinel-x: sentinel OK" in out


def test_synthetic_sentinel_hash_mismatch_fails(tmp_path, monkeypatch):
    repo = _make_synthetic_repo(tmp_path)
    sentinel_rel = "orchestrator/inference_router/sentinel.txt"
    _write_blob(repo / sentinel_rel, b"actual bytes\n")
    _write_manifest(repo, [
        {
            "id": "sentinel-x",
            "category": "open_weights_self_hostable",
            "format": "sentinel",
            "sentinel_path": sentinel_rel,
            "sha256": "a" * 64,
        }
    ])
    code, out = _run(repo, monkeypatch)
    assert code == FAIL, out
    assert "sentinel sha256 mismatch" in out


# ---------------------------------------------------------------------------
# Provenance-record format
# ---------------------------------------------------------------------------


def test_synthetic_provenance_record_ok(tmp_path, monkeypatch):
    repo = _make_synthetic_repo(tmp_path)
    rel = "orchestrator/inference_router/floor_provenance.txt"
    sha = _write_blob(repo / rel, b"operator declaration about the runtime\n")
    _write_manifest(repo, [
        {
            "id": "prov-x",
            "category": "open_weights_self_hostable",
            "format": "provenance-record",
            "sentinel_path": rel,
            "sha256": sha,
        }
    ])
    code, out = _run(repo, monkeypatch)
    assert code == OK, out
    assert "prov-x: provenance-record OK" in out


def test_synthetic_provenance_record_hash_mismatch_fails(tmp_path, monkeypatch):
    repo = _make_synthetic_repo(tmp_path)
    rel = "orchestrator/inference_router/floor_provenance.txt"
    _write_blob(repo / rel, b"actual bytes\n")
    _write_manifest(repo, [
        {
            "id": "prov-x",
            "category": "open_weights_self_hostable",
            "format": "provenance-record",
            "sentinel_path": rel,
            "sha256": "b" * 64,
        }
    ])
    code, out = _run(repo, monkeypatch)
    assert code == FAIL, out
    assert "provenance-record sha256 mismatch" in out


# ---------------------------------------------------------------------------
# Model-blob format
# ---------------------------------------------------------------------------


def _model_blob_entry(sha: str, size: int, env_var: str = "XION_TEST_BLOB_PATH") -> dict:
    return {
        "id": "blob-x",
        "category": "open_weights_self_hostable",
        "format": "model-blob",
        "model_blob_env_var": env_var,
        "sha256": sha,
        "size_bytes": size,
        "retrieval_hints": [
            {
                "kind": "https",
                "url": "https://example.test/blob.gguf",
                "sha256": sha,
            }
        ],
    }


def test_synthetic_model_blob_env_var_unset_returns_not_yet_sealed(tmp_path, monkeypatch):
    repo = _make_synthetic_repo(tmp_path)
    payload = b"pretend this is a 5GB GGUF\n"
    sha = hashlib.sha256(payload).hexdigest()
    _write_manifest(repo, [_model_blob_entry(sha, len(payload))])
    monkeypatch.delenv("XION_TEST_BLOB_PATH", raising=False)
    code, out = _run(repo, monkeypatch)
    assert code == NOT_YET_SEALED, out
    assert "model-blob NOT_YET_SEALED" in out
    assert "XION_TEST_BLOB_PATH unset" in out


def test_synthetic_model_blob_env_var_points_at_missing_file_returns_not_yet_sealed(
    tmp_path, monkeypatch
):
    repo = _make_synthetic_repo(tmp_path)
    payload = b"x" * 17
    sha = hashlib.sha256(payload).hexdigest()
    _write_manifest(repo, [_model_blob_entry(sha, len(payload))])
    monkeypatch.setenv("XION_TEST_BLOB_PATH", str(tmp_path / "no-such-file.gguf"))
    code, out = _run(repo, monkeypatch)
    assert code == NOT_YET_SEALED, out
    assert "does not resolve to a regular file" in out


def test_synthetic_model_blob_present_matching_returns_ok(tmp_path, monkeypatch):
    repo = _make_synthetic_repo(tmp_path)
    payload = b"abc" * 1000
    sha = hashlib.sha256(payload).hexdigest()
    blob_path = tmp_path / "blob.gguf"
    blob_path.write_bytes(payload)
    _write_manifest(repo, [_model_blob_entry(sha, len(payload))])
    monkeypatch.setenv("XION_TEST_BLOB_PATH", str(blob_path))
    code, out = _run(repo, monkeypatch)
    assert code == OK, out
    assert "blob-x: model-blob OK" in out


def test_synthetic_model_blob_present_size_mismatch_fails(tmp_path, monkeypatch):
    repo = _make_synthetic_repo(tmp_path)
    payload = b"abc" * 1000
    sha = hashlib.sha256(payload).hexdigest()
    blob_path = tmp_path / "blob.gguf"
    blob_path.write_bytes(payload)
    _write_manifest(repo, [_model_blob_entry(sha, len(payload) + 1)])  # wrong size
    monkeypatch.setenv("XION_TEST_BLOB_PATH", str(blob_path))
    code, out = _run(repo, monkeypatch)
    assert code == FAIL, out
    assert "model-blob size mismatch" in out


def test_synthetic_model_blob_present_hash_mismatch_fails(tmp_path, monkeypatch):
    repo = _make_synthetic_repo(tmp_path)
    payload = b"abc" * 1000
    blob_path = tmp_path / "blob.gguf"
    blob_path.write_bytes(payload)
    bogus_sha = "0" * 64
    _write_manifest(repo, [_model_blob_entry(bogus_sha, len(payload))])
    monkeypatch.setenv("XION_TEST_BLOB_PATH", str(blob_path))
    code, out = _run(repo, monkeypatch)
    assert code == FAIL, out
    assert "model-blob sha256 mismatch" in out


def test_synthetic_model_blob_chunked_hashing_handles_multi_chunk_files(
    tmp_path, monkeypatch
):
    """The chunked reader must yield the same digest as a one-shot read."""
    repo = _make_synthetic_repo(tmp_path)
    chunk_size = 4 * 1024 * 1024
    payload = (b"X" * chunk_size) + (b"Y" * chunk_size) + (b"Z" * 12345)
    sha = hashlib.sha256(payload).hexdigest()
    blob_path = tmp_path / "blob.gguf"
    blob_path.write_bytes(payload)
    _write_manifest(repo, [_model_blob_entry(sha, len(payload))])
    monkeypatch.setenv("XION_TEST_BLOB_PATH", str(blob_path))
    code, out = _run(repo, monkeypatch)
    assert code == OK, out
    assert "blob-x: model-blob OK" in out


def test_synthetic_model_blob_missing_retrieval_hints_fails(tmp_path, monkeypatch):
    repo = _make_synthetic_repo(tmp_path)
    payload = b"data"
    sha = hashlib.sha256(payload).hexdigest()
    entry = _model_blob_entry(sha, len(payload))
    entry.pop("retrieval_hints")
    _write_manifest(repo, [entry])
    code, out = _run(repo, monkeypatch)
    assert code == FAIL, out
    assert "non-empty 'retrieval_hints' list" in out


def test_synthetic_model_blob_retrieval_hint_sha_disagrees_with_entry_fails(
    tmp_path, monkeypatch
):
    repo = _make_synthetic_repo(tmp_path)
    payload = b"data"
    sha = hashlib.sha256(payload).hexdigest()
    entry = _model_blob_entry(sha, len(payload))
    entry["retrieval_hints"][0]["sha256"] = "f" * 64
    _write_manifest(repo, [entry])
    code, out = _run(repo, monkeypatch)
    assert code == FAIL, out
    assert "disagrees with entry sha256" in out


def test_synthetic_model_blob_missing_env_var_field_fails(tmp_path, monkeypatch):
    repo = _make_synthetic_repo(tmp_path)
    payload = b"data"
    sha = hashlib.sha256(payload).hexdigest()
    entry = _model_blob_entry(sha, len(payload))
    entry.pop("model_blob_env_var")
    _write_manifest(repo, [entry])
    code, out = _run(repo, monkeypatch)
    assert code == FAIL, out
    assert "requires a 'model_blob_env_var'" in out


# ---------------------------------------------------------------------------
# Unknown-format dispatch
# ---------------------------------------------------------------------------


def test_synthetic_unknown_format_value_fails(tmp_path, monkeypatch):
    """Adding a new format must be a verifier change, not a manifest-only change."""
    repo = _make_synthetic_repo(tmp_path)
    _write_manifest(repo, [
        {
            "id": "wat",
            "category": "open_weights_self_hostable",
            "format": "future-novel-format",
            "sha256": "c" * 64,
        }
    ])
    code, out = _run(repo, monkeypatch)
    assert code == FAIL, out
    assert "unknown or missing 'format'" in out


def test_synthetic_no_floor_satisfying_entry_fails(tmp_path, monkeypatch):
    """At least one entry must have category open_weights_self_hostable."""
    repo = _make_synthetic_repo(tmp_path)
    _write_manifest(repo, [
        {
            "id": "nonfloor",
            "category": "hosted_api",
            "format": "sentinel",
            "sentinel_path": "x",
            "sha256": "d" * 64,
        }
    ])
    code, out = _run(repo, monkeypatch)
    assert code == FAIL, out
    assert "Invariant 17 floor unsatisfied" in out


# ---------------------------------------------------------------------------
# Mixed-entry manifest (the post-Phase-5g-viii shape)
# ---------------------------------------------------------------------------


def test_synthetic_mixed_manifest_one_blob_unsealed_one_sentinel_ok(tmp_path, monkeypatch):
    """A sentinel + an absent model-blob: overall verdict is NOT_YET_SEALED."""
    repo = _make_synthetic_repo(tmp_path)
    sentinel_rel = "orchestrator/inference_router/sentinel.txt"
    sha_sentinel = _write_blob(repo / sentinel_rel, b"sentinel bytes\n")
    payload = b"data"
    sha_blob = hashlib.sha256(payload).hexdigest()
    _write_manifest(repo, [
        {
            "id": "sent",
            "category": "open_weights_self_hostable",
            "format": "sentinel",
            "sentinel_path": sentinel_rel,
            "sha256": sha_sentinel,
        },
        _model_blob_entry(sha_blob, len(payload)),
    ])
    monkeypatch.delenv("XION_TEST_BLOB_PATH", raising=False)
    code, out = _run(repo, monkeypatch)
    assert code == NOT_YET_SEALED, out
    assert "sent: sentinel OK" in out
    assert "blob-x: model-blob NOT_YET_SEALED" in out
