"""SQLite vector memory store with Journal back-compat."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from orchestrator.cognition.memory_adapter import ForgetScope


@dataclass(frozen=True)
class MemoryHit:
    record_id: str
    text: str
    score: float
    principal_id: str
    scope: ForgetScope


class SQLiteVecMemoryStore:
    """Dependency-free sqlite-vec-shaped store.

    The table schema keeps vectors in SQLite and exposes a cosine search API.
    If the sqlite-vec extension is later enabled, this class is the swap point.
    """

    backend_id = "sqlite-vec-memory"

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or os.environ.get("XION_MEMORY_VECTOR_DB", "journal_vectors.db"))
        self._init_db()

    def _init_db(self) -> None:
        parent = self.db_path.parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_vectors (
                    record_id TEXT PRIMARY KEY,
                    principal_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    role TEXT NOT NULL,
                    text TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    embedder_id TEXT NOT NULL,
                    created_utc_s INTEGER DEFAULT (strftime('%s','now'))
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_vectors_principal_scope ON memory_vectors(principal_id, scope)")

    def put(
        self,
        *,
        record_id: str,
        principal_id: str,
        scope: ForgetScope,
        role: str,
        text: str,
        embedding: list[float],
        embedder_id: str,
    ) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_vectors
                (record_id, principal_id, scope, role, text, embedding_json, embedder_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    principal_id,
                    scope.value,
                    role,
                    text,
                    json.dumps(embedding, separators=(",", ":")),
                    embedder_id,
                ),
            )

    def search(self, embedding: list[float], *, top_k: int = 20, principal_id: str | None = None) -> list[MemoryHit]:
        query_norm = _norm(embedding)
        hits: list[MemoryHit] = []
        sql = "SELECT record_id, principal_id, scope, role, text, embedding_json FROM memory_vectors"
        params: tuple[str, ...] = ()
        if principal_id is not None:
            sql += " WHERE principal_id IN (?, ?)"
            params = (principal_id, "global")
        with sqlite3.connect(str(self.db_path)) as conn:
            for record_id, pid, scope, role, text, raw_vec in conn.execute(sql, params):
                vec = [float(v) for v in json.loads(raw_vec)]
                score = _cosine(embedding, query_norm, vec)
                hits.append(
                    MemoryHit(
                        record_id=str(record_id),
                        text=f"{role}: {text}",
                        score=score,
                        principal_id=str(pid),
                        scope=ForgetScope(scope),
                    )
                )
        return sorted(hits, key=lambda h: h.score, reverse=True)[:top_k]

    def forget(self, principal_id: str, scope: ForgetScope) -> int:
        scopes = _scopes_for(scope)
        with sqlite3.connect(str(self.db_path)) as conn:
            before = conn.total_changes
            conn.execute(
                f"DELETE FROM memory_vectors WHERE principal_id = ? AND scope IN ({','.join('?' for _ in scopes)})",
                (principal_id, *(s.value for s in scopes)),
            )
            return conn.total_changes - before

    def pending_count(self, principal_id: str, scope: ForgetScope) -> int:
        scopes = _scopes_for(scope)
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                f"SELECT COUNT(*) FROM memory_vectors WHERE principal_id = ? AND scope IN ({','.join('?' for _ in scopes)})",
                (principal_id, *(s.value for s in scopes)),
            ).fetchone()
        return int(row[0] if row else 0)


def _scopes_for(scope: ForgetScope) -> tuple[ForgetScope, ...]:
    if scope == ForgetScope.ALL:
        return (ForgetScope.USER, ForgetScope.SESSION, ForgetScope.COLLECTION, ForgetScope.EPHEMERAL)
    return (scope,)


def _norm(vector: list[float]) -> float:
    return sum(v * v for v in vector) ** 0.5


def _cosine(query: list[float], query_norm: float, vector: list[float]) -> float:
    denom = query_norm * _norm(vector)
    if denom <= 0:
        return 0.0
    return sum(a * b for a, b in zip(query, vector, strict=False)) / denom


def build_default_memory_store() -> SQLiteVecMemoryStore:
    return SQLiteVecMemoryStore()


__all__ = ["MemoryHit", "SQLiteVecMemoryStore", "build_default_memory_store"]
