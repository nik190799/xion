"""Tests for the alerting gateway."""

from __future__ import annotations

import json

import pytest

from orchestrator.alerting import (
    Alerter,
    AlerterSettings,
    LocalLogAlerter,
    NtfyAlerter,
    PushoverAlerter,
    get_alerter,
)


def test_local_log_alerter_writes_jsonl(tmp_path):
    path = tmp_path / "ALERT_LOG.jsonl"
    alerter = LocalLogAlerter(path=path)

    alerter.notify("critical", "summary", "body")

    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["provider_id"] == "local-log"
    assert row["level"] == "critical"
    assert row["summary"] == "summary"


def test_alert_factory_selects_providers():
    assert isinstance(get_alerter(AlerterSettings(provider="local-log")), LocalLogAlerter)
    assert isinstance(get_alerter(AlerterSettings(provider="local-log")), Alerter)
    assert isinstance(get_alerter(AlerterSettings(provider="ntfy")), NtfyAlerter)
    assert isinstance(get_alerter(AlerterSettings(provider="pushover")), PushoverAlerter)


def test_hosted_alert_providers_do_not_fake_without_credentials():
    with pytest.raises(NotImplementedError, match="KW-ALERT-001"):
        NtfyAlerter().notify("critical", "summary", "body")
    with pytest.raises(NotImplementedError, match="KW-ALERT-001"):
        PushoverAlerter().notify("critical", "summary", "body")
