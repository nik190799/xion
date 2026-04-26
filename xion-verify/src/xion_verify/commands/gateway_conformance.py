"""Gateway Pattern conformance verifier stub.

Phase 6.9.1 reserves the command name and prints the audit scope. The actual
static verifier lands in Phase 6.9.2, after the doctrine and KW gaps exist.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import click

from xion_verify.exit_codes import NOT_YET_SEALED


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


@click.command(
    name="gateway-conformance",
    help="[NOT_YET_SEALED] Verify Gateway Pattern conformance across load-bearing externals.",
)
@click.option(
    "--surface",
    type=click.Choice(tuple(gap.surface for gap in _GAPS)),
    default=None,
    help="Limit output to one unsealed gateway surface.",
)
def gateway_conformance(surface: str | None) -> None:
    """Print the unsealed Gateway Pattern scope and exit NOT_YET_SEALED."""

    selected = tuple(gap for gap in _GAPS if surface is None or gap.surface == surface)
    click.echo(
        "gateway-conformance: NOT_YET_SEALED - Gateway Pattern doctrine is sealed, "
        "but the cross-cutting verifier is not live yet."
    )
    click.echo("doctrine: docs/39-GATEWAY-PATTERN.md")
    click.echo("audit: docs/38-MODULAR-SUBSTRATE.md#gateway-audit-phase-691")
    click.echo("open gaps:")
    for gap in selected:
        click.echo(f"  - {gap.surface}: {gap.kw_id} - {gap.closure}")
    sys.exit(NOT_YET_SEALED)


__all__ = ["gateway_conformance"]
