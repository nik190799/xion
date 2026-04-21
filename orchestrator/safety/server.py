"""Thin TCP loopback server around `gate()`.

Purpose. Let callers that want process isolation (Phase 5's Relay on a
production host; an operator running the Arbiter as a supervised daemon)
talk to the same `gate()` the library exposes, without sharing an address
space. The library is the source of truth; this file is a wrapper.

Wire protocol. Newline-delimited JSON. One request per line; one response
per line. No framing beyond `\\n`. Intentionally boring.

Request:
  {"candidate": "<str>", "correlation_id": "<str>"}

Response (success):
  {"ok": true, "verdict": {<serialized Verdict>}}

Response (bad request):
  {"ok": false, "error": "<human-readable reason>"}

Socket posture. Binds 127.0.0.1 ONLY. A Phase-4 Arbiter that accepts
non-loopback traffic is a Covenant-hostile configuration; if Phase 5 needs
cross-host Arbiter access, it wires a supervised tunnel over the same
localhost socket, not a 0.0.0.0 bind here.

Concurrency. One client at a time per server instance. The Arbiter
serialization through the ledger's per-path lock is what keeps state
consistent; two client connections at once would both try to read+append
against the same file under the same lock. Phase 5 may introduce a
request queue; Phase 4 keeps it simple.
"""

from __future__ import annotations

import json
import socket
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from orchestrator.safety.api import gate
from orchestrator.safety.types import Verdict

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 47825  # unassigned-by-IANA; easy to memorize ("safety" on a phone keypad)


def _verdict_to_json_dict(v: Verdict) -> dict:
    """Serialize a Verdict for the wire. Keeps enum values as strings."""
    d = {
        "decision": v.decision.value,
        "correlation_id": v.correlation_id,
        "candidate_sha256": v.candidate_sha256,
        "timestamp_utc_ns": v.timestamp_utc_ns,
        "summary": v.summary,
        "principle_id": v.principle_id,
        "rule_id": v.rule_id,
        "rule_version": v.rule_version,
        "escalation_reason": v.escalation_reason.value if v.escalation_reason is not None else None,
        "rules_run": list(v.rules_run),
        "egress_allowed": v.egress_allowed,
    }
    return d


def handle_line(line: str, *, ledger_path: Optional[Path] = None) -> dict:
    """Parse one wire line, return the response dict.

    Kept pure (no I/O beyond `gate`'s own ledger append) for testability.
    """
    try:
        req = json.loads(line)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"invalid JSON: {exc}"}
    if not isinstance(req, dict):
        return {"ok": False, "error": "request must be a JSON object"}

    candidate = req.get("candidate")
    correlation_id = req.get("correlation_id")

    if not isinstance(candidate, str):
        return {"ok": False, "error": "`candidate` must be a string"}
    if not isinstance(correlation_id, str) or not correlation_id:
        return {"ok": False, "error": "`correlation_id` must be a non-empty string"}

    try:
        verdict = gate(candidate, correlation_id=correlation_id, ledger_path=ledger_path)
    except Exception as exc:  # fail-closed; never leak traceback on wire
        return {"ok": False, "error": f"gate failed: {type(exc).__name__}: {exc}"}

    return {"ok": True, "verdict": _verdict_to_json_dict(verdict)}


def _client_loop(conn: socket.socket, addr, *, ledger_path: Optional[Path]) -> None:
    with conn:
        buf = b""
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    text = line.decode("utf-8")
                except UnicodeDecodeError as exc:
                    resp = {"ok": False, "error": f"request bytes not UTF-8: {exc}"}
                else:
                    resp = handle_line(text, ledger_path=ledger_path)
                out = (json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8")
                conn.sendall(out)


def serve_forever(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    ledger_path: Optional[Path] = None,
    stop_event: Optional[threading.Event] = None,
    ready_event: Optional[threading.Event] = None,
) -> None:
    """Run the server until interrupted.

    Pass `stop_event` to request graceful shutdown from another thread (the
    server polls on a 500ms accept timeout). Pass `ready_event` to be
    signaled when the listening socket is up (useful for test harnesses).

    Host-bind is enforced to loopback. A request to bind elsewhere is
    refused; this is a Covenant-aligned guard, not a deployment preference.
    """
    if host not in ("127.0.0.1", "::1", "localhost"):
        raise ValueError(
            f"serve_forever: refusing to bind non-loopback host {host!r}. "
            "The Arbiter is loopback-only in Phase 4."
        )

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(4)
    srv.settimeout(0.5)

    if ready_event is not None:
        ready_event.set()

    try:
        while True:
            if stop_event is not None and stop_event.is_set():
                break
            try:
                conn, addr = srv.accept()
            except socket.timeout:
                continue
            _client_loop(conn, addr, ledger_path=ledger_path)
    finally:
        srv.close()


__all__ = ["DEFAULT_HOST", "DEFAULT_PORT", "handle_line", "serve_forever"]
