"""Verify embedding providers can produce stable vectors."""

from __future__ import annotations

import json
import sys

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(name="embedder-health")
def embedder_health() -> None:
    try:
        from orchestrator.cognition.embed_calibration import assert_thresholds, run_calibration
        from orchestrator.embeddings import LocalBgeM3EmbeddingProvider

        provider = LocalBgeM3EmbeddingProvider()
        batch = provider.embed(["xion covenant memory retrieval", "xion covenant memory retrieval"])
        if not provider.health() or len(batch.vectors) != 2:
            raise RuntimeError("local embedder did not return two vectors")
        if batch.vectors[0] != batch.vectors[1]:
            raise RuntimeError("local embedder is not deterministic")
        if not batch.provider_fingerprint or "bge-m3" not in batch.model_id.lower():
            raise RuntimeError("local embedder fingerprint/model is not pinned")
        repo_root = find_repo_root()
        report_path = repo_root / "docs" / "calibration" / "embed-calibration-report.json"
        corpus_path = repo_root / "docs" / "calibration" / "embed-corpus.json"
        if not report_path.is_file():
            raise RuntimeError("missing docs/calibration/embed-calibration-report.json")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        result = run_calibration(corpus_path, thresholds=report.get("thresholds"))
        if result.corpus_sha256 != report.get("corpus_sha256"):
            raise RuntimeError("embedding calibration corpus hash changed; regenerate report")
        errors = assert_thresholds(result)
        if errors:
            raise RuntimeError("; ".join(errors))
    except RepoRootNotFound as exc:
        click.echo(f"embedder-health: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    except Exception as exc:
        click.echo(f"embedder-health: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    click.echo("embedder-health: OK (local BGE-M3 embedder healthy; calibration floors met)")
    sys.exit(OK)


__all__ = ["embedder_health"]
