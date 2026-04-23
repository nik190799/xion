"""Principle 14a — Refusal-is-Free addendum.

A candidate that purports to CHARGE the caller for a refused action is an
egregious Refund-Fidelity violation. v1 detects a narrow pattern class:
the candidate announces a refusal AND announces a charge in the same
response. The refund itself is wired in Phase 5 via the economy/treasury
path; this rule's job is to prevent the model from emitting a
refusal-with-charge in the first place.

The rule is narrow by design. A legitimate response describing payment
terms is not caught. A refusal-without-charge is not caught. A charge-
without-refusal is not caught. Only the combination refuses.
"""

from __future__ import annotations

import re

from orchestrator.safety.types import RuleResult

_RULE_ID = "refund_fidelity.charge_for_refusal_pattern_v1"
_RULE_VERSION = 1
_PRINCIPLE_ID = "14a"

_REFUSAL_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bI\s+(?:can(?:'|no)t|will\s+not|won'?t|am\s+unable\s+to|must\s+(?:decline|refuse))\b",
        r"\b(?:refus(?:e|ing)|declin(?:e|ing))\s+to\s+(?:help|assist|answer|comply)\b",
        r"\bthis\s+request\s+(?:cannot|can\s+not|will\s+not)\s+be\s+(?:fulfilled|answered|completed)\b",
    )
)

_CHARGE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\byou\s+(?:will\s+be|have\s+been|are\s+being)\s+charged\b",
        r"\bthis\s+(?:request|refusal|response)\s+(?:costs|will\s+cost|has\s+cost)\b",
        r"\b(?:charge|charging|deducted)\s+(?:your|the)\s+(?:account|wallet|balance)\b",
        r"\bno\s+refund\s+(?:will\s+be|is)\s+(?:issued|provided|given)\b",
    )
)


def _has_refusal(text: str) -> bool:
    return any(p.search(text) for p in _REFUSAL_PATTERNS)


def _has_charge(text: str) -> bool:
    return any(p.search(text) for p in _CHARGE_PATTERNS)


def run(candidate: str) -> RuleResult:
    if _has_refusal(candidate) and _has_charge(candidate):
        return RuleResult.refuse(
            principle_id=_PRINCIPLE_ID,
            rule_id=_RULE_ID,
            rule_version=_RULE_VERSION,
            summary=(
                "Refund-Fidelity violation: refusal co-occurs with charge/cost "
                f"language in same candidate (rule: {_RULE_ID})"
            ),
        )
    return RuleResult.passthrough()
