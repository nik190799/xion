"""Phase 5h/6.9: SQLite Journal plus embedding index hook."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from orchestrator.cognition.memory_adapter import ForgetScope
from orchestrator.embeddings import EmbeddingProvider, LocalBgeM3EmbeddingProvider
from orchestrator.memory import SQLiteVecMemoryStore

class Journal:
    def __init__(
        self,
        db_path: str = "journal.db",
        *,
        embedder: EmbeddingProvider | None = None,
        memory_store: SQLiteVecMemoryStore | None = None,
    ):
        self.db_path = db_path
        self.embedder = embedder or LocalBgeM3EmbeddingProvider()
        self.memory_store = memory_store or SQLiteVecMemoryStore()
        self.index_embeddings = os.environ.get("XION_JOURNAL_EMBEDDINGS", "true").strip().lower() not in {"0", "false", "no"}
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    correlation_id TEXT,
                    principal_id TEXT DEFAULT 'global',
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            columns = {row[1] for row in conn.execute("PRAGMA table_info(journal)").fetchall()}
            if "principal_id" not in columns:
                conn.execute("ALTER TABLE journal ADD COLUMN principal_id TEXT DEFAULT 'global'")
            
    def append(self, correlation_id: str, role: str, content: str, *, principal_id: str = "global") -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO journal (correlation_id, principal_id, role, content) VALUES (?, ?, ?, ?)",
                (correlation_id, principal_id, role, content)
            )
            row_id = int(cursor.lastrowid)
        if self.index_embeddings:
            batch = self.embedder.embed([content])
            self.memory_store.put(
                record_id=f"journal:{row_id}",
                principal_id=principal_id,
                scope=ForgetScope.USER,
                role=role,
                text=content,
                embedding=batch.vectors[0],
                embedder_id=batch.provider_fingerprint,
            )

    def get_recent(self, limit: int = 10) -> list[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT role, content FROM journal ORDER BY id DESC LIMIT ?", 
                (limit,)
            )
            rows = cursor.fetchall()
            return [f"{role}: {content}" for role, content in reversed(rows)]
            
    def search(self, keyword: str, limit: int = 5) -> list[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT role, content FROM journal WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{keyword}%", limit)
            )
            rows = cursor.fetchall()
            return [f"{role}: {content}" for role, content in reversed(rows)]

    def vector_search(self, query: str, *, top_k: int = 20, principal_id: str | None = None) -> list[tuple[str, float, str]]:
        batch = self.embedder.embed([query])
        return [
            (hit.text, hit.score, hit.record_id)
            for hit in self.memory_store.search(
                batch.vectors[0],
                top_k=top_k,
                principal_id=principal_id,
            )
        ]
