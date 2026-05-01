"""Root click group for xion-verify.

This is the only place every subcommand is named and registered. If a
subcommand is not wired here, it does not exist from the CLI's perspective,
regardless of what is in `commands/`. That discipline is intentional: it keeps
the surface area legible and enumerable.

`xion-verify --self-test` runs before any other subcommand resolution so that
a tampered verifier cannot claim to have passed anything else. The flag lives
at the root group rather than as a subcommand so `xion-verify --self-test` is
usable even when no arguments are given.
"""

from __future__ import annotations

import contextlib
import sys
from typing import Any

import click

from xion_verify import __version__
from xion_verify.commands import REGISTERED_COMMANDS
from xion_verify.commands.abdication import abdication_schedule, abdication_status
from xion_verify.commands.agent_cast import agent_cast
from xion_verify.commands.agent_souls import agent_souls
from xion_verify.commands.amendments import amendments
from xion_verify.commands.ao_deploy import identity, sister_fork_readiness, state_tip
from xion_verify.commands.ao_handlers import verify_ao_handlers
from xion_verify.commands.api_tokens import api_tokens
from xion_verify.commands.arbiter_determinism import arbiter_determinism
from xion_verify.commands.arbiter_up import arbiter_up
from xion_verify.commands.auto_research import auto_research
from xion_verify.commands.benchmark import benchmark
from xion_verify.commands.billing_credits_floor import billing_credits_floor
from xion_verify.commands.bridge_attest import bridge_attest
from xion_verify.commands.bridge_egress_cap import bridge_egress_cap
from xion_verify.commands.cadence_audit import cadence_audit
from xion_verify.commands.cast import cast_cmd
from xion_verify.commands.charter_signed import charter_signed
from xion_verify.commands.chat_streaming_fidelity import chat_streaming_fidelity
from xion_verify.commands.chutes_topup_multisig import chutes_topup_multisig
from xion_verify.commands.cognition import cognition
from xion_verify.commands.cognition_disjoint import cognition_disjoint
from xion_verify.commands.cognition_loop_bounded import cognition_loop_bounded
from xion_verify.commands.constitutional import (
    covenant,
    credentials,
    form,
    invariants,
    memory,
    resurrect,
    soul,
    unknowns,
)
from xion_verify.commands.contracts_deployed import authorities, liquidity_lock, supply
from xion_verify.commands.cost_pressure import cost_pressure
from xion_verify.commands.covenant_addenda import covenant_addenda
from xion_verify.commands.credentials_vault import credentials_vault
from xion_verify.commands.crisis_fidelity import crisis_fidelity
from xion_verify.commands.crypto_currency import crypto_currency
from xion_verify.commands.cutoff_events import cutoff_events
from xion_verify.commands.discovery import discovery
from xion_verify.commands.drive import drive
from xion_verify.commands.drive_vector import drive_vector
from xion_verify.commands.embedder_health import embedder_health
from xion_verify.commands.gateway_conformance import gateway_conformance
from xion_verify.commands.hermes_runtime import hermes_runtime
from xion_verify.commands.hermes_version import hermes_version
from xion_verify.commands.identity_bindings import identity_bindings
from xion_verify.commands.image_digest import image_digest
from xion_verify.commands.inference_provider_chutes import inference_provider_chutes
from xion_verify.commands.inference_sovereignty import inference_sovereignty
from xion_verify.commands.interaction_anchor import cli as interaction_anchor
from xion_verify.commands.ledgers import ledgers
from xion_verify.commands.links import links
from xion_verify.commands.local import local_cmd
from xion_verify.commands.mcp_export import mcp_export
from xion_verify.commands.measurement_vocabulary import measurement_vocabulary
from xion_verify.commands.memory_store_integrity import memory_store_integrity
from xion_verify.commands.modality_consent import modality_consent
from xion_verify.commands.model_promotion_discipline import model_promotion_discipline
from xion_verify.commands.nervous_system import nervous_system_cli
from xion_verify.commands.new import new_cmd
from xion_verify.commands.not_yet_sealed import STUB_COMMANDS, STUB_NAMES
from xion_verify.commands.operator_dependency import operator_dependency
from xion_verify.commands.pre_genesis import pre_genesis
from xion_verify.commands.presence import presence
from xion_verify.commands.pricing import pricing
from xion_verify.commands.prompt_isolation import prompt_isolation
from xion_verify.commands.provisioning import provisioning
from xion_verify.commands.provisioning_roles import provisioning_roles
from xion_verify.commands.rebuild import rebuild
from xion_verify.commands.refund_fidelity import refund_fidelity
from xion_verify.commands.refusal_is_free import refusal_is_free
from xion_verify.commands.refusal_rate import refusal_rate
from xion_verify.commands.registries import registries
from xion_verify.commands.regulatory_ledger import regulatory_ledger
from xion_verify.commands.replay_corpus import replay_corpus
from xion_verify.commands.request_fingerprint import request_fingerprint
from xion_verify.commands.rerank_improvement import rerank_improvement
from xion_verify.commands.research_sources import research_sources
from xion_verify.commands.schemas import schemas
from xion_verify.commands.self_test import run_self_test
from xion_verify.commands.sensorium_ledger import sensorium_ledger
from xion_verify.commands.shadow_divergence import shadow_divergence
from xion_verify.commands.shadow_relay import shadow_relay
from xion_verify.commands.skill_bounty import skill_bounty
from xion_verify.commands.soul_prompt import soul_prompt
from xion_verify.commands.sovereign_profile import sovereign_profile
from xion_verify.commands.spend_discipline import spend_discipline
from xion_verify.commands.spend_posture import spend_posture
from xion_verify.commands.spof import spof
from xion_verify.commands.state_chain import state_chain
from xion_verify.commands.substrate_portability import substrate_portability
from xion_verify.commands.substrates import substrates
from xion_verify.commands.supervisor_singleton import supervisor_singleton
from xion_verify.commands.sustainability import sustainability
from xion_verify.commands.tool_resolver_mcp import tool_resolver_mcp
from xion_verify.commands.topography import topography_cli
from xion_verify.commands.treasury import treasury
from xion_verify.commands.treasury_buckets import foundation_reserve, improvement_fund, reserve, treasury_flow
from xion_verify.commands.vessel_compact import vessel_compact
from xion_verify.commands.vessel_registry import vessel_registry
from xion_verify.commands.vitals import vitals
from xion_verify.commands.voice_form import voice_form
from xion_verify.commands.voice_property import voice_property
from xion_verify.commands.voice_sovereignty import voice_sovereignty
from xion_verify.commands.web_client import web_client
from xion_verify.commands.which_level import which_level
from xion_verify.exit_codes import FAIL, OK
from xion_verify.exit_codes import name as exit_code_name

_REAL_COMMANDS: dict[str, click.Command] = {
    "covenant": covenant,
    "invariants": invariants,
    "soul": soul,
    "soul-prompt": soul_prompt,
    "voice-property": voice_property,
    "form": form,
    "memory": memory,
    "resurrect": resurrect,
    "credentials": credentials,
    "unknowns": unknowns,
    "links": links,
    "schemas": schemas,
    "cognition": cognition,
    "hermes-runtime": hermes_runtime,
    "agent-souls": agent_souls,
    "agent-cast": agent_cast,
    "cognition-disjoint": cognition_disjoint,
    "registries": registries,
    "rebuild": rebuild,
    "replay-corpus": replay_corpus,
    "ledgers": ledgers,
    "drive": drive,
    "discovery": discovery,
    "drive-vector": drive_vector,
    "state-chain": state_chain,
    "state-tip": state_tip,
    "identity": identity,
    "sister-fork-readiness": sister_fork_readiness,
    "supply": supply,
    "liquidity-lock": liquidity_lock,
    "authorities": authorities,
    "arbiter-up": arbiter_up,
    "image-digest": image_digest,
    "arbiter-determinism": arbiter_determinism,
    "refusal-rate": refusal_rate,
    "pricing": pricing,
    "treasury": treasury,
    "treasury-flow": treasury_flow,
    "improvement-fund": improvement_fund,
    "reserve": reserve,
    "foundation-reserve": foundation_reserve,
    "refund-fidelity": refund_fidelity,
    "refusal-is-free": refusal_is_free,
    "crisis-fidelity": crisis_fidelity,
    "interaction-anchor": interaction_anchor,
    "inference-sovereignty": inference_sovereignty,
    "voice-sovereignty": voice_sovereignty,
    "voice-form": voice_form,
    "substrate-portability": substrate_portability,
    "regulatory-ledger": regulatory_ledger,
    "abdication-status": abdication_status,
    "abdication-schedule": abdication_schedule,
    "amendments": amendments,
    "covenant-addenda": covenant_addenda,
    "cadence-audit": cadence_audit,
    "sensorium-ledger": sensorium_ledger,
    "spof": spof,
    "credentials-vault": credentials_vault,
    "hermes-version": hermes_version,
    "cutoff-events": cutoff_events,
    "api-tokens": api_tokens,
    "web-client": web_client,
    "chat-streaming-fidelity": chat_streaming_fidelity,
    "supervisor-singleton": supervisor_singleton,
    "vitals": vitals,
    "sustainability": sustainability,
    "new": new_cmd,
    "local": local_cmd,
    "cast": cast_cmd,
    "operator-dependency": operator_dependency,
    "benchmark": benchmark,
    "crypto-currency": crypto_currency,
    "research-sources": research_sources,
    "pre-genesis": pre_genesis,
    "shadow-relay": shadow_relay,
    "shadow-divergence": shadow_divergence,
    "cost-pressure": cost_pressure,
    "substrates": substrates,
    "auto-research": auto_research,
    "skill-bounty": skill_bounty,
    "charter-signed": charter_signed,
    "ao-handlers": verify_ao_handlers,
    "provisioning": provisioning,
    "provisioning-roles": provisioning_roles,
    "which-level": which_level,
    "identity-bindings": identity_bindings,
    "mcp-export": mcp_export,
    "presence": presence,
    "modality-consent": modality_consent,
    "nervous-system": nervous_system_cli,
    "topography": topography_cli,
    "measurement-vocabulary": measurement_vocabulary,
    "vessel-compact": vessel_compact,
    "vessel-registry": vessel_registry,
    "spend-posture": spend_posture,
    "spend-discipline": spend_discipline,
    "inference-provider-chutes": inference_provider_chutes,
    "sovereign-profile": sovereign_profile,
    "billing-credits-floor": billing_credits_floor,
    "chutes-topup-multisig": chutes_topup_multisig,
    "model-promotion-discipline": model_promotion_discipline,
    "request-fingerprint": request_fingerprint,
    "memory-store-integrity": memory_store_integrity,
    "embedder-health": embedder_health,
    "rerank-improvement": rerank_improvement,
    "tool-resolver-mcp": tool_resolver_mcp,
    "prompt-isolation": prompt_isolation,
    "cognition-loop-bounded": cognition_loop_bounded,
    "bridge-attest": bridge_attest,
    "bridge-egress-cap": bridge_egress_cap,
    "gateway-conformance": gateway_conformance,
}


def _build_root() -> click.Group:
    @click.group(
        name="xion-verify",
        help=(
            "Third-party verifier for Xion's constitutional claims.\n\n"
            "Every subcommand is deterministic: same input, same output. "
            "A disagreement between two independent runs against the same state is an alert. "
            "Trust by structure, not by promise."
        ),
        context_settings={"help_option_names": ["-h", "--help"]},
        invoke_without_command=True,
    )
    @click.version_option(__version__, prog_name="xion-verify")
    @click.option(
        "--self-test",
        "self_test",
        is_flag=True,
        help="Verify the verifier's own source against PINNED_HASH.txt; run before trusting other output.",
    )
    @click.option(
        "--update",
        "update",
        is_flag=True,
        help="With --self-test: overwrite PINNED_HASH.txt (requires --i-understand).",
    )
    @click.option(
        "--i-understand",
        "i_understand",
        is_flag=True,
        help="Required alongside --self-test --update.",
    )
    @click.pass_context
    def root(
        ctx: click.Context,
        self_test: bool,
        update: bool,
        i_understand: bool,
    ) -> None:
        if self_test:
            code, message = run_self_test(update=update, i_understand=i_understand)
            click.echo(message, err=(code != OK))
            ctx.exit(code)
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())
            ctx.exit(OK)

    for cli_name, cmd in _REAL_COMMANDS.items():
        root.add_command(cmd, name=cli_name)
    for cli_name in STUB_NAMES:
        root.add_command(STUB_COMMANDS[cli_name], name=cli_name)

    _register_all(root)
    _verify_registry(root)
    return root


def _register_all(root: click.Group) -> None:
    @root.command(
        name="all",
        help="Run every registered subcommand; exit 0 only if every one returned OK (NOT_YET_SEALED counts as non-OK).",
    )
    @click.option("--allow-not-yet-sealed", is_flag=True,
                  help="Treat NOT_YET_SEALED as OK for this run (pre-genesis convenience; never use in CI gating).")
    @click.pass_context
    def _all(ctx: click.Context, allow_not_yet_sealed: bool) -> None:
        results: list[tuple[str, int]] = []
        for cli_name in REGISTERED_COMMANDS:
            cmd = root.commands.get(cli_name)
            if cmd is None:
                click.echo(f"all: FAIL: subcommand '{cli_name}' declared in registry but not wired", err=True)
                ctx.exit(FAIL)
            code = _invoke_subcommand_for_all(cmd)
            results.append((cli_name, code))

        non_ok = [(n, c) for n, c in results if c != OK]
        if allow_not_yet_sealed:
            from xion_verify.exit_codes import NOT_YET_SEALED
            non_ok = [(n, c) for n, c in non_ok if c != NOT_YET_SEALED]

        click.echo("")
        click.echo("--- xion-verify all ---")
        for n, c in results:
            click.echo(f"  {n}: {exit_code_name(c)}")
        if non_ok:
            click.echo(f"all: FAIL: {len(non_ok)} non-OK subcommand(s)", err=True)
            ctx.exit(FAIL)
        click.echo("all: OK (every registered subcommand returned OK)")
        ctx.exit(OK)


def _invoke_subcommand_for_all(cmd: click.Command) -> int:
    """Invoke a subcommand in-process, returning its exit code without exiting."""
    try:
        cmd.main(args=[], standalone_mode=False)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else FAIL
        return code
    except click.ClickException as exc:
        exc.show()
        return FAIL
    return OK


def _verify_registry(root: click.Group) -> None:
    """Fail at import time if the registry and the wired commands disagree."""
    registered = set(REGISTERED_COMMANDS)
    wired = set(root.commands.keys()) - {"all"}
    missing_from_wiring = registered - wired
    extra_wired = wired - registered
    if missing_from_wiring or extra_wired:
        raise RuntimeError(
            "xion-verify registry mismatch: "
            f"declared-but-not-wired={sorted(missing_from_wiring)} "
            f"wired-but-not-declared={sorted(extra_wired)}. "
            "Update xion_verify/commands/__init__.py REGISTERED_COMMANDS."
        )


root = _build_root()


def main(argv: list[str] | None = None) -> Any:
    _force_utf8_io()
    return root.main(args=argv, prog_name="xion-verify")


def _force_utf8_io() -> None:
    """Ensure CLI output is UTF-8 on every platform.

    Xion's doctrine uses em-dashes and section signs; these must render
    identically on Linux, macOS, and Windows. Without this, a Windows
    terminal defaulting to cp1252 raises UnicodeEncodeError.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(OSError, ValueError):
                reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    sys.exit(main())
