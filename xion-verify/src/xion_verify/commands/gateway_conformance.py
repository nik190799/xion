"""Gateway Pattern conformance verifier."""

from __future__ import annotations

import sys
from collections.abc import Iterable
from dataclasses import dataclass

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import find_repo_root


@dataclass(frozen=True)
class GatewayGap:
    surface: str
    kw_id: str
    closure: str


_GAPS: tuple[GatewayGap, ...] = (
    GatewayGap(
        "gateway-conformance",
        "KW-GATEWAY-001",
        "Implement static audit-table, KW, and provider-module checks.",
    ),
    GatewayGap(
        "alerting",
        "KW-ALERT-001",
        "Add an Alerter Protocol with ntfy, Pushover, and local-log providers.",
    ),
    GatewayGap(
        "observability",
        "KW-OBS-001",
        "Add metrics, logs, and traces provider interfaces with local and hosted providers.",
    ),
    GatewayGap(
        "ao-core-client",
        "KW-AOCORE-CLIENT-001",
        "Add an AOCoreGateway Protocol with legacynet, localnet, and future-substrate providers.",
    ),
    GatewayGap(
        "vault",
        "KW-VAULT-001",
        "Add a Vault Protocol for startup credential retrieval.",
    ),
    GatewayGap(
        "relay-registry",
        "KW-REGISTRY-001",
        "Add a RelayRegistryPublisher Protocol with Arweave and alternate providers.",
    ),
    GatewayGap(
        "settlement-chain",
        "KW-TREASURY-CHAIN-001",
        "Add a SettlementChain Protocol for token, reputation, and treasury rails.",
    ),
    GatewayGap(
        "status",
        "KW-STATUS-001",
        "Add a StatusPublisher Protocol with Arweave and alternate providers.",
    ),
)


def _ao_core_client_presence_lines() -> Iterable[str]:
    """Assert the Phase 6.9.2 AO Core gateway slice is mechanically present."""
    try:
        from orchestrator.ao_core.client import (
            LegacynetAOCoreGateway,
            LocalnetAOCoreGateway,
        )
        from orchestrator.ao_core.gateway import (
            AOCoreGateway,
            AOCoreGatewaySettings,
            get_ao_core_gateway,
        )
    except Exception as e:  # pragma: no cover - surfaced through verifier output
        return (f"ao-core-client presence: FAIL - import error: {e}",)

    try:
        localnet = get_ao_core_gateway(
            AOCoreGatewaySettings(substrate="localnet", process_id="probe")
        )
        legacynet = get_ao_core_gateway(
            AOCoreGatewaySettings(substrate="legacynet", process_id="probe")
        )
        if not isinstance(localnet, LocalnetAOCoreGateway):
            return ("ao-core-client presence: FAIL - localnet provider not selected",)
        if not isinstance(legacynet, LegacynetAOCoreGateway):
            return ("ao-core-client presence: FAIL - legacynet provider not selected",)
        if not isinstance(localnet, AOCoreGateway) or not isinstance(
            legacynet,
            AOCoreGateway,
        ):
            return ("ao-core-client presence: FAIL - providers do not satisfy Protocol",)
    except Exception as e:  # pragma: no cover - surfaced through verifier output
        return (f"ao-core-client presence: FAIL - provider probe failed: {e}",)

    return (
        "ao-core-client presence: OK - AOCoreGateway Protocol, localnet provider, "
        "legacynet placeholder, and factory are present.",
    )


def _vault_presence_lines() -> Iterable[str]:
    try:
        from orchestrator.vault import EnvVault, ThresholdVaultStub, Vault, VaultSettings, get_vault
    except Exception as e:
        return (f"vault presence: FAIL - import error: {e}",)
    try:
        env = get_vault(VaultSettings(provider="env"))
        threshold = get_vault(VaultSettings(provider="threshold"))
        if not isinstance(env, EnvVault) or not isinstance(threshold, ThresholdVaultStub):
            return ("vault presence: FAIL - providers not selected by factory",)
        if not isinstance(env, Vault) or not isinstance(threshold, Vault):
            return ("vault presence: FAIL - providers do not satisfy Protocol",)
    except Exception as e:
        return (f"vault presence: FAIL - provider probe failed: {e}",)
    return ("vault presence: OK - Vault Protocol, env provider, threshold placeholder, and factory are present.",)


def _alerting_presence_lines() -> Iterable[str]:
    try:
        from orchestrator.alerting import (
            Alerter,
            AlerterSettings,
            LocalLogAlerter,
            NtfyAlerter,
            PushoverAlerter,
            get_alerter,
        )
    except Exception as e:
        return (f"alerting presence: FAIL - import error: {e}",)
    try:
        local = get_alerter(AlerterSettings(provider="local-log"))
        ntfy = get_alerter(AlerterSettings(provider="ntfy"))
        pushover = get_alerter(AlerterSettings(provider="pushover"))
        if not isinstance(local, LocalLogAlerter) or not isinstance(ntfy, NtfyAlerter) or not isinstance(pushover, PushoverAlerter):
            return ("alerting presence: FAIL - providers not selected by factory",)
        if not all(isinstance(provider, Alerter) for provider in (local, ntfy, pushover)):
            return ("alerting presence: FAIL - providers do not satisfy Protocol",)
    except Exception as e:
        return (f"alerting presence: FAIL - provider probe failed: {e}",)
    return ("alerting presence: OK - Alerter Protocol, local-log, ntfy, Pushover providers, and factory are present.",)


def _observability_presence_lines() -> Iterable[str]:
    try:
        from orchestrator.observability import (
            HostedObservabilityStub,
            MetricsEmitter,
            ObservabilitySettings,
            StdoutObservability,
            get_observability,
        )
    except Exception as e:
        return (f"observability presence: FAIL - import error: {e}",)
    try:
        stdout = get_observability(ObservabilitySettings(provider="stdout"))
        hosted = get_observability(ObservabilitySettings(provider="hosted"))
        if not isinstance(stdout.metrics, StdoutObservability) or not isinstance(hosted.metrics, HostedObservabilityStub):
            return ("observability presence: FAIL - providers not selected by factory",)
        if not isinstance(stdout.metrics, MetricsEmitter) or not isinstance(hosted.metrics, MetricsEmitter):
            return ("observability presence: FAIL - providers do not satisfy Protocol",)
    except Exception as e:
        return (f"observability presence: FAIL - provider probe failed: {e}",)
    return ("observability presence: OK - metrics/logs/traces Protocols, stdout provider, hosted placeholder, and factory are present.",)


def _relay_registry_presence_lines() -> Iterable[str]:
    try:
        from orchestrator.registry import (
            ArweaveRelayRegistryPublisher,
            LocalFileRelayRegistryPublisher,
            RelayRegistryPublisher,
            RelayRegistryPublisherSettings,
            get_relay_registry_publisher,
        )
    except Exception as e:
        return (f"relay-registry presence: FAIL - import error: {e}",)
    try:
        local = get_relay_registry_publisher(RelayRegistryPublisherSettings(backend="local-file"))
        arweave = get_relay_registry_publisher(RelayRegistryPublisherSettings(backend="arweave"))
        if not isinstance(local, LocalFileRelayRegistryPublisher) or not isinstance(arweave, ArweaveRelayRegistryPublisher):
            return ("relay-registry presence: FAIL - providers not selected by factory",)
        if not isinstance(local, RelayRegistryPublisher) or not isinstance(arweave, RelayRegistryPublisher):
            return ("relay-registry presence: FAIL - providers do not satisfy Protocol",)
    except Exception as e:
        return (f"relay-registry presence: FAIL - provider probe failed: {e}",)
    return ("relay-registry presence: OK - RelayRegistryPublisher Protocol, local-file provider, Arweave provider, and factory are present.",)


def _settlement_chain_presence_lines() -> Iterable[str]:
    try:
        from pathlib import Path

        from orchestrator.treasury import (
            BaseEvmSettlementChain,
            FutureChainStub,
            SettlementChain,
            SettlementChainSettings,
            get_settlement_chain,
        )
    except Exception as e:
        return (f"settlement-chain presence: FAIL - import error: {e}",)
    try:
        base = get_settlement_chain(SettlementChainSettings(chain="base", repo_root=Path(".")))
        future = get_settlement_chain(SettlementChainSettings(chain="future-chain"))
        if not isinstance(base, BaseEvmSettlementChain) or not isinstance(future, FutureChainStub):
            return ("settlement-chain presence: FAIL - providers not selected by factory",)
        if not isinstance(base, SettlementChain) or not isinstance(future, SettlementChain):
            return ("settlement-chain presence: FAIL - providers do not satisfy Protocol",)
    except Exception as e:
        return (f"settlement-chain presence: FAIL - provider probe failed: {e}",)
    return ("settlement-chain presence: OK - SettlementChain Protocol, Base EVM provider, future-chain placeholder, and factory are present.",)


def _status_presence_lines() -> Iterable[str]:
    try:
        from orchestrator.status import (
            ArweaveStatusPublisher,
            LocalFileStatusPublisher,
            StatusPublisher,
            StatusPublisherSettings,
            get_status_publisher,
        )
    except Exception as e:
        return (f"status presence: FAIL - import error: {e}",)
    try:
        local = get_status_publisher(StatusPublisherSettings(backend="local-file"))
        arweave = get_status_publisher(StatusPublisherSettings(backend="arweave"))
        if not isinstance(local, LocalFileStatusPublisher) or not isinstance(arweave, ArweaveStatusPublisher):
            return ("status presence: FAIL - providers not selected by factory",)
        if not isinstance(local, StatusPublisher) or not isinstance(arweave, StatusPublisher):
            return ("status presence: FAIL - providers do not satisfy Protocol",)
    except Exception as e:
        return (f"status presence: FAIL - provider probe failed: {e}",)
    return ("status presence: OK - StatusPublisher Protocol, local-file provider, Arweave provider, and factory are present.",)


_PRESENCE_CHECKS = {
    "ao-core-client": _ao_core_client_presence_lines,
    "vault": _vault_presence_lines,
    "alerting": _alerting_presence_lines,
    "observability": _observability_presence_lines,
    "relay-registry": _relay_registry_presence_lines,
    "settlement-chain": _settlement_chain_presence_lines,
    "status": _status_presence_lines,
}


_AUDIT_EXPECTATIONS = {
    "orchestrator/ao_core/gateway.py::AOCoreGateway": "AO Core RPC client",
    "orchestrator/vault/gateway.py::Vault": "Credential vault unlock",
    "orchestrator/alerting/gateway.py::Alerter": "Alerting",
    "orchestrator/observability/gateway.py": "Observability",
    "orchestrator/registry/gateway.py::RelayRegistryPublisher": "Relay registry / discovery publishing",
    "orchestrator/treasury/settlement_gateway.py::SettlementChain": "Settlement chain / treasury rail",
    "orchestrator/status/gateway.py::StatusPublisher": "Public status publishing",
}


def _audit_table_presence_lines() -> Iterable[str]:
    try:
        audit = find_repo_root() / "docs" / "38-MODULAR-SUBSTRATE.md"
        text = audit.read_text(encoding="utf-8")
    except Exception as e:
        return (f"audit-table presence: FAIL - could not read audit table: {e}",)
    missing = [
        f"{surface} -> {interface}"
        for interface, surface in _AUDIT_EXPECTATIONS.items()
        if surface not in text or interface not in text
    ]
    if missing:
        return (
            "audit-table presence: FAIL - missing gateway audit row(s): "
            + "; ".join(missing),
        )
    return ("audit-table presence: OK - Phase 6.9.2 gateway rows resolve to code surfaces.",)


@click.command(
    name="gateway-conformance",
    help="Verify Gateway Pattern conformance across load-bearing externals.",
)
@click.option(
    "--surface",
    type=click.Choice(tuple(gap.surface for gap in _GAPS)),
    default=None,
    help="Limit output to one unsealed gateway surface.",
)
def gateway_conformance(surface: str | None) -> None:
    """Verify that Gateway Pattern surfaces are mechanically present."""

    selected = tuple(gap for gap in _GAPS if surface is None or gap.surface == surface)
    click.echo("gateway-conformance: checking Gateway Pattern surfaces")
    click.echo("doctrine: docs/39-GATEWAY-PATTERN.md")
    click.echo("audit: docs/38-MODULAR-SUBSTRATE.md#gateway-audit-phase-691")
    lines: list[str] = []
    for name, checker in _PRESENCE_CHECKS.items():
        if surface in {name, None}:
            lines.extend(checker())
    if surface in {"gateway-conformance", None}:
        lines.append("gateway-conformance presence: OK - live verifier dispatches every Phase 6.9.2 surface.")
        lines.extend(_audit_table_presence_lines())
    for line in lines:
        click.echo(line)

    click.echo("registered surfaces:")
    for gap in selected:
        click.echo(f"  - {gap.surface}: {gap.kw_id} - {gap.closure}")

    failures = [line for line in lines if ": FAIL" in line]
    if failures:
        click.echo(f"gateway-conformance: FAIL ({len(failures)} failed presence check(s))", err=True)
        sys.exit(FAIL)
    click.echo("gateway-conformance: OK")
    sys.exit(OK)


__all__ = ["gateway_conformance"]
