"""Verify vector memory store integrity and forget semantics."""

from __future__ import annotations

import gc
import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK


@click.command(name="memory-store-integrity")
def memory_store_integrity() -> None:
    try:
        from orchestrator.cognition.memory_adapter import ForgetScope
        from orchestrator.embeddings import LocalBgeM3EmbeddingProvider
        from orchestrator.memory import SQLiteVecMemoryStore

        db = Path("memory_store_integrity.tmp.db")
        try:
            if db.exists():
                db.unlink()
            store = SQLiteVecMemoryStore(db)
            embedder = LocalBgeM3EmbeddingProvider()
            vector = embedder.embed(["private journal item about apples"]).vectors[0]
            store.put(
                record_id="test:1",
                principal_id="principal-a",
                scope=ForgetScope.USER,
                role="user",
                text="private journal item about apples",
                embedding=vector,
                embedder_id=embedder.provider_id,
            )
            hits = store.search(vector, top_k=1, principal_id="principal-a")
            if not hits or hits[0].record_id != "test:1":
                raise RuntimeError("inserted vector was not searchable")
            deleted = store.forget("principal-a", ForgetScope.ALL)
            if deleted != 1 or store.pending_count("principal-a", ForgetScope.ALL) != 0:
                raise RuntimeError("forget did not remove embedded record")
        finally:
            store = None
            gc.collect()
            if db.exists():
                db.unlink()
    except Exception as exc:
        click.echo(f"memory-store-integrity: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    click.echo("memory-store-integrity: OK (sqlite vector store + forget)")
    sys.exit(OK)


__all__ = ["memory_store_integrity"]
