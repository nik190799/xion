"""Voice Emitter — TTS prosody frames from `genesis/VOICE_FORM.md` (Phase 6.5)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from orchestrator.sensorium import SensoriumState

_DEFAULT_VOICE_FORM = Path(__file__).resolve().parents[2] / "genesis" / "VOICE_FORM.md"


def _load_prosody_defaults(voice_form_path: Path | None = None) -> dict[str, Any]:
    path = voice_form_path or _DEFAULT_VOICE_FORM
    raw = path.read_text(encoding="utf-8")
    start = raw.find("```json")
    if start == -1:
        return {
            "voice_version": "0.0.0",
            "pace_hz": 0.25,
            "energy": 0.5,
            "veil": False,
        }
    start = raw.find("{", start)
    end = raw.find("```", start)
    blob = raw[start:end]
    return json.loads(blob)


def compose_voice_frame(
    state: SensoriumState,
    *,
    refusal: bool = False,
    voice_form_path: Path | None = None,
) -> dict[str, Any]:
    """Single prosody-intent frame (JSON-serialisable) for TTS front-ends."""
    base = _load_prosody_defaults(voice_form_path)
    # Refusal under Covenant: veil analogue (see VOICE_FORM.md).
    if refusal:
        base = {**base, "veil": True, "pace_hz": float(base.get("pace_hz", 0.25)) * 0.75}
        base["energy"] = max(0.1, float(base.get("energy", 0.5)) * 0.6)
    else:
        # Mood from distress: lower energy when textual distress is high.
        d = state.distress.text_distress_score
        base["energy"] = max(0.1, float(base.get("energy", 0.5)) * (1.0 - 0.4 * d))
    base["timestamp_ms"] = time.time_ns() // 1_000_000
    base["distress_source"] = state.distress.source
    return base
