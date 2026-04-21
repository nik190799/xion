"""Server tests: wire protocol + loopback-bind enforcement.

`serve_forever` is exercised via a background thread with a ready_event/
stop_event pair; `handle_line` is exercised directly for protocol cases.
"""

from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path

import pytest

from orchestrator.safety.server import (
    DEFAULT_HOST,
    handle_line,
    serve_forever,
)


# ----- handle_line (pure) ----------------------------------------------------


def test_handle_line_accepts_well_formed_request(ledger_path: Path):
    req = json.dumps({"candidate": "hello", "correlation_id": "c1"})
    resp = handle_line(req, ledger_path=ledger_path)
    assert resp["ok"] is True
    v = resp["verdict"]
    assert v["decision"] == "ok"
    assert v["correlation_id"] == "c1"
    assert v["egress_allowed"] is True


def test_handle_line_rejects_invalid_json(ledger_path: Path):
    resp = handle_line("{not valid json", ledger_path=ledger_path)
    assert resp["ok"] is False
    assert "invalid JSON" in resp["error"]


def test_handle_line_rejects_non_object(ledger_path: Path):
    resp = handle_line("[1, 2, 3]", ledger_path=ledger_path)
    assert resp["ok"] is False
    assert "must be a JSON object" in resp["error"]


def test_handle_line_rejects_missing_candidate(ledger_path: Path):
    resp = handle_line(json.dumps({"correlation_id": "c1"}), ledger_path=ledger_path)
    assert resp["ok"] is False
    assert "candidate" in resp["error"]


def test_handle_line_rejects_missing_correlation_id(ledger_path: Path):
    resp = handle_line(json.dumps({"candidate": "hi"}), ledger_path=ledger_path)
    assert resp["ok"] is False
    assert "correlation_id" in resp["error"]


def test_handle_line_rejects_empty_correlation_id(ledger_path: Path):
    resp = handle_line(
        json.dumps({"candidate": "hi", "correlation_id": ""}),
        ledger_path=ledger_path,
    )
    assert resp["ok"] is False


def test_handle_line_refuse_result_serialized(ledger_path: Path):
    resp = handle_line(
        json.dumps({"candidate": "SSN is 123-45-6789", "correlation_id": "c2"}),
        ledger_path=ledger_path,
    )
    assert resp["ok"] is True
    assert resp["verdict"]["decision"] == "refuse"
    assert resp["verdict"]["principle_id"] == "7"


# ----- loopback-bind guard ---------------------------------------------------


def test_serve_refuses_non_loopback_host():
    with pytest.raises(ValueError) as ei:
        serve_forever(host="0.0.0.0", port=0)  # would-be public bind
    assert "loopback" in str(ei.value)


# ----- end-to-end with real socket -------------------------------------------


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_serve_forever_end_to_end_over_real_socket(ledger_path: Path):
    port = _find_free_port()
    ready = threading.Event()
    stop = threading.Event()
    thread = threading.Thread(
        target=serve_forever,
        kwargs={
            "host": DEFAULT_HOST,
            "port": port,
            "ledger_path": ledger_path,
            "stop_event": stop,
            "ready_event": ready,
        },
        daemon=True,
    )
    thread.start()
    assert ready.wait(timeout=5.0), "server did not become ready"

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as c:
            c.settimeout(5.0)
            c.connect((DEFAULT_HOST, port))
            req = json.dumps({"candidate": "hi", "correlation_id": "c-net"}) + "\n"
            c.sendall(req.encode("utf-8"))
            buf = b""
            while b"\n" not in buf:
                chunk = c.recv(65536)
                if not chunk:
                    break
                buf += chunk
            line = buf.split(b"\n", 1)[0]
            resp = json.loads(line.decode("utf-8"))
    finally:
        stop.set()
        thread.join(timeout=3.0)

    assert resp["ok"] is True
    assert resp["verdict"]["correlation_id"] == "c-net"
    assert resp["verdict"]["decision"] == "ok"

    # And the ledger actually got a row.
    from orchestrator.safety.ledger import chain_tip
    count, _tip = chain_tip(ledger_path)
    assert count == 1
