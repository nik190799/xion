"""Phase 5h: The Cognition Wiring - SQLite Journal."""
import sqlite3
import json
from typing import Any
from pathlib import Path

class Journal:
    def __init__(self, db_path: str = "journal.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    correlation_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
    def append(self, correlation_id: str, role: str, content: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO journal (correlation_id, role, content) VALUES (?, ?, ?)",
                (correlation_id, role, content)
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
