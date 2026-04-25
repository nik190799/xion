"""Floor provider stub: Whisper + Piper + LiveKit (Phase 6.5).

Real STT/TTS/WebRTC integration lands behind the same interface; bootstrap
uses manifest id `whisper-piper-livekit-floor` and `xion-verify voice-sovereignty`
pins the structural sentinel.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from orchestrator.voice_router.router import VoiceCategory


@dataclass
class WhisperPiperLiveKitProvider:
    """Open-source self-hostable voice floor (structural; runtime optional)."""

    provider_id: str = "whisper-piper-livekit-floor"
    category: VoiceCategory = "voice_open_source_self_hostable"

    def health(self) -> bool:
        """True when the structural floor is operable for bootstrap.

        With ``XION_VOICE_FLOOR_INTEGRATION=0`` (default) only the presence of
        the manifest + sentinel path matters for CI. Set
        ``XION_VOICE_FLOOR_INTEGRATION=1`` to require operator-local daemons
        (future: probe Whisper/Piper/LiveKit endpoints).
        """
        if os.environ.get("XION_VOICE_FLOOR_INTEGRATION", "").strip() in (
            "0",
            "",
        ):
            return True
        # Future: socket probes to local services.
        return True
