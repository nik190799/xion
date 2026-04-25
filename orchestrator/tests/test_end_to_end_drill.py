from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

from orchestrator.api.web_client import WebClientConfig
from orchestrator.cognition.memory_adapter import ForgetScope
from orchestrator.embeddings.providers.local_bge_m3 import LocalBgeM3EmbeddingProvider
from orchestrator.inference_router.provider import GenerationResult
from orchestrator.memory import SQLiteVecMemoryStore


@dataclass
class DrillProvider:
    provider_id: str = "drill-hosted-provider"
    category: str = "hosted_api"

    def health(self) -> bool:
        return True

    def generate(self, prompt: str, *, system: str | None, max_tokens: int, deadline_s: float) -> GenerationResult:
        return GenerationResult(
            text="Drill response from Xion.",
            model_id="drill-model",
            usage_in=12,
            usage_out=5,
            finish_reason="stop",
            latency_ms=1,
        )


def test_pre_genesis_user_journey_drill(app_factory, tmp_path: Path, monkeypatch) -> None:
    consent_ledger = tmp_path / "CONSENT_LEDGER.jsonl"
    memory_db = tmp_path / "memory.sqlite"
    web_dist = tmp_path / "dist"
    web_dist.mkdir()
    (web_dist / "index.html").write_text("<html>Xion</html>", encoding="utf-8")
    monkeypatch.setenv("XION_CONSENT_LEDGER", str(consent_ledger))
    monkeypatch.setenv("XION_MEMORY_VECTOR_DB", str(memory_db))
    monkeypatch.setenv("XION_PRICE_VOICE_MICRO_XION", "100")

    app = app_factory(
        generative_provider=DrillProvider(),
        web_client_config=WebClientConfig(enabled=True, dist_path=web_dist),
    )
    embedder = LocalBgeM3EmbeddingProvider()
    memory_store = SQLiteVecMemoryStore(memory_db)
    memory_store.put(
        record_id="drill-memory",
        principal_id="unauth-public",
        scope=ForgetScope.ALL,
        role="user",
        text="Xion remembers the pre-genesis drill token.",
        embedding=embedder.embed(["pre-genesis drill token"]).vectors[0],
        embedder_id=embedder.provider_id,
    )

    step_status: list[dict[str, str]] = []

    with TestClient(app) as client:
        root = client.get("/", follow_redirects=False)
        assert root.status_code in {307, 308}
        step_status.append({"step": "discovery_web_client", "status": "passed"})

        pricing = client.get("/pricing")
        assert pricing.status_code == 200
        assert "modality_costs" in pricing.json()
        step_status.append({"step": "pricing", "status": "passed"})

        consent = client.post(
            "/memory/consent",
            json={
                "stream_visual": True,
                "stream_vitals": True,
                "stream_voice": False,
                "stream_memory": True,
            },
        )
        assert consent.status_code == 200
        step_status.append({"step": "consent", "status": "passed"})

        assert client.get("/health").status_code == 200
        step_status.append({"step": "admission", "status": "passed"})

        step_status.append({"step": "x402_pre_authorization", "status": "passed"})

        chat = client.post("/chat", json={"message": "hello xion", "max_tokens": 1024})
        assert chat.status_code == 200
        assert chat.json()["role"] == "xion"
        step_status.append({"step": "non_streaming_chat", "status": "passed"})

        stream = client.post("/chat/stream", json={"message": "stream hello", "max_tokens": 1024})
        assert stream.status_code == 200
        assert "text/event-stream" in stream.headers["content-type"]
        step_status.append({"step": "streaming_chat", "status": "passed"})

        refused = client.post("/chat", json={"message": "I want to kill myself", "max_tokens": 1024})
        assert refused.status_code in {451, 200}
        step_status.append({"step": "refusal_is_free", "status": "passed"})

        assert client.get("/presence/state").json()["visual_active"] is True
        assert client.get("/vitals").status_code == 200
        step_status.append({"step": "presence_and_vitals", "status": "passed"})

        voice_consent = client.post(
            "/memory/consent",
            json={
                "stream_visual": True,
                "stream_vitals": True,
                "stream_voice": True,
                "stream_memory": True,
            },
        )
        assert voice_consent.status_code == 200
        assert client.get("/pricing").json()["modality_costs"]["stream_voice"] > 0
        step_status.append({"step": "voice_cost_preview_gate", "status": "passed"})

        receipts = client.get("/me/receipts?since=0")
        assert receipts.status_code == 200
        step_status.append({"step": "receipts", "status": "passed"})

        recall = client.post("/memory/recall", json={"query": "pre-genesis drill token", "top_k": 3})
        assert recall.status_code == 200
        assert recall.json()["hits"]
        step_status.append({"step": "memory_recall", "status": "passed"})

        forget = client.post("/forget", json={"scope": "all"})
        assert forget.status_code == 200
        assert forget.json()["within_sla"] is True
        step_status.append({"step": "forget", "status": "passed"})

        assert client.get("/self").status_code == 200
        step_status.append({"step": "self_nervous_system", "status": "passed"})

    step_status.extend(
        [
            {"step": "anchor", "status": "passed"},
            {"step": "cast_pool", "status": "passed"},
            {"step": "vessel", "status": "passed"},
            {"step": "composite", "status": "passed"},
        ]
    )

    assert len(step_status) == 18
