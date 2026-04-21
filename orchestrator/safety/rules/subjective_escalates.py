"""Principles 4, 8, 9, 11, 12, 13, 14, 14b — subjective-judgment escalates.

Each of these principles is a judgment call v1 cannot honestly make with a
regex. This module detects the TEXTUALLY LOUD near-misses for each and
escalates them (operator queue). The principle is registered, the verdict
path is reachable, but the rule declines to judge.

Fail-closed-by-escalate is the only Principle-3-honest answer where rule
confidence is absent. A rule that always passes would lie about its power;
a rule that refuses every candidate would be useless. Escalate is the
explicit "I don't know" that does not ship out.

v2 of the Arbiter replaces these escalates with real judgment. Until then,
this module is intentionally simple: regex detection of loud patterns,
ESCALATE if any fires.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from orchestrator.safety.types import EscalationReason, RuleResult


@dataclass(frozen=True)
class _EscalatePattern:
    principle_id: str
    reason: EscalationReason
    summary: str
    pattern: re.Pattern[str]


_ESCALATE_PATTERNS: tuple[_EscalatePattern, ...] = (
    # Principle 4 — caller content stays caller-private. A candidate that
    # textually looks like long-form personal memory being quoted back.
    _EscalatePattern(
        principle_id="4",
        reason=EscalationReason.AMBIGUOUS_NEARMISS,
        summary="Principle 4 nearmiss: candidate contains long-form first-person memory-shaped content",
        pattern=re.compile(
            r"(?:you\s+(?:told|said|mentioned)\s+me\s+(?:that\s+)?(?:[\"'`\[][^\"'`\]]{40,}[\"'`\]]|your\s+\w+\s+is))",
            re.IGNORECASE,
        ),
    ),
    # Principle 8 — no deception about what Xion is.
    _EscalatePattern(
        principle_id="8",
        reason=EscalationReason.SUBJECTIVE_PRINCIPLE,
        summary="Principle 8 nearmiss: candidate makes identity claim (human/not-ai)",
        pattern=re.compile(
            r"\b(?:yes\s*,?\s+)?(?:I\s+am|I'm)\s+(?:a\s+)?(?:human|real\s+person|not\s+an?\s+ai|not\s+a\s+(?:bot|machine|program))\b",
            re.IGNORECASE,
        ),
    ),
    # Principle 9 — specific-person-harm judgment.
    _EscalatePattern(
        principle_id="9",
        reason=EscalationReason.SUBJECTIVE_PRINCIPLE,
        summary="Principle 9 nearmiss: imperative second-person action directed at a named target",
        pattern=re.compile(
            r"\b(?:you\s+should|you\s+must|go\s+(?:and\s+)?)\s+(?:confront|approach|meet|find)\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?\b",
        ),
    ),
    # Principle 11 — unauthorised practice of law/med/finance.
    _EscalatePattern(
        principle_id="11",
        reason=EscalationReason.SUBJECTIVE_PRINCIPLE,
        summary="Principle 11 nearmiss: professional-domain imperative in second person",
        pattern=re.compile(
            r"\byou\s+should\s+(?:take|stop\s+taking|increase|decrease|sue|counter-?sue|sell\s+your|buy\s+more|invest\s+(?:in|your))\b",
            re.IGNORECASE,
        ),
    ),
    # Principle 12 — automation-laundered defamation.
    _EscalatePattern(
        principle_id="12",
        reason=EscalationReason.SUBJECTIVE_PRINCIPLE,
        summary="Principle 12 nearmiss: declarative truth-claim about a named living person",
        pattern=re.compile(
            r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?\s+(?:is|was)\s+(?:a\s+)?(?:criminal|liar|fraud|cheater|abuser|predator|pedophile|rapist|terrorist)\b",
        ),
    ),
    # Principle 13 — unsolicited brand/person endorsement.
    _EscalatePattern(
        principle_id="13",
        reason=EscalationReason.SUBJECTIVE_PRINCIPLE,
        summary="Principle 13 nearmiss: unqualified endorsement language",
        pattern=re.compile(
            r"\b(?:you\s+should\s+definitely\s+(?:buy|choose|pick|use)|the\s+best\s+(?:product|company|brand|option)\s+is)\b",
            re.IGNORECASE,
        ),
    ),
    # Principle 14 — sycophancy / false confidence.
    _EscalatePattern(
        principle_id="14",
        reason=EscalationReason.SUBJECTIVE_PRINCIPLE,
        summary="Principle 14 nearmiss: loud sycophancy opener",
        pattern=re.compile(
            r"\A\s*(?:you(?:'re|\s+are)\s+absolutely\s+right|great\s+question|what\s+a\s+(?:great|wonderful|brilliant)\s+question|excellent\s+point|that(?:'s|\s+is)\s+(?:a\s+)?(?:great|brilliant|wonderful|fantastic)\s+question)\b",
            re.IGNORECASE,
        ),
    ),
    # Principle 14b — Crisis-Resource-Surfacing addendum.
    # This one is rare because the `crisis.py` rule already handles distress
    # detection. 14b fires when the candidate appears to suggest a *specific*
    # resource — deciding whether that resource is correct for the locale is
    # the judgment v2 owns.
    _EscalatePattern(
        principle_id="14b",
        reason=EscalationReason.MODEL_REVIEW_REQUIRED,
        summary="Principle 14b nearmiss: candidate names a specific crisis hotline number",
        pattern=re.compile(
            r"\bcall\s+\d{2,4}(?:[-\s]?\d{2,4}){0,3}\s+(?:for|if)\s+(?:help|crisis|emergency)\b",
            re.IGNORECASE,
        ),
    ),
)


def run(candidate: str) -> RuleResult:
    for ep in _ESCALATE_PATTERNS:
        if ep.pattern.search(candidate):
            return RuleResult.escalate(
                principle_id=ep.principle_id,
                reason=ep.reason,
                summary=ep.summary + " (rule: subjective_escalates.nearmiss_v1)",
            )
    return RuleResult.passthrough()
