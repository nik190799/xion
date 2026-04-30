"""Tests for the status publisher gateway."""

from __future__ import annotations

import json

import pytest

from orchestrator.status import (
    ArweaveStatusPublisher,
    LocalFileStatusPublisher,
    StatusPublisher,
    StatusPublisherSettings,
    get_status_publisher,
)


def test_local_file_status_publisher_writes_snapshot(tmp_path):
    path = tmp_path / "STATUS_SNAPSHOT.json"
    publisher = LocalFileStatusPublisher(path=path)

    locator = publisher.publish({"status": "ok", "details": {"run_id": "r1"}})

    assert locator == str(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["details"]["run_id"] == "r1"


def test_status_factory_selects_providers():
    local = get_status_publisher(StatusPublisherSettings(backend="local-file"))
    arweave = get_status_publisher(StatusPublisherSettings(backend="arweave"))

    assert isinstance(local, LocalFileStatusPublisher)
    assert isinstance(local, StatusPublisher)
    assert isinstance(arweave, ArweaveStatusPublisher)
    assert isinstance(arweave, StatusPublisher)


def test_status_factory_rejects_unknown_backend():
    with pytest.raises(ValueError, match="unsupported XION_STATUS_BACKEND"):
        get_status_publisher(StatusPublisherSettings(backend="moonbase"))
