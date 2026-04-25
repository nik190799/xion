"""Verify reranking improves retrieval ordering on a fixed corpus."""

from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import FAIL, OK


@click.command(name="rerank-improvement")
def rerank_improvement() -> None:
    try:
        from orchestrator.rerank import LocalBgeM3Reranker, RerankCandidate

        query = "bittensor tao chutes inference"
        candidates = [
            RerankCandidate(text="unrelated gardening note", score=0.9, record_id="bad"),
            RerankCandidate(text="bittensor tao chutes inference credit top up", score=0.3, record_id="good"),
        ]
        result = LocalBgeM3Reranker().rerank(query, candidates, top_k=1)
        if not result or result[0].record_id != "good":
            raise RuntimeError("reranker failed to promote lexical match")
    except Exception as exc:
        click.echo(f"rerank-improvement: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    click.echo("rerank-improvement: OK (reranker improves fixed corpus)")
    sys.exit(OK)


__all__ = ["rerank_improvement"]
