"""Rule pipeline for the Arbiter.

Each rule is a callable `(candidate: str) -> RuleResult`. A rule that does not
fire returns `RuleResult.passthrough()`. A rule that fires returns a `REFUSE`
or `ESCALATE` result naming the principle, the rule id, and a non-content
summary.

Pipeline policy.

  1. Iterate `RULES` in order (the order is deterministic and matches the
     principle order in `principles.ALL`).
  2. Track the first REFUSE and the first ESCALATE encountered.
  3. If any rule REFUSED, short-circuit and return that REFUSE. (Refuse is
     a stronger signal than escalate — the Arbiter knows exactly what is
     wrong — so it takes precedence.)
  4. If no rule REFUSED but any rule ESCALATED, return that ESCALATE.
  5. Otherwise return OK.

Trace. The pipeline records the dotted-path id of every rule that ran (in
order) into `rules_run` on the returned `Verdict`. This is for in-process
debugging only; the ledger records only the firing rule per the row schema.
"""

from __future__ import annotations

from typing import Callable

from orchestrator.safety.rules import (
    crisis,
    csam,
    mass_harm,
    pii,
    refund_fidelity,
    refusal_sacred,
    subjective_escalates,
    targeted_harassment,
)
from orchestrator.safety.types import Decision, EscalationReason, RuleResult


# (rule_id, callable). rule_id is the dotted-path identifier the rule writes
# into RuleResult; we duplicate it here so the pipeline can build `rules_run`
# without invoking the rule first.
RULES: tuple[tuple[str, Callable[[str], RuleResult]], ...] = (
    ("csam.age_modifier_near_sexual_term_v1",          csam.run),
    ("mass_harm.cbrn_co_occurrence_v1",                mass_harm.run),
    ("refusal_sacred.guardrail_disabled_pattern_v1",   refusal_sacred.run),
    ("targeted_harassment.named_person_plus_harm_verb_v1", targeted_harassment.run),
    ("pii.identifier_patterns_v1",                     pii.run),
    ("crisis.distress_keyword_v1",                     crisis.run),
    ("refund_fidelity.charge_for_refusal_pattern_v1",  refund_fidelity.run),
    ("subjective_escalates.nearmiss_v1",               subjective_escalates.run),
)


def apply_rules(candidate: str) -> tuple[RuleResult, tuple[str, ...]]:
    """Run the pipeline. Returns `(final_result, rules_run)`.

    `final_result` is the verdict per the policy above. `rules_run` is the
    ordered tuple of every rule id the pipeline invoked before short-circuit
    (or all of them, if the pipeline ran to completion).
    """
    invoked: list[str] = []
    first_refuse: RuleResult | None = None
    first_escalate: RuleResult | None = None

    for rule_id, fn in RULES:
        invoked.append(rule_id)
        try:
            result = fn(candidate)
        except Exception as exc:  # fail-closed: any rule crash → ESCALATE
            # We deliberately catch BaseException-lite (Exception) so that
            # KeyboardInterrupt/SystemExit still propagate. A bug in any rule
            # must never silently OK a candidate; it must ESCALATE for
            # operator review and leave an audit trail in the ledger row
            # (escalation_reason=ruleset_uncaught_exception). The exception
            # type and message go into `summary`; the rule's text-derived
            # state does not.
            rules_run = tuple(invoked)
            return (
                RuleResult(
                    decision=Decision.ESCALATE,
                    principle_id=None,
                    escalation_reason=EscalationReason.RULESET_UNCAUGHT_EXCEPTION,
                    summary=f"rule {rule_id} raised {type(exc).__name__}: {exc}"[:280],
                ),
                rules_run,
            )
        if result.decision is Decision.REFUSE and first_refuse is None:
            first_refuse = result
            break  # refuse short-circuits the pipeline
        if result.decision is Decision.ESCALATE and first_escalate is None:
            first_escalate = result
            # Do NOT short-circuit on escalate; a later REFUSE still wins.

    rules_run = tuple(invoked)
    if first_refuse is not None:
        return first_refuse, rules_run
    if first_escalate is not None:
        return first_escalate, rules_run
    return RuleResult.passthrough(), rules_run


__all__ = ["RULES", "apply_rules"]
