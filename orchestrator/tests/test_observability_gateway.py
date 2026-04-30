"""Tests for the observability gateway."""

from __future__ import annotations

import pytest

from orchestrator.observability import (
    HostedObservabilityStub,
    MetricsEmitter,
    ObservabilitySettings,
    StdoutObservability,
    get_observability,
)


def test_stdout_observability_satisfies_all_protocols(capsys):
    obs = get_observability(ObservabilitySettings(provider="stdout"))

    assert isinstance(obs.metrics, StdoutObservability)
    assert isinstance(obs.metrics, MetricsEmitter)
    obs.metrics.emit("test.metric", 1.0, {"kind": "unit"})
    obs.logs.log("info", "hello", {"a": 1})
    with obs.traces.span("unit-span", {"b": 2}):
        pass

    out = capsys.readouterr().out
    assert '"kind":"metric"' in out
    assert '"kind":"log"' in out
    assert '"kind":"span_start"' in out
    assert '"kind":"span_end"' in out


def test_hosted_observability_stub_does_not_fake_provider():
    obs = get_observability(ObservabilitySettings(provider="hosted"))

    assert isinstance(obs.metrics, HostedObservabilityStub)
    with pytest.raises(NotImplementedError, match="KW-OBS-001"):
        obs.metrics.emit("test.metric", 1.0)


def test_observability_factory_rejects_unknown_provider():
    with pytest.raises(ValueError, match="unsupported XION_OBSERVABILITY_PROVIDER"):
        get_observability(ObservabilitySettings(provider="moonbase"))
