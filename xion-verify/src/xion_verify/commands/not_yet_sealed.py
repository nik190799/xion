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
    StubSpec("research-spend",
             "Verify RESEARCH_SPEND_LEDGER rows and Improvement Fund authorization (docs/27-RESEARCH-SPEND.md).",
             "RESEARCH_SPEND_LEDGER writer and on-chain Improvement Fund balance not yet live.",
             "Phase 6+"),
    StubSpec("media-provenance",
             "Verify signed vessel media bundles against Relay keys, Core lineage, Covenant hash, Voice/Form hashes, and edit history.",
             "No signed podcast, livestream, audio/video, or AR bundle exists yet; verifier promotes when the first reference bundle lands.",
             "Phase 6.7"),
)


STUB_COMMANDS: dict[str, click.Command] = {spec.name: _stub_command(spec) for spec in _UNSEALED}
"""Every NOT_YET_SEALED stub, keyed by CLI name."""

STUB_NAMES: tuple[str, ...] = tuple(spec.name for spec in _UNSEALED)
"""Ordered tuple of stub subcommand names, for enumeration."""
