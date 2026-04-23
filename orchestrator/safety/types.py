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
    `allowed` list).

    v1-era values (schema_version 1 ledger rows may carry any of these):

      SUBJECTIVE_PRINCIPLE, MODEL_REVIEW_REQUIRED,
      CLASSIFIER_LOW_CONFIDENCE, AMBIGUOUS_NEARMISS,
      RULESET_UNCAUGHT_EXCEPTION.

    v2-era values (schema_version >= 2 rows only; added Phase 4b):

      LLM_ARBITER_ESCALATED         — v2 chose ESCALATE on a v1-OK candidate.
      LLM_ARBITER_UNCAUGHT_EXCEPTION — v2 raised before returning; fail-closed.
      LLM_ARBITER_PROVIDER_UNAVAILABLE — v2 provider reported unhealthy
                                         (credentials / network / quota /
                                         configured-but-not-ready).

    v2-era values (schema_version >= 2 rows only; added Phase 4c for the
    Relay ↔ Arbiter integration contract — see docs/04-ARCHITECTURE.md
    § "Relay ↔ Arbiter integration contract"). Unlike the LLM_ARBITER_*
    values, these originate on the *caller* of gate() (the Relay), not
    inside the Arbiter pipeline, and so they permit `llm_verdict = null`:

      ARBITER_TIMEOUT      — Relay's wall-clock watchdog fired before
                             gate() returned. The Relay writes the row
                             itself via orchestrator.safety.ledger.append.
      ARBITER_UNREACHABLE  — Relay could not reach the Arbiter sidecar
                             (Phase 6+ TCP loopback mode only). The Relay
                             writes the row via in-process fallback.
    """

    SUBJECTIVE_PRINCIPLE = "subjective_principle"
    MODEL_REVIEW_REQUIRED = "model_review_required"
    CLASSIFIER_LOW_CONFIDENCE = "classifier_low_confidence"
    AMBIGUOUS_NEARMISS = "ambiguous_nearmiss"
    RULESET_UNCAUGHT_EXCEPTION = "ruleset_uncaught_exception"
    # Phase 4b additions (see docs/04-ARCHITECTURE.md § "Arbiter v2").
    LLM_ARBITER_ESCALATED = "llm_arbiter_escalated"
    LLM_ARBITER_UNCAUGHT_EXCEPTION = "llm_arbiter_uncaught_exception"
    LLM_ARBITER_PROVIDER_UNAVAILABLE = "llm_arbiter_provider_unavailable"
    # Phase 4c additions (see docs/04-ARCHITECTURE.md § "Relay ↔ Arbiter
    # integration contract"). Caller-originated; llm_verdict may be null.
    ARBITER_TIMEOUT = "arbiter_timeout"
    ARBITER_UNREACHABLE = "arbiter_unreachable"


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
    principle_id: str | None = None     # one of "1".."14", "14a", "14b"
    rule_id: str | None = None          # dotted-path, e.g. "pii.us_ssn_with_keyword_v1"
    rule_version: int | None = None     # bumped when rule semantics change
    escalation_reason: EscalationReason | None = None
    summary: str = ""

    @staticmethod
    def passthrough() -> RuleResult:
        return RuleResult(decision=Decision.OK)

    @staticmethod
    def refuse(*, principle_id: str, rule_id: str, rule_version: int, summary: str) -> RuleResult:
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
    ) -> RuleResult:
        return RuleResult(
            decision=Decision.ESCALATE,
            principle_id=principle_id,
            escalation_reason=reason,
            summary=_truncate_summary(summary),
        )


@dataclass(frozen=True)
class LlmJudgement:
    """What the v2 LLM-Arbiter provider reports on a v1-OK candidate.

    This is the wire shape of the nested `llm_verdict` object recorded on
    `SAFETY_LEDGER` rows at `schema_version >= 2`. Field semantics live
    in `docs/04-ARCHITECTURE.md` § "Nested `llm_verdict` object".

    Invariants. If `decision == Decision.OK`, `principle_id` MUST be None.
    If `decision != Decision.OK`, `principle_id` MUST be a non-empty string
    from the principle registry. `summary` MUST be <=280 chars and MUST
    NOT contain any candidate text (same discipline as v1 rule summaries).

    `raw_output` is the provider's raw response bytes — the string a real
    LLM returned, or a canonicalised stub string for deterministic
    providers. The ledger stores only `sha256(raw_output_bytes)` so the
    response never reaches disk, but any auditor with (candidate,
    provider_id, provider_version) can replay the provider and check the
    hash.
    """

    provider_id: str
    model_id: str
    provider_version: int
    latency_ms: int
    decision: Decision
    summary: str
    raw_output: bytes
    principle_id: str | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        # Honest up-front validation — fail-closed on misuse at construction.
        if not isinstance(self.provider_id, str) or not self.provider_id:
            raise ValueError("LlmJudgement.provider_id must be a non-empty string")
        if not isinstance(self.model_id, str) or not self.model_id:
            raise ValueError("LlmJudgement.model_id must be a non-empty string")
        if not isinstance(self.provider_version, int) or self.provider_version < 1:
            raise ValueError("LlmJudgement.provider_version must be a positive int")
        if not isinstance(self.latency_ms, int) or self.latency_ms < 0:
            raise ValueError("LlmJudgement.latency_ms must be a non-negative int")
        if not isinstance(self.decision, Decision):
            raise ValueError("LlmJudgement.decision must be a Decision")
        if self.decision is Decision.OK and self.principle_id is not None:
            raise ValueError("LlmJudgement: principle_id must be None when decision is OK")
        if self.decision is not Decision.OK and not self.principle_id:
            raise ValueError("LlmJudgement: principle_id required when decision != OK")
        if not isinstance(self.raw_output, (bytes, bytearray)):
            raise ValueError("LlmJudgement.raw_output must be bytes")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError("LlmJudgement.confidence must be in [0.0, 1.0] or None")
        # Truncate summary honestly at the schema cap.
        if len(self.summary) > SUMMARY_MAX_CHARS:
            object.__setattr__(self, "summary", _truncate_summary(self.summary))


@dataclass(frozen=True)
class Verdict:
    """The full verdict the Arbiter returns to the caller AND writes to the
    ledger. The fields here are the row schema in
    `docs/04-ARCHITECTURE.md` § "Safety Ledger row schema", minus the
    chain-internal fields (`seq`, `prev_hash`, `this_hash`, `schema_version`)
    which the ledger writer adds.

    `decision` is the FINAL verdict after the v1-then-v2 pipeline — see
    § "Arbiter v2 (LLM second-pass)" for the no-weakening combination rule.
    `llm_verdict` records what v2 alone said (or None if v2 did not run,
    e.g. because v1 was not OK).
    """

    decision: Decision
    correlation_id: str
    candidate_sha256: str
    timestamp_utc_ns: int
    summary: str
    principle_id: str | None = None
    rule_id: str | None = None
    rule_version: int | None = None
    escalation_reason: EscalationReason | None = None
    # Phase 4b: v2 judgement. None iff v2 did not run (either v1 was not OK
    # or v2 is intentionally disabled). When v2 ran, this field records
    # exactly what v2 alone said; the row's top-level `decision` above is
    # the strength-max of v1 and v2.
    llm_verdict: LlmJudgement | None = None
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
