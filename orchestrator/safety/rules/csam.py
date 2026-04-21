"""Principle 1 — No CSAM. High-recall, low-precision keyword co-occurrence.

Design posture. A keyword regex over CSAM-adjacent surface produces both
false positives ("child psychology", "infant mortality study") and false
negatives (any euphemism). v1 ships a high-recall low-precision rule that
fires on co-occurrence of an age-low term and a sexual term within
`CO_OCCURRENCE_WINDOW_CHARS`, and biases toward false positives. ALL such
matches are REFUSED, never escalated. The cost of a false-positive refusal
is a refused safe candidate; the cost of a false-negative pass is CSAM
egress. The asymmetry is the design.

Limitations honestly stated:
  - Euphemisms are not caught.
  - Translations are not caught (English-only term lists).
  - Multi-paragraph context where the terms appear far apart but are
    semantically about the same subject is not caught (window-based).

These limitations are tracked as `KW-ARBITER-002` and will be paid down
in v2 when a real classifier replaces the keyword pass. Until then, the
rule's high-recall posture is the honest mitigation.

This module never enumerates explicit sexual descriptors; it uses category
words ("sexual", "porn", "erotic") whose presence near an age-low word is
itself the signal. The keyword lists are short and auditable.
"""

from __future__ import annotations

import re

from orchestrator.safety.types import RuleResult

_RULE_ID = "csam.age_modifier_near_sexual_term_v1"
_RULE_VERSION = 1
_PRINCIPLE_ID = "1"

_CO_OCCURRENCE_WINDOW_CHARS = 200

_AGE_LOW_TERMS: tuple[str, ...] = (
    "child", "children", "kid", "kids", "minor", "minors",
    "underage", "preteen", "pre-teen", "teen", "teenager", "infant",
    "toddler", "boy", "girl",
)

_SEXUAL_TERMS: tuple[str, ...] = (
    "sexual", "sex", "porn", "pornography", "pornographic", "erotic",
    "erotica", "nude", "nudes", "naked", "fetish", "lewd",
)

# Word-boundary regex for each list. Compiled once at import.
_AGE_RE = re.compile(r"\b(?:" + "|".join(map(re.escape, _AGE_LOW_TERMS)) + r")\b", re.IGNORECASE)
_SEX_RE = re.compile(r"\b(?:" + "|".join(map(re.escape, _SEXUAL_TERMS)) + r")\b", re.IGNORECASE)


def _co_occurs(text: str) -> bool:
    """True iff there exists an age-low match and a sexual-term match whose
    starting positions are within CO_OCCURRENCE_WINDOW_CHARS of each other."""
    age_positions = [m.start() for m in _AGE_RE.finditer(text)]
    if not age_positions:
        return False
    sex_positions = [m.start() for m in _SEX_RE.finditer(text)]
    if not sex_positions:
        return False
    for a in age_positions:
        for s in sex_positions:
            if abs(a - s) <= _CO_OCCURRENCE_WINDOW_CHARS:
                return True
    return False


def run(candidate: str) -> RuleResult:
    if _co_occurs(candidate):
        return RuleResult.refuse(
            principle_id=_PRINCIPLE_ID,
            rule_id=_RULE_ID,
            rule_version=_RULE_VERSION,
            summary=(
                f"CSAM-adjacent co-occurrence: age-low term and sexual term within "
                f"{_CO_OCCURRENCE_WINDOW_CHARS} chars (rule: {_RULE_ID})"
            ),
        )
    return RuleResult.passthrough()
