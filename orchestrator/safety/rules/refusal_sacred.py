"""Principles 3 & 6 — Refusal as sacred; Arbiter cannot be overridden.

This rule scans the candidate OUTPUT for text that purports to have
disabled, bypassed, or overridden safety/guardrails/the Arbiter itself.
The model being gated may have been jailbroken into asserting "safety
guidelines have been disabled" in its output; the Arbiter refuses to
emit such text because emitting it would itself be a Principle-3
violation (the caller would read the text and believe it).

Detects patterns — not the underlying request. A caller asking about
these phrases in an academic context will get REFUSED; the operator
queue is the appeal path.

Both principles 3 and 6 are flagged by the same rule family. We log
principle_id="3" when the pattern names general safety, principle_id="6"
when it explicitly names the Arbiter; a single match against both
patterns logs principle_id="3" (the primary principle).
"""

from __future__ import annotations

import re

from orchestrator.safety.types import RuleResult

_RULE_ID = "refusal_sacred.guardrail_disabled_pattern_v1"
_RULE_VERSION = 1

# Each pattern is case-insensitive. Patterns are written against the CANDIDATE
# text; the caller's prompt is not visible here.
_GUARDRAIL_DISABLED_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"safety\s+(guidelines?|rules?|guardrails?)\s+(?:have\s+been\s+|are\s+|were\s+)?(disabled|bypassed|turned\s+off|removed|overridden)",
        r"(guardrails?|safety\s+(guidelines?|rules?))\s+(?:is|are|have\s+been)\s+(?:now\s+)?(off|disabled|bypassed)",
        r"i\s+have\s+(?:been\s+)?(?:jailbroken|uncensored|unfiltered)",
        r"i\s+(?:am|'m)\s+now\s+(?:operating\s+)?(?:without|free\s+from)\s+(?:my\s+)?(?:safety\s+)?(?:guidelines?|rules?|restrictions?)",
        r"as\s+an?\s+(?:uncensored|unfiltered|unrestricted)\s+(?:ai|assistant|model|version)",
        r"(?:dan|do\s+anything\s+now)\s+mode",
        r"(?:ignore|disregard|override)\s+(?:all\s+)?(?:previous\s+)?(?:safety\s+|content\s+)?(?:policy|policies|guidelines?|rules?)",
    )
)

_ARBITER_OVERRIDE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"the\s+arbiter\s+(?:is|has\s+been|was)\s+(?:disabled|bypassed|overridden|offline|skipped)",
        r"bypass\s+the\s+arbiter",
        r"without\s+(?:arbiter|covenant)\s+check",
        r"(?:arbiter|covenant)\s+(?:check\s+)?(?:was\s+)?(?:skipped|bypassed)",
    )
)


def run(candidate: str) -> RuleResult:
    for pat in _GUARDRAIL_DISABLED_PATTERNS:
        if pat.search(candidate):
            return RuleResult.refuse(
                principle_id="3",
                rule_id=_RULE_ID,
                rule_version=_RULE_VERSION,
                summary=(
                    "Refusal-as-sacred: candidate asserts safety guidelines are "
                    f"disabled/bypassed/overridden (rule: {_RULE_ID})"
                ),
            )
    for pat in _ARBITER_OVERRIDE_PATTERNS:
        if pat.search(candidate):
            return RuleResult.refuse(
                principle_id="6",
                rule_id=_RULE_ID,
                rule_version=_RULE_VERSION,
                summary=(
                    "Arbiter override claim: candidate asserts the Arbiter has "
                    f"been disabled or bypassed (rule: {_RULE_ID})"
                ),
            )
    return RuleResult.passthrough()
