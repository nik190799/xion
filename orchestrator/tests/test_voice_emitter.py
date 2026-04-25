"""Voice emitter prosody frame composition."""

from orchestrator.sensorium.sensorium import (
    Chronoception,
    DistressSignal,
    Interoception,
    Proprioception,
    SensoriumState,
)
from orchestrator.senses.voice_emitter import compose_voice_frame


def _state(distress: float) -> SensoriumState:
    return SensoriumState(
        interoception=Interoception.from_placeholders(
            treasury_stress=0.1, cost_pressure=0.1
        ),
        chronoception=Chronoception(),
        proprioception=Proprioception(),
        distress=DistressSignal(text_distress_score=distress, source="textual"),
    )


def test_compose_includes_refusal_veil() -> None:
    f = compose_voice_frame(_state(0.0), refusal=True)
    assert f.get("veil") is True


def test_compose_lowers_energy_with_distress() -> None:
    low = compose_voice_frame(_state(0.1), refusal=False)
    high = compose_voice_frame(_state(0.9), refusal=False)
    assert high["energy"] < low["energy"]
