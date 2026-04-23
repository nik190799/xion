"""Hermetic tests for the Phase 5g-iv Admission-Control Surface.

Doctrine anchors:
    docs/04-ARCHITECTURE.md § "The Admission-Control Surface (Phase 5g-iv)"
    docs/30-API-ADMISSION.md (operational doctrine)

Coverage:

    AdmissionConfig validation
      - Short token secret rejected (< 128 bits)
      - Bad principal_id charset rejected
      - Duplicate principal_ids rejected (env loader)
      - Non-loopback host without TLS paths rejected
      - require_bearer=true with empty token registry rejected

    SlidingWindow primitive
      - Admits within budget; rejects on overflow
      - Returned retry_after_s ≥ 1 on rejection
      - Eviction frees a slot when the window slides past

    verify_bearer primitive
      - Returns matched principal_id on a valid hex bearer
      - Returns None on missing / non-bearer / malformed-hex / unknown
      - Length-mismatched secret cannot match (constant-time fallthrough)

    AuthChallenge / RateLimitChallenge envelope contracts
      - Field allowlists (content-free guarantee)

    admission_dependency end-to-end (TestClient)
      - 401 on missing bearer for /drive, /sensorium, /chat
      - 401 on wrong bearer
      - 200 on valid bearer
      - 429 on bucket overflow with Retry-After header
      - /pricing reachable without bearer (constitutionally public)
      - /health reachable without bearer (per-IP rate limited)

    Constitutional ordering: 401 → 429 → 402
      - Missing bearer + no commitment → 401 (auth wins)
      - Valid bearer + bucket overflow + no commitment → 429 (rate wins)
      - Valid bearer + within budget + no commitment → 402 (existing 5g-iii)
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

from fastapi.testclient import TestClient

from orchestrator.api.admission import (
    AdmissionConfig,
    AdmissionConfigError,
    SlidingWindow,
    _parse_token_table,
    verify_bearer,
)
from orchestrator.api.models import AuthChallenge, RateLimitChallenge

# ---------------------------------------------------------------------------
# Test fixtures (module-local — kept small, no auto-use)
# ---------------------------------------------------------------------------

_PRINCIPAL = "alice"
_SECRET = bytes(range(32))  # 32 bytes; well above the 16-byte floor
_SECRET_HEX = _SECRET.hex()


def _admission(
    *,
    require_bearer: bool = True,
    rate_budget: int = 60,
    rate_window_s: int = 60,
    health_rate_budget: int = 600,
    extra_tokens: dict[str, bytes] | None = None,
) -> AdmissionConfig:
    tokens: dict[str, bytes] = {_PRINCIPAL: _SECRET}
    if extra_tokens:
        tokens.update(extra_tokens)
    return AdmissionConfig(
        require_bearer=require_bearer,
        tokens=tokens,
        rate_budget=rate_budget,
        rate_window_s=rate_window_s,
        health_rate_budget=health_rate_budget,
        api_host="127.0.0.1",
        api_port=8000,
        tls_cert_path=None,
        tls_key_path=None,
    )


def _bearer(secret: bytes = _SECRET) -> dict[str, str]:
    return {"Authorization": f"Bearer {secret.hex()}"}


# ---------------------------------------------------------------------------
# AdmissionConfig validation
# ---------------------------------------------------------------------------


def test_admission_config_rejects_short_secret() -> None:
    with pytest.raises(AdmissionConfigError, match="minimum is 16"):
        AdmissionConfig(
            require_bearer=True,
            tokens={"alice": b"too-short"},
            rate_budget=60,
            rate_window_s=60,
            health_rate_budget=600,
            api_host="127.0.0.1",
            api_port=8000,
            tls_cert_path=None,
            tls_key_path=None,
        )


def test_admission_config_rejects_bad_principal_charset() -> None:
    with pytest.raises(AdmissionConfigError, match="does not match"):
        AdmissionConfig(
            require_bearer=True,
            tokens={"Alice!": _SECRET},
            rate_budget=60,
            rate_window_s=60,
            health_rate_budget=600,
            api_host="127.0.0.1",
            api_port=8000,
            tls_cert_path=None,
            tls_key_path=None,
        )


def test_admission_config_rejects_overlong_principal_id() -> None:
    with pytest.raises(AdmissionConfigError):
        AdmissionConfig(
            require_bearer=True,
            tokens={"a" * 65: _SECRET},
            rate_budget=60,
            rate_window_s=60,
            health_rate_budget=600,
            api_host="127.0.0.1",
            api_port=8000,
            tls_cert_path=None,
            tls_key_path=None,
        )


def test_admission_config_require_bearer_with_empty_tokens_refused() -> None:
    with pytest.raises(AdmissionConfigError, match="require_bearer=true"):
        AdmissionConfig(
            require_bearer=True,
            tokens={},
            rate_budget=60,
            rate_window_s=60,
            health_rate_budget=600,
            api_host="127.0.0.1",
            api_port=8000,
            tls_cert_path=None,
            tls_key_path=None,
        )


def test_admission_config_non_loopback_without_tls_refused(tmp_path: Path) -> None:
    with pytest.raises(AdmissionConfigError, match="non-loopback"):
        AdmissionConfig(
            require_bearer=True,
            tokens={_PRINCIPAL: _SECRET},
            rate_budget=60,
            rate_window_s=60,
            health_rate_budget=600,
            api_host="0.0.0.0",
            api_port=8000,
            tls_cert_path=None,
            tls_key_path=None,
        )


def test_admission_config_non_loopback_with_missing_cert_refused(tmp_path: Path) -> None:
    cert = tmp_path / "missing.crt"
    key = tmp_path / "missing.key"
    with pytest.raises(AdmissionConfigError, match="tls_cert_path"):
        AdmissionConfig(
            require_bearer=True,
            tokens={_PRINCIPAL: _SECRET},
            rate_budget=60,
            rate_window_s=60,
            health_rate_budget=600,
            api_host="0.0.0.0",
            api_port=8000,
            tls_cert_path=cert,
            tls_key_path=key,
        )


def test_admission_config_non_loopback_with_existing_tls_accepted(
    tmp_path: Path,
) -> None:
    cert = tmp_path / "fake.crt"
    key = tmp_path / "fake.key"
    cert.write_bytes(b"-----BEGIN CERTIFICATE-----\nx\n-----END CERTIFICATE-----\n")
    key.write_bytes(b"-----BEGIN PRIVATE KEY-----\nx\n-----END PRIVATE KEY-----\n")
    cfg = AdmissionConfig(
        require_bearer=True,
        tokens={_PRINCIPAL: _SECRET},
        rate_budget=60,
        rate_window_s=60,
        health_rate_budget=600,
        api_host="example.org",
        api_port=8443,
        tls_cert_path=cert,
        tls_key_path=key,
    )
    assert cfg.api_host == "example.org"
    assert cfg.tls_cert_path == cert


def test_admission_config_rejects_zero_budget() -> None:
    with pytest.raises(AdmissionConfigError, match="rate_budget"):
        AdmissionConfig(
            require_bearer=True,
            tokens={_PRINCIPAL: _SECRET},
            rate_budget=0,
            rate_window_s=60,
            health_rate_budget=600,
            api_host="127.0.0.1",
            api_port=8000,
            tls_cert_path=None,
            tls_key_path=None,
        )


def test_admission_config_rejects_bad_port() -> None:
    with pytest.raises(AdmissionConfigError, match="api_port"):
        AdmissionConfig(
            require_bearer=True,
            tokens={_PRINCIPAL: _SECRET},
            rate_budget=60,
            rate_window_s=60,
            health_rate_budget=600,
            api_host="127.0.0.1",
            api_port=70000,
            tls_cert_path=None,
            tls_key_path=None,
        )


# ---------------------------------------------------------------------------
# Token-table parser
# ---------------------------------------------------------------------------


def test_parse_token_table_handles_empty() -> None:
    assert _parse_token_table("") == {}
    assert _parse_token_table("   ") == {}


def test_parse_token_table_parses_two_entries() -> None:
    bob_hex = (b"\xcd" * 16).hex()
    raw = f"alice:{_SECRET_HEX}, bob:{bob_hex}"
    out = _parse_token_table(raw)
    assert set(out) == {"alice", "bob"}
    assert out["alice"] == _SECRET


def test_parse_token_table_rejects_duplicate() -> None:
    other_hex = (b"\xff" * 16).hex()
    raw = f"alice:{_SECRET_HEX},alice:{other_hex}"
    with pytest.raises(AdmissionConfigError, match="duplicate"):
        _parse_token_table(raw)


def test_parse_token_table_rejects_missing_colon() -> None:
    with pytest.raises(AdmissionConfigError, match="missing ':'"):
        _parse_token_table("alice")


def test_parse_token_table_rejects_non_hex_secret() -> None:
    with pytest.raises(AdmissionConfigError, match="non-hex"):
        _parse_token_table("alice:nothex")


# ---------------------------------------------------------------------------
# SlidingWindow primitive
# ---------------------------------------------------------------------------


def test_sliding_window_admits_within_budget() -> None:
    win = SlidingWindow(budget=3, window_ns=1_000_000_000)
    t0 = 10_000_000_000
    assert win.check_and_record(now_ns=t0) == (True, 0)
    assert win.check_and_record(now_ns=t0 + 1) == (True, 0)
    assert win.check_and_record(now_ns=t0 + 2) == (True, 0)


def test_sliding_window_rejects_on_overflow() -> None:
    win = SlidingWindow(budget=2, window_ns=1_000_000_000)
    t0 = 10_000_000_000
    win.check_and_record(now_ns=t0)
    win.check_and_record(now_ns=t0)
    admitted, retry = win.check_and_record(now_ns=t0)
    assert admitted is False
    assert retry >= 1


def test_sliding_window_evicts_after_window() -> None:
    win = SlidingWindow(budget=1, window_ns=1_000_000_000)
    t0 = 10_000_000_000
    assert win.check_and_record(now_ns=t0) == (True, 0)
    # Just inside the window — still rejects.
    admitted, retry = win.check_and_record(now_ns=t0 + 500_000_000)
    assert admitted is False
    assert retry == 1
    # Past the window — old entry evicts, new one admits.
    assert win.check_and_record(now_ns=t0 + 2_000_000_000) == (True, 0)


def test_sliding_window_rejects_bad_construction() -> None:
    with pytest.raises(ValueError):
        SlidingWindow(budget=0, window_ns=1_000_000_000)
    with pytest.raises(ValueError):
        SlidingWindow(budget=1, window_ns=0)


# ---------------------------------------------------------------------------
# verify_bearer primitive
# ---------------------------------------------------------------------------


def test_verify_bearer_returns_matched_principal_id() -> None:
    tokens = {_PRINCIPAL: _SECRET}
    assert verify_bearer(f"Bearer {_SECRET_HEX}", tokens) == _PRINCIPAL


def test_verify_bearer_returns_none_on_missing_header() -> None:
    assert verify_bearer(None, {_PRINCIPAL: _SECRET}) is None
    assert verify_bearer("", {_PRINCIPAL: _SECRET}) is None


def test_verify_bearer_returns_none_on_non_bearer_scheme() -> None:
    assert verify_bearer(f"Basic {_SECRET_HEX}", {_PRINCIPAL: _SECRET}) is None


def test_verify_bearer_returns_none_on_malformed_hex() -> None:
    assert verify_bearer("Bearer ZZZZ", {_PRINCIPAL: _SECRET}) is None


def test_verify_bearer_returns_none_on_unknown_token() -> None:
    other = (b"\x99" * 32).hex()
    assert verify_bearer(f"Bearer {other}", {_PRINCIPAL: _SECRET}) is None


def test_verify_bearer_returns_none_on_too_short_input() -> None:
    short = (b"\x01" * 8).hex()  # 8 bytes < 16
    assert verify_bearer(f"Bearer {short}", {_PRINCIPAL: _SECRET}) is None


def test_verify_bearer_picks_correct_principal_when_multiple_tokens() -> None:
    bob_secret = b"\xbb" * 16
    tokens = {"alice": _SECRET, "bob": bob_secret}
    assert verify_bearer(f"Bearer {bob_secret.hex()}", tokens) == "bob"


# ---------------------------------------------------------------------------
# Envelope contracts
# ---------------------------------------------------------------------------


def test_auth_challenge_field_allowlist() -> None:
    assert set(AuthChallenge.model_fields.keys()) == {"error", "accepted_schemes"}


def test_rate_limit_challenge_field_allowlist() -> None:
    assert set(RateLimitChallenge.model_fields.keys()) == {
        "error",
        "retry_after_s",
        "bucket",
    }


# ---------------------------------------------------------------------------
# End-to-end via TestClient (admission_dependency wired through routes)
# ---------------------------------------------------------------------------


def test_drive_401_on_missing_bearer(app_factory: Callable[..., Any]) -> None:
    app = app_factory(admission_config=_admission())
    with TestClient(app) as client:
        r = client.get("/drive")
    assert r.status_code == 401
    body = r.json()["detail"]
    assert body["error"] == "unauthorized"
    assert body["accepted_schemes"] == ["Bearer"]
    assert r.headers.get("WWW-Authenticate") == "Bearer"


def test_drive_401_on_wrong_bearer(app_factory: Callable[..., Any]) -> None:
    app = app_factory(admission_config=_admission())
    wrong = (b"\x99" * 32).hex()
    with TestClient(app) as client:
        r = client.get("/drive", headers={"Authorization": f"Bearer {wrong}"})
    assert r.status_code == 401


def test_drive_200_on_valid_bearer(app_factory: Callable[..., Any]) -> None:
    app = app_factory(admission_config=_admission())
    with TestClient(app) as client:
        r = client.get("/drive", headers=_bearer())
    assert r.status_code == 200, r.text


def test_sensorium_401_on_missing_bearer(app_factory: Callable[..., Any]) -> None:
    app = app_factory(admission_config=_admission())
    with TestClient(app) as client:
        r = client.get("/sensorium")
    assert r.status_code == 401


def test_chat_401_on_missing_bearer(app_factory: Callable[..., Any]) -> None:
    app = app_factory(admission_config=_admission())
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "hi"})
    assert r.status_code == 401


def test_pricing_reachable_without_bearer(
    app_factory: Callable[..., Any],
) -> None:
    """``/pricing`` is constitutionally public per existing 5g-iii doctrine."""
    app = app_factory(admission_config=_admission())
    with TestClient(app) as client:
        r = client.get("/pricing")
    assert r.status_code == 200, r.text
    assert "per_message_price_micro_XION" in r.json()


def test_health_reachable_without_bearer(
    app_factory: Callable[..., Any],
) -> None:
    """``/health`` is auth-free (liveness probes work without a token)."""
    app = app_factory(admission_config=_admission())
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200, r.text


def test_drive_429_on_bucket_overflow(app_factory: Callable[..., Any]) -> None:
    """Per-principal sliding window rejects with 429 + Retry-After once the
    budget is exhausted within the window."""
    app = app_factory(admission_config=_admission(rate_budget=2, rate_window_s=60))
    with TestClient(app) as client:
        # Two admitted requests fill the bucket.
        assert client.get("/drive", headers=_bearer()).status_code == 200
        assert client.get("/drive", headers=_bearer()).status_code == 200
        # Third request inside the window must reject with 429.
        r = client.get("/drive", headers=_bearer())
    assert r.status_code == 429
    body = r.json()["detail"]
    assert body["error"] == "rate_limited"
    assert body["bucket"] == "principal"
    assert body["retry_after_s"] >= 1
    assert int(r.headers["Retry-After"]) == body["retry_after_s"]


def test_health_429_on_per_ip_overflow(app_factory: Callable[..., Any]) -> None:
    """The per-IP /health bucket rejects with 429 + bucket='ip' once exhausted."""
    app = app_factory(
        admission_config=_admission(health_rate_budget=2, rate_window_s=60),
    )
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 200
        r = client.get("/health")
    assert r.status_code == 429
    body = r.json()["detail"]
    assert body["bucket"] == "ip"


def test_compat_mode_allows_unauth_traffic(app_factory: Callable[..., Any]) -> None:
    """``XION_API_REQUIRE_BEARER=false`` is the 5g-i backward-compat posture.
    The autouse conftest fixture sets this, so unconfigured tests reach the
    routes without bearer."""
    app = app_factory()  # No admission_config; lifespan loads from env (REQUIRE_BEARER=false).
    with TestClient(app) as client:
        assert client.get("/drive").status_code == 200
        assert client.get("/sensorium").status_code == 200


# ---------------------------------------------------------------------------
# Constitutional ordering: 401 → 429 → 402
# ---------------------------------------------------------------------------


def test_ordering_401_wins_over_402(app_factory: Callable[..., Any]) -> None:
    """Missing bearer + missing commitment must surface as 401 (auth before
    payment). Otherwise an unauthenticated scraper could probe the 402
    surface and learn the posted price + accepted postures."""
    from orchestrator.billing import BillingConfig

    arch_sha = "1" * 64
    secret = b"\xab" * 32
    bcfg = BillingConfig(
        billing_required=True,
        allow_x402=True,
        operator_attestation_secret=secret,
        payment_ledger_path=Path("PAYMENT_LEDGER_test_401.jsonl"),
        architecture_sha256=arch_sha,
    )
    app = app_factory(admission_config=_admission(), billing_config=bcfg)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "hi"})
    assert r.status_code == 401, r.text
    assert r.json()["detail"]["error"] == "unauthorized"


def test_ordering_429_wins_over_402(app_factory: Callable[..., Any]) -> None:
    """Valid bearer + bucket overflow + missing commitment must surface as
    429 (rate-limit before payment). Otherwise a token-holding integrator
    that has already exceeded its budget could be told the request is
    payment-eligible — which it is not, because the bucket already
    rejected it."""
    from orchestrator.billing import BillingConfig

    arch_sha = "1" * 64
    secret = b"\xab" * 32
    bcfg = BillingConfig(
        billing_required=True,
        allow_x402=True,
        operator_attestation_secret=secret,
        payment_ledger_path=Path("PAYMENT_LEDGER_test_429.jsonl"),
        architecture_sha256=arch_sha,
    )
    app = app_factory(
        admission_config=_admission(rate_budget=1, rate_window_s=60),
        billing_config=bcfg,
    )
    with TestClient(app) as client:
        # First request: no commitment, bearer ok → 402 (within budget,
        # bucket consumes one slot).
        r1 = client.post("/chat", json={"message": "hi"}, headers=_bearer())
        assert r1.status_code == 402, r1.text
        # Second request: bucket is now exhausted → 429 must win over 402.
        r2 = client.post("/chat", json={"message": "hi"}, headers=_bearer())
    assert r2.status_code == 429, r2.text
    assert r2.json()["detail"]["error"] == "rate_limited"


def test_ordering_402_when_authed_and_within_budget(
    app_factory: Callable[..., Any],
) -> None:
    """Valid bearer + within budget + missing commitment → 402 (existing
    5g-iii behaviour). Demonstrates that admission does not eat the 402
    when both predecessor gates pass."""
    from orchestrator.billing import BillingConfig

    arch_sha = "1" * 64
    secret = b"\xab" * 32
    bcfg = BillingConfig(
        billing_required=True,
        allow_x402=True,
        operator_attestation_secret=secret,
        payment_ledger_path=Path("PAYMENT_LEDGER_test_402.jsonl"),
        architecture_sha256=arch_sha,
    )
    app = app_factory(admission_config=_admission(), billing_config=bcfg)
    with TestClient(app) as client:
        r = client.post("/chat", json={"message": "hi"}, headers=_bearer())
    assert r.status_code == 402
    assert r.json()["error"] == "payment_required"


# ---------------------------------------------------------------------------
# Phase 5g+ RateLimitStore variants
# ---------------------------------------------------------------------------


def test_in_process_store_lazily_allocates_per_principal() -> None:
    """The default store allocates buckets on first admit, not at
    construction time. This is the 5g+ pay-down of the 5g-iv
    pre-populated posture: a principal that never connects consumes
    zero bucket memory."""
    from orchestrator.api.admission import InProcessSlidingWindowStore

    store = InProcessSlidingWindowStore(budget=2, window_ns=1_000_000_000)
    assert store.known_principals() == []
    admitted, retry = store.check_and_record("alice", now_ns=10**9)
    assert admitted is True
    assert retry == 0
    assert store.known_principals() == ["alice"]
    # A second principal opens its own bucket; they do not share.
    store.check_and_record("bob", now_ns=10**9)
    assert set(store.known_principals()) == {"alice", "bob"}


def test_in_process_store_rejects_on_overflow_same_principal() -> None:
    from orchestrator.api.admission import InProcessSlidingWindowStore

    store = InProcessSlidingWindowStore(budget=2, window_ns=1_000_000_000)
    t0 = 10**9
    assert store.check_and_record("alice", now_ns=t0)[0] is True
    assert store.check_and_record("alice", now_ns=t0 + 1)[0] is True
    admitted, retry = store.check_and_record("alice", now_ns=t0 + 2)
    assert admitted is False
    assert retry >= 1


def test_in_process_store_independent_principals_independent_budgets() -> None:
    """Property: one principal overflowing does not starve another.
    A bucket is per-principal; different principals do not share."""
    from orchestrator.api.admission import InProcessSlidingWindowStore

    store = InProcessSlidingWindowStore(budget=1, window_ns=1_000_000_000)
    t0 = 10**9
    assert store.check_and_record("alice", now_ns=t0)[0] is True
    # Alice over budget:
    assert store.check_and_record("alice", now_ns=t0 + 1)[0] is False
    # Bob has a full budget still:
    assert store.check_and_record("bob", now_ns=t0 + 1)[0] is True


# ---------------------------------------------------------------------------
# Phase 5g+ broker-backed multi-worker budget coherence (closes KW-RATE-001)
# ---------------------------------------------------------------------------


def test_broker_backed_store_two_workers_share_one_global_bucket(
    tmp_path: Path,
) -> None:
    """Multi-worker budget-coherence property (closes KW-RATE-001):
    two workers sharing one broker DB see one global bucket per
    principal. A principal hitting worker A then worker B exhausts
    the global budget in N total requests, not N × workers requests.

    This is the core property Phase 5g+ closes. In the 5g-iv in-process
    posture, two workers would each allow N admits before rejecting —
    a 2× budget inflation. With the broker, the 1st admit on worker A
    and the 1st admit on worker B share the same SQLite-backed bucket;
    the (N+1)th admit across both workers rejects.
    """
    from orchestrator.api.admission import BrokerBackedSlidingWindowStore
    from orchestrator.runtime import BrokerConfig, SqliteBroker

    db_path = tmp_path / "broker.sqlite3"
    broker_a = SqliteBroker(config=BrokerConfig(
        db_path=db_path, leader_lease_s=10.0, leader_renew_s=1.0
    ))
    broker_b = SqliteBroker(config=BrokerConfig(
        db_path=db_path, leader_lease_s=10.0, leader_renew_s=1.0
    ))
    try:
        store_a = BrokerBackedSlidingWindowStore(
            broker=broker_a, budget=3, window_ns=10_000_000_000
        )
        store_b = BrokerBackedSlidingWindowStore(
            broker=broker_b, budget=3, window_ns=10_000_000_000
        )
        t0 = 1_000_000_000_000
        # Two admits on A; one admit on B. Budget is 3. Total is 3 —
        # the global bucket is now full.
        assert store_a.check_and_record("alice", now_ns=t0)[0] is True
        assert store_a.check_and_record("alice", now_ns=t0 + 1)[0] is True
        assert store_b.check_and_record("alice", now_ns=t0 + 2)[0] is True
        # The 4th total attempt — on either worker — rejects.
        admitted_a, retry_a = store_a.check_and_record("alice", now_ns=t0 + 3)
        assert admitted_a is False
        assert retry_a >= 1
        admitted_b, retry_b = store_b.check_and_record("alice", now_ns=t0 + 4)
        assert admitted_b is False
        assert retry_b >= 1
    finally:
        broker_a.close()
        broker_b.close()


def test_broker_backed_store_different_principals_do_not_share(
    tmp_path: Path,
) -> None:
    """The broker keys buckets by principal_id; different principals
    maintain independent budgets even through a shared broker."""
    from orchestrator.api.admission import BrokerBackedSlidingWindowStore
    from orchestrator.runtime import BrokerConfig, SqliteBroker

    db_path = tmp_path / "broker.sqlite3"
    broker = SqliteBroker(config=BrokerConfig(
        db_path=db_path, leader_lease_s=10.0, leader_renew_s=1.0
    ))
    try:
        store = BrokerBackedSlidingWindowStore(
            broker=broker, budget=1, window_ns=10_000_000_000
        )
        t0 = 1_000_000_000_000
        assert store.check_and_record("alice", now_ns=t0)[0] is True
        # Alice over budget:
        assert store.check_and_record("alice", now_ns=t0 + 1)[0] is False
        # Bob has a fresh budget:
        assert store.check_and_record("bob", now_ns=t0 + 2)[0] is True
    finally:
        broker.close()


def test_broker_backed_store_eviction_across_workers(tmp_path: Path) -> None:
    """Global bucket eviction: a time advance past the window frees
    the bucket for BOTH workers (the broker's DELETE is scoped by
    principal, not by worker)."""
    from orchestrator.api.admission import BrokerBackedSlidingWindowStore
    from orchestrator.runtime import BrokerConfig, SqliteBroker

    db_path = tmp_path / "broker.sqlite3"
    broker_a = SqliteBroker(config=BrokerConfig(
        db_path=db_path, leader_lease_s=10.0, leader_renew_s=1.0
    ))
    broker_b = SqliteBroker(config=BrokerConfig(
        db_path=db_path, leader_lease_s=10.0, leader_renew_s=1.0
    ))
    try:
        window_ns = 1_000_000_000
        store_a = BrokerBackedSlidingWindowStore(
            broker=broker_a, budget=1, window_ns=window_ns
        )
        store_b = BrokerBackedSlidingWindowStore(
            broker=broker_b, budget=1, window_ns=window_ns
        )
        t0 = 1_000_000_000_000
        assert store_a.check_and_record("alice", now_ns=t0)[0] is True
        # Worker B sees the global bucket full:
        assert store_b.check_and_record("alice", now_ns=t0 + 1)[0] is False
        # Advance past the window; the prior admit evicts. The next
        # admit on either worker succeeds.
        assert store_b.check_and_record(
            "alice", now_ns=t0 + window_ns + 10
        )[0] is True
    finally:
        broker_a.close()
        broker_b.close()


def test_build_rate_limiters_returns_in_process_store_when_no_broker() -> None:
    """Backward-compat: build_rate_limiters without a broker returns the
    in-process store (the 5g-iv posture, Lazy-allocated per-principal)."""
    from orchestrator.api.admission import (
        InProcessSlidingWindowStore,
        build_rate_limiters,
    )

    config = _admission(rate_budget=10, rate_window_s=30)
    store = build_rate_limiters(config)
    assert isinstance(store, InProcessSlidingWindowStore)


def test_build_rate_limiters_returns_broker_backed_store_with_broker(
    tmp_path: Path,
) -> None:
    """When build_rate_limiters is handed a broker, it returns the
    broker-backed store. This is the lifespan's wiring path when
    XION_BROKER_DB_PATH is set."""
    from orchestrator.api.admission import (
        BrokerBackedSlidingWindowStore,
        build_rate_limiters,
    )
    from orchestrator.runtime import BrokerConfig, SqliteBroker

    broker = SqliteBroker(config=BrokerConfig(
        db_path=tmp_path / "broker.sqlite3",
        leader_lease_s=10.0,
        leader_renew_s=1.0,
    ))
    try:
        config = _admission(rate_budget=10, rate_window_s=30)
        store = build_rate_limiters(config, broker=broker)
        assert isinstance(store, BrokerBackedSlidingWindowStore)
    finally:
        broker.close()


def test_admission_dependency_with_broker_backed_store_enforces_429(
    app_factory: Callable[..., Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end integration: a lifespan with XION_BROKER_DB_PATH set
    wires a BrokerBackedSlidingWindowStore; admission_dependency reads
    it and still enforces 429 on overflow (the wire-shape stays
    identical; only the storage swapped)."""
    broker_path = tmp_path / "broker.sqlite3"
    monkeypatch.setenv("XION_BROKER_DB_PATH", str(broker_path))
    monkeypatch.setenv("XION_BROKER_LEADER_LEASE_S", "10.0")
    monkeypatch.setenv("XION_BROKER_LEADER_RENEW_S", "1.0")

    app = app_factory(
        admission_config=_admission(rate_budget=2, rate_window_s=60),
        tick_cadence_s=0.05,
    )
    with TestClient(app) as client:
        # Verify the broker-backed path is live.
        from orchestrator.api.admission import BrokerBackedSlidingWindowStore

        assert isinstance(
            app.state.rate_limiters, BrokerBackedSlidingWindowStore
        )
        r1 = client.get("/drive", headers=_bearer())
        assert r1.status_code == 200, r1.text
        r2 = client.get("/drive", headers=_bearer())
        assert r2.status_code == 200, r2.text
        r3 = client.get("/drive", headers=_bearer())
    assert r3.status_code == 429, r3.text
    assert r3.json()["detail"]["bucket"] == "principal"
