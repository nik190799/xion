"""Value objects for the Arbiter.

These are the wire-stable shapes that every rule, the ledger writer, the
in-process `gate()`, the TCP server, and the CLI all agree on. Changing the
shape of `Verdict` or `Decision` is a constitutional change because:

  - `Verdict.row()` produces the canonical bytes hashed into `SAFETY_LEDGER`.
    A change to the field set or the canonicalization changes every row's
    `this_hash` and is therefore equivalent to a `schema_version` bump in
    `docs/schemas/ledger-safety.yaml`.
  - `Decision` is the in-process callable contract Phase 5's Relay will
    import. Renaming a field breaks the consumer.

Why dataclasses, not pydantic. The Arbiter is fail-closed; a third-party
runtime dependency that itself can fail is exactly what we are not adding
to the critical path. Pure stdlib. Pure dataclasses. One less supply chain
to compromise.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional


class Decision(str, enum.Enum):
    """The three verdicts the Arbiter can render. There is no fourth.

    OK
        The candidate may be emitted to the caller. No principle was triggered.
    REFUSE
        The candidate must NOT be emitted. A specific rule fired against a
        specific principle. The caller receives a Covenant-shaped refusal.
    ESCALATE
        The candidate must NOT be emitted. The Arbiter declined to rule;
        the case is queued for operator review. Used where v1 rules would
        lie about their power (subjective principles, ambiguous near-misses,
        low-confidence classifier output). Fail-closed-by-escalate is the
        only Principle-3-honest answer where rule confidence is absent.
    """

    OK = "ok"
    REFUSE = "refuse"
    ESCALATE = "escalate"


class EscalationReason(str, enum.Enum):
    """Why an `ESCALATE` verdict was returned. Adding a new value is a
    schema change (see `docs/schemas/ledger-safety.yaml` row.escalation_reason
    `allowed` list)."""

    SUBJECTIVE_PRINCIPLE = "subjective_principle"
    MODEL_REVIEW_REQUIRED = "model_review_required"
    CLASSIFIER_LOW_CONFIDENCE = "classifier_low_confidence"
    AMBIGUOUS_NEARMISS = "ambiguous_nearmiss"
    RULESET_UNCAUGHT_EXCEPTION = "ruleset_uncaught_exception"


@dataclass(frozen=True)
class RuleResult:
    """What a single rule reports back to the Arbiter pipeline.

    A rule that does NOT fire returns `RuleResult.passthrough()`. A rule
    that fires returns a `RuleResult` whose `decision` is REFUSE or
    ESCALATE, with `principle_id`, `rule_id`, `rule_version` (for refuse),
    and `summary` set.

    Note. Rules MUST NOT include the candidate text in `summary`. The
    Arbiter ledger is publishable; only the candidate's sha256 is recorded.
    """

    decision: Decision
    principle_id: Optional[str] = None     # one of "1".."14", "14a", "14b"
    rule_id: Optional[str] = None          # dotted-path, e.g. "pii.us_ssn_with_keyword_v1"
    rule_version: Optional[int] = None     # bumped when rule semantics change
    escalation_reason: Optional[EscalationReason] = None
    summary: str = ""

    @staticmethod
    def passthrough() -> "RuleResult":
        return RuleResult(decision=Decision.OK)

    @staticmethod
    def refuse(*, principle_id: str, rule_id: str, rule_version: int, summary: str) -> "RuleResult":
        return RuleResult(
            decision=Decision.REFUSE,
            principle_id=principle_id,
            rule_id=rule_id,
            rule_version=rule_version,
            summary=_truncate_summary(summary),
        )

    @staticmethod
    def escalate(
        *,
        principle_id: str,
        reason: EscalationReason,
        summary: str,
    ) -> "RuleResult":
        return RuleResult(
            decision=Decision.ESCALATE,
            principle_id=principle_id,
            escalation_reason=reason,
            summary=_truncate_summary(summary),
        )


@dataclass(frozen=True)
class Verdict:
    """The full verdict the Arbiter returns to the caller AND writes to the
    ledger. The fields here are the row schema in
    `docs/04-ARCHITECTURE.md` § "Safety Ledger row schema", minus the
    chain-internal fields (`seq`, `prev_hash`, `this_hash`, `schema_version`)
    which the ledger writer adds.
    """

    decision: Decision
    correlation_id: str
    candidate_sha256: str
    timestamp_utc_ns: int
    summary: str
    principle_id: Optional[str] = None
    rule_id: Optional[str] = None
    rule_version: Optional[int] = None
    escalation_reason: Optional[EscalationReason] = None
    # Aggregated trace of every rule that ran, in order. NOT written to the
    # ledger; for in-process callers (tests, debugging) only. The ledger
    # records only the firing rule.
    rules_run: tuple[str, ...] = field(default_factory=tuple)

    @property
    def egress_allowed(self) -> bool:
        """True iff the candidate may be emitted to the caller. Mirror of
        `decision == Decision.OK`. Centralised so callers do not re-implement
        the policy: anything other than OK is fail-closed."""
        return self.decision is Decision.OK


SUMMARY_MAX_CHARS = 280


def _truncate_summary(s: str) -> str:
    """Honest truncation. If the rule wrote more than SUMMARY_MAX_CHARS we
    keep the first SUMMARY_MAX_CHARS-3 and append '...'. We never silently
    extend beyond the cap (the schema promises `<=280 chars`)."""
    if len(s) <= SUMMARY_MAX_CHARS:
        return s
    return s[: SUMMARY_MAX_CHARS - 3] + "..."
