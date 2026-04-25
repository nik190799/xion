from __future__ import annotations

import asyncio
from dataclasses import dataclass

from orchestrator.cognition.worker import CognitionWorker


@dataclass
class _Result:
    text: str


class _Provider:
    def generate(self, prompt: str, *, system: str | None, max_tokens: int, deadline_s: float) -> _Result:
        return _Result(text=f"candidate:{prompt}:{max_tokens}:{int(deadline_s)}")


class _UserContext:
    correlation_id = "cid-1"


def test_cognition_worker_returns_candidate() -> None:
    worker = CognitionWorker("worker-1", provider=_Provider(), soul_prompt="soul", max_tokens=7, deadline_s=3)

    candidate = asyncio.run(worker.run_turn(_UserContext(), "hello"))

    assert candidate.correlation_id == "cid-1"
    assert candidate.text == "candidate:hello:7:3"
