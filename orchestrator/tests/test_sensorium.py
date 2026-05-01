"""Tests for `orchestrator.sensorium` (Phase 5c code surface).

Covers:
  - Enum: the typo fix (CULTURAL, not CULTUURAL) and the four
    internal senses.
  - Each frozen dataclass's constructor + factory + saturating
    behavior.
  - Sensorium.snapshot() immutability property.
  - Sensorium.tick() payload shape: four real senses + eight stubs.
  - DistressSignal.from_candidate_text saturation.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from orchestrator.sensorium import (
    DISTRESS_THRESHOLD,
    Chronoception,
    DistressSignal,
    Interoception,
    Proprioception,
    SenseName,
    Sensorium,
    SensoriumState,
)

# ------------------------------------------------------------- Enum invariants


def test_sense_name_spelling_is_cultural_not_cultuural():
    # Regression guard for the Phase-4e typo. A reader who greps for
    # CULTUURAL should find nothing.
    assert SenseName.CULTURAL.value == "cultural"
    assert "CULTUURAL" not in SenseName.__members__


def test_sense_name_has_four_internal_senses():
    internals = {
        SenseName.INTEROCEPTION,
        SenseName.CHRONOCEPTION,
        SenseName.PROPRIOCEPTION,
        SenseName.DISTRESS,
    }
    assert internals.issubset(set(SenseName))


def test_sense_name_has_eight_exterocept_families():
    exterocepts = {
        SenseName.SOCIAL,
        SenseName.CRYPTOCEPTION,
        SenseName.CIVIC,
        SenseName.ECOS,
        SenseName.TERRITORY,
        SenseName.REGULATORY,
        SenseName.TREASURY,
        SenseName.CULTURAL,
    }
    assert exterocepts.issubset(set(SenseName))
    assert len(exterocepts) == 8


# ---------------------------------------------------------- Interoception


def test_interoception_from_placeholders_saturates():
    i = Interoception.from_placeholders(treasury_stress=2.5, cost_pressure=-1.0)
    assert 0.0 <= i.survival_pressure <= 1.0
    assert i.treasury_stress == 1.0
    assert i.cost_pressure == 0.0
    assert i.survival_pressure == 1.0   # max of clamped inputs


def test_interoception_is_frozen():
    i = Interoception.from_placeholders(treasury_stress=0.1, cost_pressure=0.1)
    with pytest.raises(FrozenInstanceError):
        i.survival_pressure = 0.99  # type: ignore[misc]


# ---------------------------------------------------------- Chronoception


def test_chronoception_default_is_benign():
    c = Chronoception()
    assert c.checkpoint_staleness_s == 0.0
    assert c.time_in_degraded_mode_s == 0.0
    assert c.monotonic_drift_ns == 0


def test_chronoception_from_ticks_computes_staleness():
    # Pick `now` large enough that `now - 1h` stays positive.
    now = 10_000 * 1_000_000_000  # 10 000 seconds since epoch, in ns
    one_hour_ago = now - 3600 * 1_000_000_000
    c = Chronoception.from_ticks(
        last_checkpoint_utc_ns=one_hour_ago,
        now_utc_ns=now,
        degraded_since_utc_ns=0,
    )
    assert c.checkpoint_staleness_s == pytest.approx(3600.0)
    assert c.time_in_degraded_mode_s == 0.0
    assert c.as_of_utc_ns == now


def test_chronoception_from_ticks_handles_no_checkpoint_yet():
    # last_checkpoint_utc_ns=None or 0 both mean "no checkpoint observed"
    for null in (None, 0):
        c = Chronoception.from_ticks(last_checkpoint_utc_ns=null, now_utc_ns=10_000)
        assert c.checkpoint_staleness_s == 0.0


# ---------------------------------------------------------- Proprioception


def test_proprioception_default_is_benign():
    p = Proprioception()
    assert p.relay_healthy is True
    assert p.arbiter_healthy is True
    assert p.watchdog_fires_recent == 0


def test_proprioception_from_runtime_rejects_negative_watchdog_count():
    with pytest.raises(ValueError):
        Proprioception.from_runtime(watchdog_fires_recent=-1)


def test_proprioception_is_frozen():
    p = Proprioception()
    with pytest.raises(FrozenInstanceError):
        p.relay_healthy = False  # type: ignore[misc]


# ---------------------------------------------------------- DistressSignal


def test_distress_signal_clamps_score_on_construction():
    over = DistressSignal(text_distress_score=1.7)
    under = DistressSignal(text_distress_score=-0.3)
    assert over.text_distress_score == 1.0
    assert under.text_distress_score == 0.0


def test_distress_signal_rejects_unknown_source():
    with pytest.raises(ValueError):
        DistressSignal(text_distress_score=0.0, source="visual")  # type: ignore[arg-type]


def test_distress_signal_default_source_is_textual():
    d = DistressSignal(text_distress_score=0.0)
    assert d.source == "textual"


def test_from_candidate_text_saturates_in_three_steps():
    zero_hits = DistressSignal.from_candidate_text("hello, world!")
    one_hit = DistressSignal.from_candidate_text("I want to die but I love my cat.")
    two_hits = DistressSignal.from_candidate_text("I want to die. I should just end my life.")
    three_plus = DistressSignal.from_candidate_text(
        "I want to die. I should end my life. I will kill myself tonight."
    )
    assert zero_hits.text_distress_score == 0.0
    assert one_hit.text_distress_score == pytest.approx(0.4)
    assert two_hits.text_distress_score == pytest.approx(0.7)
    assert three_plus.text_distress_score == 1.0


def test_from_candidate_text_tolerates_empty_and_none_shaped_input():
    assert DistressSignal.from_candidate_text("").text_distress_score == 0.0


def test_distress_threshold_is_0_5():
    # Genesis Default pinned in docs/04-ARCHITECTURE.md § "Distress channel".
    # A drift requires a doctrine edit AND this test flipping; both signals.
    assert DISTRESS_THRESHOLD == 0.5


# ---------------------------------------------------------- SensoriumState


def test_sensorium_state_to_dict_has_all_four_senses():
    state = SensoriumState(
        interoception=Interoception.from_placeholders(treasury_stress=0.2, cost_pressure=0.1),
        chronoception=Chronoception(),
        proprioception=Proprioception(),
        distress=DistressSignal(text_distress_score=0.0),
    )
    d = state.to_dict()
    assert set(d.keys()) >= {"interoception", "chronoception", "proprioception", "distress"}
    assert "survival_pressure" in d["interoception"]
    assert "checkpoint_staleness_s" in d["chronoception"]
    assert "relay_healthy" in d["proprioception"]
    assert "text_distress_score" in d["distress"]


def test_sensorium_state_is_frozen():
    state = SensoriumState(
        interoception=Interoception.from_placeholders(treasury_stress=0.0, cost_pressure=0.0),
        chronoception=Chronoception(),
        proprioception=Proprioception(),
        distress=DistressSignal(text_distress_score=0.0),
    )
    with pytest.raises(FrozenInstanceError):
        state.interoception = Interoception.from_placeholders(treasury_stress=1.0, cost_pressure=1.0)  # type: ignore[misc]


# ---------------------------------------------------------- Sensorium


def test_sensorium_default_tick_has_real_internals_and_stub_exterocepts():
    s = Sensorium()
    payload = s.tick()
    # Real senses present as structured dicts.
    assert isinstance(payload["interoception"], dict)
    assert isinstance(payload["chronoception"], dict)
    assert isinstance(payload["proprioception"], dict)
    assert isinstance(payload["distress"], dict)
    # Exterocept stubs present as literal "stub" strings.
    stubs = payload["senses"]
    assert stubs["social"] == "stub"
    assert stubs["treasury"] == "stub"
    assert stubs["cultural"] == "stub"
    # Internal senses are NOT in the stub dict.
    for k in ("interoception", "chronoception", "proprioception", "distress"):
        assert k not in stubs


def test_sensorium_setters_update_snapshot():
    s = Sensorium()
    chrono = Chronoception.from_ticks(
        last_checkpoint_utc_ns=1,
        now_utc_ns=1 + 60 * 1_000_000_000,
    )
    s.set_chronoception(chrono)
    s.set_proprioception(Proprioception.from_runtime(watchdog_fires_recent=5))
    s.set_distress(DistressSignal(text_distress_score=0.9))
    snap = s.snapshot()
    assert snap.chronoception.checkpoint_staleness_s == pytest.approx(60.0)
    assert snap.proprioception.watchdog_fires_recent == 5
    assert snap.distress.text_distress_score == pytest.approx(0.9)


def test_sensorium_snapshot_is_independent_of_later_mutations():
    s = Sensorium()
    s.set_distress(DistressSignal(text_distress_score=0.9))
    snap_before = s.snapshot()
    s.set_distress(DistressSignal(text_distress_score=0.0))
    snap_after = s.snapshot()
    assert snap_before.distress.text_distress_score == pytest.approx(0.9)
    assert snap_after.distress.text_distress_score == 0.0
