"""Voice Router (Invariant 18) — bootstrap and manifest wiring."""

from pathlib import Path

import pytest

from orchestrator.voice_router import (
    VoiceFloorStub,
    WhisperPiperLiveKitProvider,
    load_voice_router,
)
from orchestrator.voice_router.router import VoiceRouter


def test_bootstrap_succeeds_with_stub_register() -> None:
    r = load_voice_router(
        providers=[VoiceFloorStub(provider_id="whisper-piper-livekit-floor")],
    )
    r.bootstrap()
    assert r.bootstrapped
    p = r.select_floor()
    assert p is not None
    assert p.provider_id == "whisper-piper-livekit-floor"


def test_bootstrap_fails_without_floor() -> None:
    r = VoiceRouter(manifest_path=Path(__file__).resolve().parents[1] / "voice_router" / "voice_open_source_manifest.json")
    with pytest.raises(RuntimeError, match="Invariant 18"):
        r.bootstrap()


def test_whisper_piper_provider_registers() -> None:
    w = WhisperPiperLiveKitProvider()
    r = load_voice_router(providers=[w])
    r.bootstrap()
    assert r.select_floor() is w
