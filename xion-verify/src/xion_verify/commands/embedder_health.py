"""Verify embedding providers can produce stable vectors."""

from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import FAIL, OK


@click.command(name="embedder-health")
def embedder_health() -> None:
    try:
        from orchestrator.embeddings import LocalBgeM3EmbeddingProvider

        provider = LocalBgeM3EmbeddingProvider()
        batch = provider.embed(["xion covenant memory retrieval", "xion covenant memory retrieval"])
        if not provider.health() or len(batch.vectors) != 2:
            raise RuntimeError("local embedder did not return two vectors")
        if batch.vectors[0] != batch.vectors[1]:
            raise RuntimeError("local embedder is not deterministic")
        if not batch.provider_fingerprint or "bge-m3" not in batch.model_id.lower():
            raise RuntimeError("local embedder fingerprint/model is not pinned")
    except Exception as exc:
        click.echo(f"embedder-health: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    click.echo("embedder-health: OK (local BGE-M3 embedder healthy)")
    sys.exit(OK)


__all__ = ["embedder_health"]
