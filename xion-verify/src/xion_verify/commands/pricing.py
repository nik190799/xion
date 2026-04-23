"""``xion-verify pricing`` — posted five-slice readout (Phase 5g-iii live).

Promoted from NOT_YET_SEALED on the 5g-iii landing. The verifier loads
the same ``PricingConfig`` the orchestrator's lifespan loads, validates
its constitutional invariants, and prints a stable human-readable
summary of the posted price.

The loader is authoritative: it enforces (at
``orchestrator.api.pricing.PricingConfig.__post_init__``) the property
"five slices sum to 1.0 within tolerance, each slice is in [0, 1],
governance_revision_id is non-empty ≤ 128 chars, posted price is
non-negative, last_reviewed_utc_ns is non-negative". A configuration
that fails any of these is a constitutional violation of
``docs/07-ECONOMY.md`` § "Five-slice posted price" and the orchestrator
will refuse to start. This verifier mirrors that discipline: it imports
the same loader and reports ``FAIL`` with the specific reason on any
failure.

What this verifier does NOT do (with an honest pointer):

  * It does not walk the PAYMENT_LEDGER or verify that rows carry a
    ``posted_price_XION`` field matching this config. That is the
    scope of ``xion-verify refusal-is-free``, which joins the two
    ledgers on ``correlation_id`` and asserts money-shape symmetry.
  * It does not check that the running ``GET /pricing`` endpoint
    returns the same body. Endpoint-vs-config drift is a deployment
    concern for the operator's runbook; this verifier checks config
    itself.
  * It does not validate that the posted price is "correct" (market-
    calibrated, Covenant-compatible). 5g-iii posts operator numbers;
    Phase 6 governance and the Treasury router add the live
    price-vs-cost verifier.

Exit codes:

  0 OK              pricing config loads and passes every structural
                    invariant; summary printed.
  1 FAIL            loader raises ``PricingConfigError`` or any other
                    exception; message carries the specific reason.
  2 NOT_YET_SEALED  never returned (the config always loads at least
                    to Genesis Defaults; there is no half-sealed
                    state for 5g-iii).
"""

from __future__ import annotations

import click

from xion_verify.exit_codes import FAIL, OK


def _fail(message: str) -> None:
    click.echo(f"pricing: FAIL: {message}", err=True)
    raise SystemExit(FAIL)


@click.command(name="pricing")
def pricing() -> None:
    """Read the posted pricing config and print the five-slice breakdown."""

    try:
        from orchestrator.api.pricing import (
            PricingConfigError,
            load_pricing_config_from_env,
        )
    except Exception as exc:
        _fail(
            f"cannot import orchestrator.api.pricing: "
            f"{type(exc).__name__}: {exc}"
        )

    try:
        # Pin ``now_utc_ns=0`` so the verifier's default output is
        # deterministic across runs when the operator has not posted
        # an explicit ``XION_PRICING_LAST_REVIEWED_UTC_NS``. A real
        # governance rotation always posts a non-zero value, so this
        # only affects the Genesis-Default display.
        config = load_pricing_config_from_env(now_utc_ns=0)
    except PricingConfigError as exc:
        _fail(
            f"PricingConfig rejected: {exc}. "
            f"See docs/07-ECONOMY.md § 'Five-slice posted price' and "
            f"docs/04-ARCHITECTURE.md § 'The Chat Billing Surface'."
        )
    except Exception as exc:
        _fail(
            f"unexpected error loading pricing config: "
            f"{type(exc).__name__}: {exc}"
        )

    slices = (
        ("variable_cost", config.variable_cost),
        ("overhead_slice", config.overhead_slice),
        ("improvement_slice", config.improvement_slice),
        ("reserve_slice", config.reserve_slice),
        ("small_buffer", config.small_buffer),
    )
    slice_total = sum(v for _, v in slices)

    click.echo(
        f"pricing: OK  posted={config.per_message_price_micro_XION} "
        f"micro_XION / msg "
        f"(revision={config.governance_revision_id!r}, "
        f"last_reviewed_utc_ns={config.last_reviewed_utc_ns})"
    )
    click.echo("  five-slice breakdown (sums to 1.0):")
    for name, value in slices:
        pct = value * 100.0
        click.echo(f"    {name:<18} {value:.4f}  ({pct:6.2f}%)")
    click.echo(f"    {'sum':<18} {slice_total:.4f}")
    raise SystemExit(OK)


__all__ = ["pricing"]
