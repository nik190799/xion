"""Audition — paralinguistic sense (Phase 6.5).

Consumes STT text or future raw audio features and produces a distress score
for `DistressSignal` with ``source=\"paralinguistic\"``. The long-term path is
direct features from the floor STT stream; until then, lightweight heuristics
on transcript text establish the structural join to Principle 10.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from orchestrator.sensorium.sensorium import DistressSignal


@dataclass(frozen=True)
class ProsodyMetrics:
    """Scalar stand-in for pitch/energy/pause structure from STT."""

    energy: float
    """Normalized [0, 1]. Low = flat / exhausted delivery."""
    pause_rate: float
    """Normalized [0, 1]. High = frequent pauses / hesitation."""


_PAUSE_RE = re.compile(r"(\.{2,}|…|,\s*,|um\.{0,3}|uh\.{0,3})", re.IGNORECASE)


def estimate_metrics_from_transcript(text: str) -> ProsodyMetrics:
    """Derive coarse metrics from transcript when raw audio is unavailable."""
    t = text or ""
    if not t.strip():
        return ProsodyMetrics(energy=0.5, pause_rate=0.0)
    pause_hits = len(_PAUSE_RE.findall(t))
    pause_rate = min(1.0, pause_hits / 5.0)
    # Short, clipped lines read as lower energy in the stub model.
    words = max(1, len(t.split()))
    energy = max(0.0, min(1.0, 1.0 - (words < 6) * 0.15))
    return ProsodyMetrics(energy=energy, pause_rate=pause_rate)


def distress_from_prosody(metrics: ProsodyMetrics) -> DistressSignal:
    """Map prosody metrics to a paralinguistic DistressSignal (Principle 10)."""
    # High pause + low energy => elevated score; bounded [0,1].
    score = min(
        1.0,
        0.45 * (1.0 - metrics.energy) + 0.55 * metrics.pause_rate,
    )
    return DistressSignal(text_distress_score=score, source="paralinguistic")


def distress_from_transcript_text(text: str) -> DistressSignal:
    """Convenience: transcript → metrics → paralinguistic distress."""
    return distress_from_prosody(estimate_metrics_from_transcript(text))
