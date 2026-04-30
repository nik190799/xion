from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from orchestrator.cognition.memory_adapter import ForgetScope
from orchestrator.embeddings.providers.local_bge_m3 import LocalBgeM3EmbeddingProvider
from orchestrator.memory.store import SQLiteVecMemoryStore


@dataclass(frozen=True)
class CalibrationResult:
    corpus_sha256: str
    provider_fingerprint: str
    model_id: str
    query_count: int
    recall_at_1: float
    recall_at_3: float
    mean_reciprocal_rank: float
    thresholds: dict[str, float]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"


DEFAULT_THRESHOLDS = {
    "recall_at_1": 0.8,
    "recall_at_3": 1.0,
    "mean_reciprocal_rank": 0.8,
}


def run_calibration(corpus_path: Path, *, thresholds: dict[str, float] | None = None) -> CalibrationResult:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    records = corpus["records"]
    queries = corpus["queries"]
    provider = LocalBgeM3EmbeddingProvider()
    thresholds = thresholds or DEFAULT_THRESHOLDS

    with tempfile.TemporaryDirectory(prefix="xion-embed-calibration-", ignore_cleanup_errors=True) as tmp:
        store = SQLiteVecMemoryStore(Path(tmp) / "vectors.sqlite3")
        record_vectors = provider.embed([record["text"] for record in records])
        for record, vector in zip(records, record_vectors.vectors, strict=True):
            store.put(
                record_id=record["id"],
                principal_id="global",
                scope=ForgetScope.COLLECTION,
                role="corpus",
                text=record["text"],
                embedding=vector,
                embedder_id=record_vectors.provider_fingerprint,
            )

        reciprocal_ranks: list[float] = []
        hits_at_1 = 0
        hits_at_3 = 0
        for query in queries:
            vector = provider.embed([query["query"]]).vectors[0]
            hits = store.search(vector, top_k=3, principal_id="global")
            ranked_ids = [hit.record_id for hit in hits]
            expected = query["expected_record_id"]
            if ranked_ids[:1] == [expected]:
                hits_at_1 += 1
            if expected in ranked_ids:
                hits_at_3 += 1
                reciprocal_ranks.append(1.0 / (ranked_ids.index(expected) + 1))
            else:
                reciprocal_ranks.append(0.0)

    query_count = len(queries)
    return CalibrationResult(
        corpus_sha256=_sha256(corpus_path),
        provider_fingerprint=record_vectors.provider_fingerprint,
        model_id=record_vectors.model_id,
        query_count=query_count,
        recall_at_1=hits_at_1 / query_count,
        recall_at_3=hits_at_3 / query_count,
        mean_reciprocal_rank=sum(reciprocal_ranks) / query_count,
        thresholds=dict(thresholds),
    )


def assert_thresholds(result: CalibrationResult) -> list[str]:
    errors: list[str] = []
    for metric, floor in result.thresholds.items():
        value = getattr(result, metric)
        if value < floor:
            errors.append(f"{metric} below floor: {value:.3f} < {floor:.3f}")
    return errors


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Xion embedding corpus calibration.")
    parser.add_argument("--corpus", default="docs/calibration/embed-corpus.json")
    parser.add_argument("--write-report", default="docs/calibration/embed-calibration-report.json")
    args = parser.parse_args(argv)

    result = run_calibration(Path(args.corpus))
    errors = assert_thresholds(result)
    if errors:
        for error in errors:
            print(f"embed-calibration: FAIL: {error}")
        return 1
    out = Path(args.write_report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.to_json(), encoding="utf-8")
    print(f"embed-calibration: OK ({result.query_count} queries, recall@3={result.recall_at_3:.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["CalibrationResult", "assert_thresholds", "run_calibration"]
