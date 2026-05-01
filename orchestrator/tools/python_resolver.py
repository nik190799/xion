"""In-process Python tool resolver for cognition."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from orchestrator.tools.resolver import ToolResult, ToolSpec

if TYPE_CHECKING:
    from orchestrator.cognition.journal import Journal


ToolFn = Callable[[dict[str, Any]], Any]


def _repo_root() -> Path:
    for base in [Path.cwd(), *Path.cwd().parents]:
        if (base / "genesis").is_dir() and (base / "xion-verify").is_dir():
            return base
    return Path.cwd()


@dataclass
class PythonToolResolver:
    resolver_id: str = "python-resolver"
    repo_root: Path = field(default_factory=_repo_root)
    journal: Journal | None = None

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="read_constitution",
                description="Read one constitutional document: covenant, invariants, soul, or unknowns.",
                input_schema={
                    "type": "object",
                    "properties": {"document": {"type": "string", "enum": ["covenant", "invariants", "soul", "unknowns"]}},
                    "required": ["document"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="query_journal",
                description="Retrieve relevant Journal memory for a query.",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "minimum": 1, "maximum": 20}},
                    "required": ["query"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="query_sensorium",
                description="Return the latest SENSORIUM_LEDGER row if present.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            ),
            ToolSpec(
                name="read_ledger",
                description="Read the last N rows of an allowlisted local ledger.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "ledger": {"type": "string", "enum": ["request", "payment", "safety", "sensorium", "billing", "shadow", "model_registry"]},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                    },
                    "required": ["ledger"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="run_verifier",
                description="Run an allowlisted xion-verify subcommand without arguments.",
                input_schema={
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                    "additionalProperties": False,
                },
            ),
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        fns: dict[str, ToolFn] = {
            "read_constitution": self._read_constitution,
            "query_journal": self._query_journal,
            "query_sensorium": self._query_sensorium,
            "read_ledger": self._read_ledger,
            "run_verifier": self._run_verifier,
        }
        fn = fns.get(name)
        if fn is None:
            return ToolResult(name=name, content=f"unknown tool: {name}", is_error=True)
        try:
            return ToolResult(name=name, content=fn(arguments))
        except Exception as exc:
            return ToolResult(name=name, content=str(exc), is_error=True)

    def _read_constitution(self, arguments: dict[str, Any]) -> dict[str, str]:
        rel = {
            "covenant": "genesis/COVENANT.md",
            "invariants": "genesis/INVARIANTS.md",
            "soul": "genesis/SOUL.md",
            "unknowns": "genesis/UNKNOWNS.md",
        }[str(arguments["document"])]
        path = self.repo_root / rel
        return {"path": rel, "text": path.read_text(encoding="utf-8") if path.is_file() else ""}

    def _query_journal(self, arguments: dict[str, Any]) -> list[str]:
        from orchestrator.cognition.retrieval import retrieve_context

        return retrieve_context(
            self._journal(),
            str(arguments["query"]),
            top_k=int(arguments.get("top_k") or 5),
        )

    def _journal(self) -> Journal:
        from orchestrator.cognition.journal import Journal

        if self.journal is None:
            self.journal = Journal(str(self.repo_root / "journal.db"))
        return self.journal

    def _query_sensorium(self, arguments: dict[str, Any]) -> dict[str, Any]:
        rows = self._read_jsonl_tail(self.repo_root / "ledgers" / "SENSORIUM_LEDGER.jsonl", 1)
        return rows[-1] if rows else {}

    def _read_ledger(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        paths = {
            "request": self.repo_root / "REQUEST_LEDGER.jsonl",
            "payment": self.repo_root / "PAYMENT_LEDGER.jsonl",
            "safety": self.repo_root / "SAFETY_LEDGER.jsonl",
            "sensorium": self.repo_root / "ledgers" / "SENSORIUM_LEDGER.jsonl",
            "billing": self.repo_root / "ledgers" / "BILLING_LEDGER.jsonl",
            "shadow": self.repo_root / "ledgers" / "SHADOW_LEDGER.jsonl",
            "model_registry": self.repo_root / "ledgers" / "MODEL_REGISTRY_LEDGER.jsonl",
        }
        path = paths[str(arguments["ledger"])]
        return self._read_jsonl_tail(path, int(arguments.get("limit") or 10))

    def _run_verifier(self, arguments: dict[str, Any]) -> dict[str, Any]:
        from xion_verify.commands import REGISTERED_COMMANDS

        command = str(arguments["command"])
        if command not in REGISTERED_COMMANDS:
            raise ValueError(f"verifier not allowlisted: {command}")
        proc = subprocess.run(
            [sys.executable, "-m", "xion_verify", command],
            cwd=str(self.repo_root / "xion-verify" / "src"),
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        return {"exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}

    @staticmethod
    def _read_jsonl_tail(path: Path, limit: int) -> list[dict[str, Any]]:
        if not path.is_file():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines()[-limit:]:
            if line.strip():
                rows.append(json.loads(line))
        return rows


__all__ = ["PythonToolResolver"]
