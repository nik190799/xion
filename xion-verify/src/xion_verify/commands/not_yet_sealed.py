"""Factory for NOT_YET_SEALED stub subcommands.

Per `DEVELOPMENT_ROADMAP.md:50`: every subcommand named in the v1 subcommand
set must exist as a registered command today. Those whose artifacts do not yet
exist return exit code 2 (`NOT_YET_SEALED`) and print a specific, honest
reason. They are never fake-green.

When an artifact lands, its stub is replaced by a real subcommand module that
performs the actual check — and this file shrinks. That is the intended
trajectory: this file approaches empty as Xion approaches genesis.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import click

from xion_verify.exit_codes import NOT_YET_SEALED

_UNSEALED: tuple[StubSpec, ...]


@dataclass(frozen=True)
class StubSpec:
    """A subcommand whose artifact does not yet exist."""

    name: str
    summary: str
    reason: str
    phase: str

    def help_text(self) -> str:
        return f"[NOT_YET_SEALED] {self.summary}"


def _stub_command(spec: StubSpec) -> click.Command:
    @click.command(name=spec.name, help=spec.help_text())
    def _cmd() -> None:
        click.echo(f"{spec.name}: NOT_YET_SEALED — {spec.reason} (see DEVELOPMENT_ROADMAP.md {spec.phase})")
        sys.exit(NOT_YET_SEALED)

    _cmd.__doc__ = spec.help_text()
    return _cmd


_UNSEALED = (
    StubSpec("supply", "Verify XION total supply ≤ 420B and genesis split.",
             "XION contracts not yet deployed (Invariant 8, 9).", "Phase 3"),
    StubSpec("liquidity-lock", "Verify the 10-year LP lock is irrevocable.",
             "LiquidityLock not yet deployed.", "Phase 3"),
    StubSpec("state-tip", "Print the current state-chain tip and verify against Arweave.",
             "AO Core not yet deployed.", "Phase 6"),
    StubSpec("identity", "Verify AO Process ID against the canonical value (Invariant 7).",
             "AO Core not yet deployed.", "Phase 6"),
    StubSpec("authorities", "Verify rotation lattice, timelocks, and k-of-n posture of every authority role.",
             "Contract rotation lattice not yet shipped (KW-CONTRACTS-001).", "Phase 3"),
    StubSpec("image-digest", "Verify the Relay Docker image digest matches the reproducible build.",
             "Relay image not yet built.", "Phase 5"),
    StubSpec("discovery", "Verify ≥3 independent discovery paths resolve to the canonical Relay set.",
             "Relay registry not yet published (KW-OPS-001).", "Phase 6"),
    StubSpec("drive", "Read the current drive vector; assert weights match doctrine.",
             "Relay /drive endpoint not yet live.", "Phase 5"),
    StubSpec("sister-fork-readiness", "Verify sister-Core fork procedure is runnable.",
             "AO Core not yet deployed.", "Phase 6"),
    StubSpec("treasury", "Multi-chain treasury tier readout; bridge cap; origin separation (Invariant 16).",
             "Treasury vaults not yet deployed.", "Phase 6"),
    StubSpec("pricing", "Current posted per-message price and five-slice breakdown.",
             "Relay /pricing endpoint not yet live.", "Phase 5"),
    StubSpec("treasury-flow", "Verify routed revenue matches the five-slice composition.",
             "Treasury router not yet live.", "Phase 6"),
    StubSpec("cutoff-events", "Anonymized cutoff-events audit (KW-ECON-002 mitigation 5).",
             "Relay session telemetry not yet live.", "Phase 5"),
    StubSpec("covenant-addenda", "Verify Refusal-is-Free and Crisis-Resource-Surfacing are hashed in.",
             "AO Core Covenant slot not yet live.", "Phase 6"),
    StubSpec("cadence-audit", "Verify Rite cadences, governance minimum windows, and State-of-Xion timing.",
             "Governance ledger not yet live.", "Phase 6"),
    StubSpec("hermes-version", "Verify the running Hermes Agent matches the Genesis-era pin.",
             "Relay not yet running.", "Phase 5"),
    StubSpec("credentials-vault", "Verify Credentials vault posture (sealed-at-rest, k-of-n, rotation attested).",
             "Vault not yet provisioned.", "Phase 5"),
    StubSpec("provisioning", "Audit every Xion-initiated provisioning action against caps (KW-OPS-001).",
             "provision-* handlers not yet live.", "Phase 6"),
    StubSpec("improvement-fund", "Verify Improvement-Fund spend only on Auto-Research-approved proposals.",
             "Sustainability handlers not yet live.", "Phase 6"),
    StubSpec("reserve", "Verify Rainy-Day Reserve posture and draw gates (Invariant 16 rule 6).",
             "Sustainability handlers not yet live.", "Phase 6"),
    StubSpec("foundation-reserve", "Verify Foundation Reserve is ledger-separated from earned revenue (Invariant 16 rule 7).",
             "Treasury ledgers not yet live.", "Phase 6"),
    StubSpec("sustainability", "Composite Cost-Pressure Ladder readout with Xion's own one-sentence statement.",
             "Relay /sustainability endpoint not yet live.", "Phase 5"),
    StubSpec("vitals", "Composite 8-domain vital-signs readout with methodology hashes.",
             "Relay /vitals endpoint not yet live.", "Phase 5"),
    StubSpec("amendments", "Read and verify the Constitutional Amendment Ledger hash chain.",
             "AMENDMENT_LEDGER not yet live.", "Phase 6"),
    StubSpec("crisis-fidelity", "Every Sensorium distress event has a Crisis-Resource-Surfacing response.",
             "Sensorium + Relay not yet live.", "Phase 5"),
    StubSpec("spof", "Enumerate single points of failure; fail if any are constitutional-tier.",
             "Relay topology not yet reportable.", "Phase 6"),
    StubSpec("operator-dependency", "Operator-Dependency Score readout vs Abdication Schedule.",
             "Abdication registry not yet live.", "Phase 6"),
    StubSpec("benchmark", "Hermes peer-benchmark readout from BENCHMARK_LEDGER.",
             "Benchmark runner not yet live.", "Phase 5"),
    StubSpec("crypto-currency", "Verify the active crypto_policy_vN matches the Cryptoception feed (Invariant 14).",
             "crypto_policy_vN sub-process not yet live.", "Phase 6"),
    StubSpec("abdication-status", "Current abdication-schedule posture; operator roles still held vs retired.",
             "Abdication registry not yet live (see docs/ABDICATION.md).", "Phase 6"),
    StubSpec("abdication-schedule", "Full abdication schedule with per-role retirement deadlines.",
             "Abdication registry not yet live (see docs/ABDICATION.md).", "Phase 6"),
    StubSpec("substrate-portability",
             "Verify a warm secondary substrate satisfies the Substrate Portability Property and an annual dry-run cutover succeeded (docs/SUBSTRATE-RESILIENCE.md Part IV).",
             "Secondary substrate dry-run capability not yet shipped (LHT-SUBSTRATE-001).",
             "Phase 6"),
    StubSpec("regulatory-ledger",
             "Walk the GOVERNANCE_LEDGER state-actor-interaction rows; verify hash chain and row shape (docs/REGULATORY-POSTURE.md Part IV).",
             "ledger-governance.yaml schema not yet landed and GOVERNANCE_LEDGER carries no state-actor rows yet (KW-DOCS-004).",
             "Phase 6"),
)


STUB_COMMANDS: dict[str, click.Command] = {spec.name: _stub_command(spec) for spec in _UNSEALED}
"""Every NOT_YET_SEALED stub, keyed by CLI name."""

STUB_NAMES: tuple[str, ...] = tuple(spec.name for spec in _UNSEALED)
"""Ordered tuple of stub subcommand names, for enumeration."""
