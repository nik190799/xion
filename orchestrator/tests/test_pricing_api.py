"""Tests for the Phase 5g-iii ``GET /pricing`` endpoint.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Chat Billing Surface
(Phase 5g-iii)". Constitutional property exercised here: the Relay
exposes governance-posted pricing with a full five-slice breakdown, and
the server refuses to start on a misconfigured pricing split (fail-
closed, analogous to a broken ledger chain).

These tests are hermetic: every test either constructs an explicit
``PricingConfig`` via ``app_factory(pricing_config=...)`` or relies on
the autouse conftest fixture that wipes ``XION_POSTED_PRICE_*`` /
``XION_PRICE_SLICE_*`` env vars, so Genesis Defaults apply.

Skipped in full if ``fastapi`` or ``pydantic`` is missing — same
posture as the Phase 5f / 5g-i HTTP tests.
"""

from __future__ import annotations

import time

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

from fastapi.testclient import TestClient

from orchestrator.api import (
    PricingConfig,
    PricingConfigError,
    PricingResponse,
    load_pricing_config_from_env,
)


# ----------------------------------------------------- PricingConfig unit


def test_pricing_config_genesis_defaults_sum_to_one() -> None:
    """The Genesis Default five-slice values pinned in
    ``pricing.py`` sum to 1.0 and construct without raising."""
    # Construct via the loader with no env vars set (conftest autouse
    # wipes them). The loader returns the Genesis Defaults.
    cfg = load_pricing_config_from_env(now_utc_ns=1_000_000_000)
    total = (
        cfg.variable_cost
        + cfg.overhead_slice
        + cfg.improvement_slice
        + cfg.reserve_slice
        + cfg.small_buffer
    )
    assert abs(total - 1.0) < 1e-9, (
        f"Genesis Default slices must sum to 1.0; got {total}"
    )
    assert cfg.improvement_slice == pytest.approx(0.08), (
        "docs/07-ECONOMY.md pins improvement_slice at 8%"
    )
    assert cfg.reserve_slice == pytest.approx(0.05), (
        "docs/07-ECONOMY.md pins reserve_slice at 5%"
    )
    assert 0.03 <= cfg.small_buffer <= 0.05, (
        "docs/07-ECONOMY.md pins small_buffer to the 3–5% band"
    )
    assert cfg.governance_revision_id == "genesis-default-v1"
    assert cfg.per_message_price_micro_XION >= 0
    assert cfg.last_reviewed_utc_ns == 1_000_000_000


def test_pricing_config_rejects_unbalanced_split() -> None:
    """A five-slice split whose sum exceeds the tolerance must refuse
    to construct. This is the constitutional fail-closed."""
    with pytest.raises(PricingConfigError, match="sum to 1.0"):
        PricingConfig(
            per_message_price_micro_XION=1000,
            variable_cost=0.50,
            overhead_slice=0.50,
            improvement_slice=0.08,
            reserve_slice=0.05,
            small_buffer=0.03,
            last_reviewed_utc_ns=1_000_000_000,
            governance_revision_id="test",
        )


def test_pricing_config_rejects_negative_slice() -> None:
    """Negative slices are schema violations."""
    with pytest.raises(PricingConfigError, match="must be in"):
        PricingConfig(
            per_message_price_micro_XION=1000,
            variable_cost=-0.10,
            overhead_slice=0.94,
            improvement_slice=0.08,
            reserve_slice=0.05,
            small_buffer=0.03,
            last_reviewed_utc_ns=1_000_000_000,
            governance_revision_id="test",
        )


def test_pricing_config_rejects_negative_price() -> None:
    """Negative posted price is a schema violation even if the five
    slices are internally consistent."""
    with pytest.raises(PricingConfigError, match="non-negative"):
        PricingConfig(
            per_message_price_micro_XION=-1,
            variable_cost=0.40,
            overhead_slice=0.44,
            improvement_slice=0.08,
            reserve_slice=0.05,
            small_buffer=0.03,
            last_reviewed_utc_ns=1_000_000_000,
            governance_revision_id="test",
        )


def test_pricing_config_rejects_empty_revision_id() -> None:
    with pytest.raises(PricingConfigError, match="non-empty"):
        PricingConfig(
            per_message_price_micro_XION=1000,
            variable_cost=0.40,
            overhead_slice=0.44,
            improvement_slice=0.08,
            reserve_slice=0.05,
            small_buffer=0.03,
            last_reviewed_utc_ns=1_000_000_000,
            governance_revision_id="",
        )


def test_pricing_config_accepts_zero_price() -> None:
    """A promotional or free-tier posted price of zero is legal —
    the five-slice invariant still holds (zero times any split is
    zero) and the wire shape carries the zero faithfully."""
    cfg = PricingConfig(
        per_message_price_micro_XION=0,
        variable_cost=0.40,
        overhead_slice=0.44,
        improvement_slice=0.08,
        reserve_slice=0.05,
        small_buffer=0.03,
        last_reviewed_utc_ns=1_000_000_000,
        governance_revision_id="promo-v1",
    )
    body = cfg.to_response().model_dump()
    assert body["per_message_price_micro_XION"] == 0


# ----------------------------------------------------- env loader seams


def test_env_loader_rejects_malformed_float(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-numeric value for a slice env var must fail-closed."""
    monkeypatch.setenv("XION_PRICE_SLICE_VARIABLE_COST", "not-a-number")
    with pytest.raises(PricingConfigError, match="must be a float"):
        load_pricing_config_from_env()


def test_env_loader_rejects_malformed_int(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-integer value for the posted price must fail-closed."""
    monkeypatch.setenv("XION_POSTED_PRICE_MICRO_XION", "1.5")
    with pytest.raises(PricingConfigError, match="must be an integer"):
        load_pricing_config_from_env()


def test_env_loader_honours_operator_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """An operator who posts a complete override via env vars gets
    those values back byte-for-byte, not the Genesis Defaults."""
    monkeypatch.setenv("XION_POSTED_PRICE_MICRO_XION", "5000")
    monkeypatch.setenv("XION_PRICE_SLICE_VARIABLE_COST", "0.30")
    monkeypatch.setenv("XION_PRICE_SLICE_OVERHEAD", "0.54")
    monkeypatch.setenv("XION_PRICE_SLICE_IMPROVEMENT", "0.08")
    monkeypatch.setenv("XION_PRICE_SLICE_RESERVE", "0.05")
    monkeypatch.setenv("XION_PRICE_SLICE_SMALL_BUFFER", "0.03")
    monkeypatch.setenv("XION_PRICING_REVISION_ID", "gov-vote-0x1234")
    monkeypatch.setenv("XION_PRICING_LAST_REVIEWED_UTC_NS", "42")

    cfg = load_pricing_config_from_env()
    assert cfg.per_message_price_micro_XION == 5000
    assert cfg.variable_cost == pytest.approx(0.30)
    assert cfg.overhead_slice == pytest.approx(0.54)
    assert cfg.governance_revision_id == "gov-vote-0x1234"
    assert cfg.last_reviewed_utc_ns == 42


# --------------------------------------------------------- /pricing route


def _hermetic_cfg() -> PricingConfig:
    """A deterministic PricingConfig for endpoint tests."""
    return PricingConfig(
        per_message_price_micro_XION=1000,
        variable_cost=0.40,
        overhead_slice=0.44,
        improvement_slice=0.08,
        reserve_slice=0.05,
        small_buffer=0.03,
        last_reviewed_utc_ns=1_700_000_000_000_000_000,
        governance_revision_id="genesis-default-v1",
    )


def test_pricing_endpoint_returns_200_with_governance_shape(app_factory) -> None:
    """``GET /pricing`` returns HTTP 200 with the full posted-pricing
    shape — the five-slice breakdown, the governance revision id, and
    the last-reviewed timestamp."""
    app = app_factory(pricing_config=_hermetic_cfg())
    with TestClient(app) as client:
        r = client.get("/pricing")
    assert r.status_code == 200
    body = r.json()
    assert body["per_message_price_micro_XION"] == 1000
    assert body["currency_units"] == "micro_XION"
    assert body["five_slice"] == {
        "variable_cost": 0.40,
        "overhead_slice": 0.44,
        "improvement_slice": 0.08,
        "reserve_slice": 0.05,
        "small_buffer": 0.03,
    }
    assert body["last_reviewed_utc_ns"] == 1_700_000_000_000_000_000
    assert body["governance_revision_id"] == "genesis-default-v1"


def test_pricing_endpoint_validates_as_pricing_response(app_factory) -> None:
    """The wire body round-trips through ``PricingResponse`` — this is
    the content-free / field-allowlist guarantee: no extra fields,
    every field known, pydantic ``extra='forbid'`` holds."""
    app = app_factory(pricing_config=_hermetic_cfg())
    with TestClient(app) as client:
        r = client.get("/pricing")
    model = PricingResponse.model_validate(r.json())
    assert model.per_message_price_micro_XION == 1000
    assert model.five_slice.improvement_slice == pytest.approx(0.08)


def test_pricing_endpoint_is_always_live_regardless_of_floor(app_factory) -> None:
    """Constitutional promise: pricing transparency is NOT gated on
    the inference floor. A no_floor bootstrap still serves /pricing;
    only /chat goes 503 open_weights_floor_unsatisfied."""
    app = app_factory(pricing_config=_hermetic_cfg(), no_floor=True)
    with TestClient(app) as client:
        r = client.get("/pricing")
    assert r.status_code == 200
    assert r.json()["per_message_price_micro_XION"] == 1000


def test_pricing_endpoint_genesis_defaults_apply_with_no_env(
    app_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no ``pricing_config=`` override and no pricing env vars
    set (the autouse conftest wipes them), the endpoint serves the
    Genesis Defaults pinned in ``pricing.py``."""
    app = app_factory()
    with TestClient(app) as client:
        r = client.get("/pricing")
    assert r.status_code == 200
    body = r.json()
    assert body["governance_revision_id"] == "genesis-default-v1"
    assert body["currency_units"] == "micro_XION"
    # Slice invariants (Genesis Defaults are fixed in pricing.py).
    five = body["five_slice"]
    assert five["improvement_slice"] == pytest.approx(0.08)
    assert five["reserve_slice"] == pytest.approx(0.05)
    total = sum(five.values())
    assert abs(total - 1.0) < 1e-9


def test_pricing_endpoint_rejects_extra_fields_via_model() -> None:
    """A caller who deserialises the endpoint body through
    ``PricingResponse`` and tacks on an extra field must FAIL pydantic
    validation — content-free guarantee, identical posture to the
    Phase 5g-i ``ChatResponse``."""
    body = {
        "per_message_price_micro_XION": 1000,
        "currency_units": "micro_XION",
        "five_slice": {
            "variable_cost": 0.40,
            "overhead_slice": 0.44,
            "improvement_slice": 0.08,
            "reserve_slice": 0.05,
            "small_buffer": 0.03,
        },
        "last_reviewed_utc_ns": 42,
        "governance_revision_id": "genesis-default-v1",
        # Unknown field — must be rejected by extra='forbid'.
        "debug_commitment": "not-allowed",
    }
    with pytest.raises(Exception) as exc:  # noqa: BLE001 — pydantic.ValidationError
        PricingResponse.model_validate(body)
    assert "debug_commitment" in str(exc.value)


# ----------------------------------------------- lifespan fail-closed


def test_lifespan_refuses_to_start_on_bad_pricing_env(
    monkeypatch: pytest.MonkeyPatch,
    app_factory,
) -> None:
    """A misconfigured pricing split (does not sum to 1.0) causes the
    lifespan to fail — the app refuses to start, which is the correct
    constitutional posture. The failure is raised out of the
    ``TestClient`` context manager."""
    monkeypatch.setenv("XION_PRICE_SLICE_VARIABLE_COST", "0.80")
    # Leave the other env vars unset so Genesis Defaults apply;
    # 0.80 + 0.44 + 0.08 + 0.05 + 0.03 = 1.40 — over by 0.40.
    app = app_factory()  # no pricing_config override → env loader runs
    with pytest.raises(PricingConfigError, match="sum to 1.0"):
        with TestClient(app):
            # Never reached; the lifespan raises during startup.
            pass


def test_lifespan_default_timestamp_is_monotonic(
    app_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the operator does NOT post
    ``XION_PRICING_LAST_REVIEWED_UTC_NS``, the lifespan stamps the
    current ``time.time_ns()``. The exact value is non-deterministic,
    but it must be within a small window of ``time.time_ns()``
    measured inside the test."""
    before = time.time_ns()
    app = app_factory()
    with TestClient(app) as client:
        r = client.get("/pricing")
    after = time.time_ns()
    assert r.status_code == 200
    reviewed = r.json()["last_reviewed_utc_ns"]
    # Allow generous slack — CI schedulers sometimes take several
    # seconds between the two time_ns calls. The invariant is just
    # "the stamp falls in the window this test observed", not that
    # it is tight.
    assert before <= reviewed <= after + 5_000_000_000
