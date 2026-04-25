"""Audition / paralinguistic distress (Phase 6.5)."""

from orchestrator.senses.audition import (
    distress_from_transcript_text,
    estimate_metrics_from_transcript,
)
from orchestrator.sensorium.sensorium import DistressSignal


def test_paralinguistic_source_on_distress() -> None:
    d = distress_from_transcript_text("um... I... I can't anymore...")
    assert d.source == "paralinguistic"
    assert 0.0 <= d.text_distress_score <= 1.0


def test_calm_transcript_low_score() -> None:
    d = distress_from_transcript_text("This is a routine neutral sentence about weather.")
    assert d.text_distress_score < 0.5


def test_distress_signal_accepts_paralinguistic_literal() -> None:
    d = DistressSignal(text_distress_score=0.3, source="paralinguistic")
    assert d.source == "paralinguistic"


def test_metrics_from_empty() -> None:
    m = estimate_metrics_from_transcript("")
    assert 0.0 <= m.energy <= 1.0
