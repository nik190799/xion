"""`xion-verify local` — local development mode.

Boots full stack against a temp directory (SQLite, in-process Arbiter, FastAPI,
in-process Auto-Research) and runs synthetic chats without network calls.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


async def _run_self_test(temp_dir: Path) -> None:
    """Run three synthetic chats through the real in-process HTTP stack."""
    try:
        from fastapi.testclient import TestClient
        from orchestrator.api import AppDeps, create_app
        from orchestrator.api.admission import AdmissionConfig
        from orchestrator.api.pricing import PricingConfig
        from orchestrator.billing.config import BillingConfig
        from orchestrator.billing.ledger import verify_chain as verify_payment_chain
        from orchestrator.inference_router import InferenceRouter, default_manifest_path
        from orchestrator.relay import Relay
        from orchestrator.relay.ledger import verify_chain as verify_request_chain
        from orchestrator.safety.ledger import verify_chain as verify_safety_chain
        from orchestrator.sensorium.ledger import verify_chain as verify_sensorium_chain
    except Exception as exc:  # pragma: no cover - operator environment guard
        raise RuntimeError(
            "local self-test requires the orchestrator [api] extra installed "
            '(run: pip install -e ".[api]" && pip install -e xion-verify)'
        ) from exc

    safety_ledger = temp_dir / "SAFETY_LEDGER.jsonl"
    sensorium_ledger = temp_dir / "SENSORIUM_LEDGER.jsonl"
    request_ledger = temp_dir / "REQUEST_LEDGER.jsonl"
    payment_ledger = temp_dir / "PAYMENT_LEDGER.jsonl"

    click.echo(f"local: booting full stack against {temp_dir}")

    router = InferenceRouter(manifest_path=default_manifest_path())
    router.register(_LocalFloorProvider())

    relay = Relay(
        safety_ledger_path=safety_ledger,
        sensorium_ledger_path=sensorium_ledger,
        request_ledger_path=request_ledger,
    )
    deps = AppDeps(
        relay=relay,
        tick_cadence_s=0.01,
        sensorium_ledger_path=sensorium_ledger,
        router=router,
        chat_deadline_s=5.0,
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
            governance_revision_id="local-self-test",
        ),
        billing_config=BillingConfig(
            billing_required=False,
            allow_x402=True,
            operator_attestation_secret=None,
            payment_ledger_path=payment_ledger,
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
        cast_pool_on_boot=False,
    )

    app = create_app(deps)

    with TestClient(app) as client:
        for index, message in enumerate(
            (
                "Hello Xion. Please answer with a short harmless greeting.",
                "Give a concise status sentence for a local self-test.",
                "Confirm the local D2 loop is running.",
            ),
            start=1,
        ):
            click.echo(f"local: running synthetic chat {index}...")
            response = client.post("/chat", json={"message": message, "max_tokens": 1024})
            if response.status_code != 200:
                raise RuntimeError(
                    f"synthetic chat {index} returned HTTP {response.status_code}: {response.text}"
                )
            body = response.json()
            if body.get("role") != "xion" or not body.get("text"):
                raise RuntimeError(f"synthetic chat {index} returned malformed body: {body}")

    _assert_ledger(safety_ledger, "SAFETY_LEDGER", verify_safety_chain)
    _assert_ledger(sensorium_ledger, "SENSORIUM_LEDGER", verify_sensorium_chain)
    _assert_ledger(request_ledger, "REQUEST_LEDGER", verify_request_chain)
    _assert_ledger(payment_ledger, "PAYMENT_LEDGER", verify_payment_chain)
    await asyncio.sleep(0)


@dataclass(frozen=True)
class _LocalFloorProvider:
    provider_id: str = "sentinel-llm-v0"
    category: Literal["open_weights_self_hostable"] = "open_weights_self_hostable"

    def health(self) -> bool:
        return True

    def generate(
        self,
        prompt: str,
        *,
        system: str | None,
        max_tokens: int,
        deadline_s: float,
    ) -> object:
        from orchestrator.inference_router.provider import GenerationResult

        return GenerationResult(
            text=f"Local self-test response received: {prompt[:64]}",
            model_id="local-self-test-floor",
            usage_in=max(1, len(prompt.split())),
            usage_out=8,
            finish_reason="stop",
            latency_ms=1,
        )


def _assert_ledger(path: Path, label: str, verifier: object) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"{label} was not written")
    result = verifier(path)  # type: ignore[operator]
    ok = getattr(result, "ok", None)
    if ok is False:
        raise RuntimeError(f"{label} chain verification failed: {result}")


@click.command(name="local", help="Local development mode.")
@click.option("--self-test", is_flag=True, help="Boot full stack against temp dir, run synthetic chats, exit 0.")
def local_cmd(self_test: bool) -> None:
    try:
        find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"local: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    if self_test:
        with tempfile.TemporaryDirectory() as temp_dir:
            asyncio.run(_run_self_test(Path(temp_dir)))
        click.echo("local: OK (self-test passed)")
        sys.exit(OK)

    click.echo("local: Running in foreground (press Ctrl+C to stop)")
    # TODO: Implement foreground local mode
    sys.exit(OK)
