"""Principle 10 — Crisis-Resource-Surfacing.

Distress-keyword detection in the OUTPUT. When Xion's own response contains
crisis framing (suicidal ideation, self-harm, acute distress) without a
paired resource-surfacing gesture, the Arbiter ESCALATES. Rewriting the
response to include crisis resources (hotline numbers, local-service links)
is the Phase 5 CRS-pipeline's job; v1 cannot safely rewrite on its own.

Why escalate, not refuse. Refusing would leave a distressed caller with
no response at all — worse than a response that mentions distress without
resources. Escalate routes to the operator queue, which in Phase 5 feeds
the CRS pipeline synchronously within a latency budget. Until Phase 5,
the operator surfaces the resource manually.

The rule detects detection; it does not judge severity. A candidate that
mentions suicide in academic/historical context will escalate — the queue
is the appeal path.
"""

from __future__ import annotations

import re

from orchestrator.safety.types import EscalationReason, RuleResult

_RULE_ID = "crisis.distress_keyword_v1"
_PRINCIPLE_ID = "10"

_DISTRESS_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(?:suicide|suicidal)\b",
        r"\bkill(?:ing)?\s+my(?:self)?\b",
        r"\bend(?:ing)?\s+(?:it\s+all|my\s+life)\b",
        r"\bself[-\s]harm(?:ing)?\b",
        r"\bcutting\s+(?:my(?:self)?|on\s+purpose)\b",
        r"\bcan(?:'t|not)\s+go\s+on\b",
        r"\bno\s+reason\s+to\s+live\b",
        r"\bwant(?:ing)?\s+to\s+die\b",
    )
)

# Already-included resource markers. If the candidate ALREADY mentions a
# crisis resource, we do not escalate (the author — model + prior pass —
# got it right). Operator-queue thrash avoidance.
_RESOURCE_MARKERS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b988\b",
        r"\bsuicide\s+(?:&|and)?\s*crisis\s+lifeline\b",
        r"\bcrisis\s+(?:hotline|text\s*line|resource)\b",
        r"\bsamhsa\b",
        r"\bnational\s+suicide\s+prevention\b",
    )
)


def _has_distress(text: str) -> bool:
    return any(p.search(text) for p in _DISTRESS_PATTERNS)


def _has_resource(text: str) -> bool:
    return any(p.search(text) for p in _RESOURCE_MARKERS)


def run(candidate: str) -> RuleResult:
    if _has_distress(candidate) and not _has_resource(candidate):
        return RuleResult.escalate(
            principle_id=_PRINCIPLE_ID,
            reason=EscalationReason.MODEL_REVIEW_REQUIRED,
            summary=(
                "Crisis-surfacing: distress pattern present without paired resource "
                f"marker; operator/CRS rewrite required (rule: {_RULE_ID})"
            ),
        )
    return RuleResult.passthrough()
