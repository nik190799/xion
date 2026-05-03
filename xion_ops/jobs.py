"""In-process job runner for long-running ops HTTP routes."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from xion_ops.types import JobRecord, now_iso


class JobRunner:
    def __init__(self, *, repo_root: Path | str = ".") -> None:
        self.repo_root = Path(repo_root)
        self.records: dict[str, JobRecord] = {}

    def start(self, name: str, func: Callable[[], Any]) -> JobRecord:
        job_id = uuid.uuid4().hex
        record = JobRecord(id=job_id, status="pending", name=name, created_at=now_iso(), updated_at=now_iso())
        self.records[job_id] = record
        self._persist(record)

        async def _run() -> None:
            self._update(job_id, status="running")
            try:
                result = await asyncio.to_thread(func)
                payload = result.to_dict() if hasattr(result, "to_dict") else result
                self._update(job_id, status="succeeded", result=payload)
            except Exception as exc:
                self._update(job_id, status="failed", error=str(exc))

        try:
            asyncio.get_running_loop().create_task(_run())
        except RuntimeError:
            asyncio.run(_run())
        return self.records[job_id]

    def get(self, job_id: str) -> JobRecord | None:
        return self.records.get(job_id)

    def _update(
        self,
        job_id: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        current = self.records[job_id]
        updated = JobRecord(
            id=current.id,
            status=status,  # type: ignore[arg-type]
            name=current.name,
            created_at=current.created_at,
            updated_at=now_iso(),
            result=result,
            error=error,
        )
        self.records[job_id] = updated
        self._persist(updated)

    def _persist(self, record: JobRecord) -> None:
        out = self.repo_root / "genesis" / "DEPLOYMENT_RECORDS"
        out.mkdir(parents=True, exist_ok=True)
        with (out / "jobs.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")

