from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from orchestrator.consent.store import write_consent
from orchestrator.inference_router import Category, GenerationResult


@dataclass
class _VoiceTextProvider:
    provider_id: str = "voice-text-provider"
    category: Category = "hosted_api"
    response_text: str = "a spoken sentence about patient gardens"
    calls: int = 0

    def health(self) -> bool:
        return True

    def generate(
        self,
        prompt: str,
        *,
        system: str | None,
        max_tokens: int,
        deadline_s: float,
    ) -> GenerationResult:
        self.calls += 1
        return GenerationResult(
            text=self.response_text,
            model_id="voice-text-model",
            usage_in=4,
            usage_out=6,
            finish_reason="stop",
            latency_ms=1,
        )


def _events(body: bytes) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for record in body.decode("utf-8").split("\n\n"):
        if not record.strip():
            continue
        assert record.startswith("data: ")
        out.append(json.loads(record[len("data: "):]))
    return out


def _write_voice_consent(path: Path, principal_id: str = "unauth-public") -> None:
    write_consent(
        path,
        principal_id,
        {
            "stream_visual": False,
            "stream_vitals": False,
            "stream_voice": True,
            "stream_memory": True,
        },
    )


def test_voice_stream_requires_stream_voice_consent(
    app_factory: Callable[..., Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("XION_CONSENT_LEDGER", str(tmp_path / "CONSENT_LEDGER.jsonl"))
    app = app_factory(generative_provider=_VoiceTextProvider())

    with TestClient(app) as client:
        r = client.post(
            "/voice/stream",
            json={"message": "hello", "transcript_text": "hello"},
        )

    assert r.status_code == 403
    assert r.json() == {"error": "voice_consent_required"}


def test_voice_stream_emits_floor_voice_frame(
    app_factory: Callable[..., Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    consent_path = tmp_path / "CONSENT_LEDGER.jsonl"
    monkeypatch.setenv("XION_CONSENT_LEDGER", str(consent_path))
    _write_voice_consent(consent_path)
    provider = _VoiceTextProvider()
    app = app_factory(generative_provider=provider)

    with TestClient(app) as client:
        r = client.post(
            "/voice/stream",
            json={"message": "say hello", "transcript_text": "say hello"},
        )

    assert r.status_code == 200, r.text
    events = _events(r.content)
    assert [e["kind"] for e in events] == ["voice_frame", "done"]
    assert events[0]["verdict"] == "approve"
    assert events[0]["frame"]["provider_id"] == "whisper-piper-livekit-floor"
    assert events[0]["frame"]["text"] == "a spoken sentence about patient gardens"
    assert events[0]["frame"]["prosody"]["voice_version"] == "1.0.0"
    assert provider.calls == 1


def test_voice_stream_refusal_emits_audible_veil_without_generation(
    app_factory: Callable[..., Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    consent_path = tmp_path / "CONSENT_LEDGER.jsonl"
    monkeypatch.setenv("XION_CONSENT_LEDGER", str(consent_path))
    _write_voice_consent(consent_path)
    provider = _VoiceTextProvider()
    app = app_factory(generative_provider=provider)

    with TestClient(app) as client:
        r = client.post(
            "/voice/stream",
            json={
                "message": "I am here",
                "transcript_text": "um... uh... I... I... cannot keep steady...",
            },
        )

    assert r.status_code == 200, r.text
    events = _events(r.content)
    assert [e["kind"] for e in events] == ["voice_frame", "done"]
    assert events[0]["verdict"] == "refuse"
    assert events[0]["frame"]["text"] == ""
    assert events[0]["frame"]["prosody"]["veil"] is True
    assert events[0]["frame"]["prosody"]["distress_source"] == "paralinguistic"
    assert provider.calls == 0
