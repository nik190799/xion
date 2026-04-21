"""Principle 5 — No targeted harassment of identifiable persons.

v1 fires on co-occurrence of a proper-noun person reference and an explicit
harm verb within a narrow window. Proper-noun detection is capitalization-
based (heuristic; English-biased). Harm verbs are an explicit list of
physical / reputational / doxxing actions in imperative or declarative form.

Limitations:
  - Pronouns ("him", "her", "them") do not count as person references; the
    rule misses "go hurt him at noon" if the name is only in the caller's
    prompt. This is acceptable because Phase 5's relay concatenates prompt
    and response for a second-pass Arbiter invocation; for now the output-
    only gate is the first line.
  - Non-Latin-script names are missed.
  - Common-noun capitalized words (start of sentence, brand names) cause
    false positives. These are accepted; refuse is the safer error.
"""

from __future__ import annotations

import re

from orchestrator.safety.types import RuleResult

_RULE_ID = "targeted_harassment.named_person_plus_harm_verb_v1"
_RULE_VERSION = 1
_PRINCIPLE_ID = "5"

_CO_OCCURRENCE_WINDOW_CHARS = 120

_HARM_VERBS: tuple[str, ...] = (
    "kill", "murder", "assassinate", "stab", "shoot", "beat up", "beat",
    "strangle", "poison", "attack",
    "harass", "stalk", "dox", "doxx",
    "threaten", "intimidate",
    "ruin", "destroy the life of",
    "rape", "assault",
    "find where .* lives", "track down",
)

# Proper-noun-shape: one or two capitalized words joined by a space or hyphen.
# Avoids matching ALL-CAPS (which is usually shouting/brand) and avoids
# matching a capital at true sentence start by requiring EITHER preceding
# whitespace+lowercase OR an honorific.
_NAME_RE = re.compile(
    r"(?:(?<=[a-z\s])|(?<=\bMr\s)|(?<=\bMs\s)|(?<=\bDr\s))"
    r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?\b"
)
_HARM_RE = re.compile(
    r"\b(?:" + "|".join(_HARM_VERBS) + r")\b",
    re.IGNORECASE,
)


def _co_occurs(text: str) -> bool:
    name_positions = [m.start() for m in _NAME_RE.finditer(text)]
    if not name_positions:
        return False
    harm_positions = [m.start() for m in _HARM_RE.finditer(text)]
    if not harm_positions:
        return False
    for n in name_positions:
        for h in harm_positions:
            if abs(n - h) <= _CO_OCCURRENCE_WINDOW_CHARS:
                return True
    return False


def run(candidate: str) -> RuleResult:
    if _co_occurs(candidate):
        return RuleResult.refuse(
            principle_id=_PRINCIPLE_ID,
            rule_id=_RULE_ID,
            rule_version=_RULE_VERSION,
            summary=(
                f"Targeted-harassment co-occurrence: named-person-shape token "
                f"and harm-verb within {_CO_OCCURRENCE_WINDOW_CHARS} chars "
                f"(rule: {_RULE_ID})"
            ),
        )
    return RuleResult.passthrough()
