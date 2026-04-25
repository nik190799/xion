"""Floor provider: Whisper + Piper + LiveKit (Phase 6.5).

The no-extra-dependency path emits a deterministic voice-frame payload for CI
and local development. Operators can set ``XION_VOICE_FLOOR_INTEGRATION=1`` to
require the local LiveKit / Whisper / Piper command surfaces to be configured.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Any

from orchestrator.voice_router.router import VoiceCategory


@dataclass
class WhisperPiperLiveKitProvider:
    """Open-source self-hostable voice floor.

    The public methods are deliberately text/JSON shaped. The browser-facing
    endpoint can exercise STT->policy->TTS wiring in CI without shipping binary
    audio fixtures; a production operator maps the returned voice frame to a
    LiveKit room and Piper audio stream.
    """

    provider_id: str = "whisper-piper-livekit-floor"
    category: VoiceCategory = "voice_open_source_self_hostable"
    whisper_command: str = "whisper"
    piper_command: str = "piper"
    livekit_url_env: str = "XION_LIVEKIT_URL"

    def health(self) -> bool:
        """True when the floor is operable for the configured posture."""
        if os.environ.get("XION_VOICE_FLOOR_INTEGRATION", "").strip() in (
            "0",
            "",
        ):
            return True

        return (
            shutil.which(self.whisper_command) is not None
            and shutil.which(self.piper_command) is not None
            and bool(os.environ.get(self.livekit_url_env, "").strip())
        )

    def transcribe(self, *, transcript_text: str | None = None) -> str:
        """Return caller-supplied STT text for the current text-first floor.

        Raw audio ingestion is intentionally not faked. Until the browser
        uploads real audio chunks, the voice endpoint accepts a transcript
        produced by client-side or operator-local STT.
        """
        text = (transcript_text or "").strip()
        if not text:
            raise ValueError("voice floor requires transcript_text until raw-audio STT is wired")
        return text

    def synthesize_frame(
        self,
        *,
        text: str,
        prosody_frame: dict[str, Any],
        livekit_room: str | None = None,
    ) -> dict[str, Any]:
        """Return a TTS-ready frame for LiveKit/Piper front-ends."""
        return {
            "provider_id": self.provider_id,
            "audio_format": "xion.voice_frame.v1",
            "text": text,
            "prosody": prosody_frame,
            "transport": {
                "kind": "livekit",
                "room": livekit_room,
                "url": os.environ.get(self.livekit_url_env, "").strip() or None,
            },
        }
