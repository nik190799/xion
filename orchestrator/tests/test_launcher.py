from __future__ import annotations

from fastapi.testclient import TestClient

from orchestrator.api.admission import AdmissionConfig
from orchestrator.api.launcher import build_app
from orchestrator.api.pricing import PricingConfig
from orchestrator.billing.config import BillingConfig
from orchestrator.inference_router import (
    InferenceRouter,
    OpenWeightsFloorStub,
    default_manifest_path,
)
from orchestrator.relay import Relay


def test_launcher_cast_pool_defaults_on_and_honors_env_false(monkeypatch) -> None:
    monkeypatch.delenv("XION_CAST_POOL_ON_BOOT", raising=False)
    _, app = build_app()
    assert app.state.deps.cast_pool_on_boot is True

    monkeypatch.setenv("XION_CAST_POOL_ON_BOOT", "false")
    _, app = build_app()
    assert app.state.deps.cast_pool_on_boot is False


def test_launcher_builds_live_relay_surface(tmp_path) -> None:
    router = InferenceRouter(manifest_path=default_manifest_path())
    router.register(OpenWeightsFloorStub(provider_id="sentinel-llm-v0"))

    relay = Relay(
        safety_ledger_path=tmp_path / "SAFETY_LEDGER.jsonl",
        sensorium_ledger_path=tmp_path / "SENSORIUM_LEDGER.jsonl",
        request_ledger_path=tmp_path / "REQUEST_LEDGER.jsonl",
    )
    _, app = build_app(
        relay=relay,
        router=router,
        sensorium_ledger_path=tmp_path / "SENSORIUM_LEDGER.jsonl",
        tick_cadence_s=0.01,
        cast_pool_on_boot=False,
        pricing_config=PricingConfig(
            per_message_price_micro_XION=1000,
            variable_cost=0.40,
            overhead_slice=0.44,
            improvement_slice=0.08,
            reserve_slice=0.05,
            small_buffer=0.03,
            modality_costs={
                "stream_visual": 0,
                "stream_vitals": 0,
                "stream_voice": 0,
                "stream_memory": 0,
            },
            last_reviewed_utc_ns=0,
            governance_revision_id="launcher-test",
        ),
        billing_config=BillingConfig(
            billing_required=False,
            allow_x402=True,
            operator_attestation_secret=None,
            payment_ledger_path=tmp_path / "PAYMENT_LEDGER.jsonl",
            architecture_sha256="0" * 64,
        ),
        admission_config=AdmissionConfig(
            require_bearer=False,
            tokens={},
            rate_budget=60,
            rate_window_s=60,
            health_rate_budget=120,
            api_host="127.0.0.1",
            api_port=8000,
            tls_cert_path=None,
            tls_key_path=None,
        ),
    )

    with TestClient(app) as client:
        health = client.get("/health")
        pricing = client.get("/pricing")
        self_response = client.get("/self")

    assert health.status_code == 200, health.text
    assert health.json()["relay_healthy"] is True
    assert health.json()["arbiter_healthy"] is True
    assert "watchdog_fires_recent" in health.json()

    assert pricing.status_code == 200, pricing.text
    assert pricing.json()["per_message_price_micro_XION"] == 1000
    assert "five_slice" in pricing.json()

    assert self_response.status_code == 200, self_response.text
    for key in ("topography", "sensorium", "vitals", "governance", "as_of_utc_ns"):
        assert key in self_response.json()
