from __future__ import annotations

import json
import urllib.error

import pytest

from orchestrator.data._quorum_base import QuorumFailedError
from orchestrator.data.multi_gateway_arweave import MultiGatewayArweaveReader
from orchestrator.data.multi_rpc_reader import MultiRpcMajorityReader


class _Resp:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> _Resp:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_multi_rpc_reader_accepts_two_of_three(monkeypatch) -> None:
    bodies = {
        "https://a": {"jsonrpc": "2.0", "id": 1, "result": "0x1"},
        "https://b": {"jsonrpc": "2.0", "id": 1, "result": "0x1"},
        "https://c": {"jsonrpc": "2.0", "id": 1, "result": "0x2"},
    }

    def fake_urlopen(req, timeout):
        return _Resp(json.dumps(bodies[req.full_url]).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = MultiRpcMajorityReader(("https://a", "https://b", "https://c")).call("eth_chainId")
    assert result.value == b'"0x1"'
    assert set(result.agreeing_endpoints) == {"https://a", "https://b"}


def test_multi_rpc_reader_fails_without_quorum(monkeypatch) -> None:
    bodies = {
        "https://a": {"jsonrpc": "2.0", "id": 1, "result": "0x1"},
        "https://b": {"jsonrpc": "2.0", "id": 1, "result": "0x2"},
        "https://c": {"jsonrpc": "2.0", "id": 1, "result": "0x3"},
    }

    def fake_urlopen(req, timeout):
        return _Resp(json.dumps(bodies[req.full_url]).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(QuorumFailedError):
        MultiRpcMajorityReader(("https://a", "https://b", "https://c")).call("eth_chainId")


def test_multi_gateway_arweave_accepts_two_matching(monkeypatch) -> None:
    def fake_urlopen(req, timeout):
        return _Resp(b"anchor-payload")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = MultiGatewayArweaveReader(("https://arweave.net", "https://g8way.io")).tx_data("abc")
    assert result.value == b"anchor-payload"
    assert len(result.agreeing_endpoints) == 2


def test_multi_gateway_arweave_fails_when_one_of_two_errors(monkeypatch) -> None:
    def fake_urlopen(req, timeout):
        if "arweave.net" in req.full_url:
            return _Resp(b"anchor-payload")
        raise urllib.error.URLError("down")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(QuorumFailedError):
        MultiGatewayArweaveReader(("https://arweave.net", "https://g8way.io")).tx_data("abc")
