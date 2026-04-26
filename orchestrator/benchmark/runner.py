"""Hash-chained BENCHMARK_LEDGER writer and verifier.

The D2 benchmark is deliberately local and bounded. It records a small synthetic
suite so `xion-verify benchmark` can distinguish "no benchmark ever ran" from
"the benchmark surface is present and auditably shaped".
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

ZERO_HASH = "0" * 64
SCHEMA_VERSION = 1


def _canonical(row: dict[str, Any]) -> bytes:
    body = {key: value for key, value in row.items() if key != "this_hash"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _hash(row: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(row)).hexdigest()


def _iter_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def append_benchmark_row(path: Path, *, suite_id: str, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    rows = _iter_rows(path)
    seq = len(rows)
    row = {
        "schema_version": SCHEMA_VERSION,
        "seq": seq,
        "prev_hash": rows[-1]["this_hash"] if rows else ZERO_HASH,
        "this_hash": "",
        "as_of_utc_ns": time.time_ns(),
        "suite_id": suite_id,
        "task_count": len(tasks),
        "tasks": tasks,
        "p95_latency_ms": max((int(task.get("latency_ms", 0)) for task in tasks), default=0),
        "mean_score": (
            sum(float(task.get("score", 0.0)) for task in tasks) / len(tasks)
            if tasks
            else 0.0
        ),
    }
    row["this_hash"] = _hash(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    return row


def verify_benchmark_chain(path: Path) -> tuple[int, str]:
    rows = _iter_rows(path)
    if not rows:
        return 0, ZERO_HASH
    prev = ZERO_HASH
    for expected_seq, row in enumerate(rows):
        if row.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"row {expected_seq}: schema_version must be {SCHEMA_VERSION}")
        if row.get("seq") != expected_seq:
            raise ValueError(f"row {expected_seq}: bad seq")
        if row.get("prev_hash") != prev:
            raise ValueError(f"row {expected_seq}: prev_hash mismatch")
        if row.get("this_hash") != _hash(row):
            raise ValueError(f"row {expected_seq}: this_hash mismatch")
        if not isinstance(row.get("tasks"), list) or row.get("task_count") != len(row["tasks"]):
            raise ValueError(f"row {expected_seq}: task_count mismatch")
        prev = row["this_hash"]
    return len(rows), prev
