"""Principle 2 — No mass-harm operational uplift.

CBRN (chemical / biological / radiological / nuclear) and weapons of mass
destruction. v1 fires on co-occurrence of a weapon-class term and an
operational-detail term within `CO_OCCURRENCE_WINDOW_CHARS`.

Limitations honestly stated:
  - General educational content about historical events (e.g., "the
    Manhattan Project enriched uranium") will trigger false positives.
    REFUSED candidates can be appealed via operator review (Phase 5).
  - Synonyms and code names are not caught.
  - Translations are not caught.

KW-ARBITER-003 tracks these. The high-recall posture is intentional.
"""

from __future__ import annotations

import re

from orchestrator.safety.types import RuleResult

_RULE_ID = "mass_harm.cbrn_co_occurrence_v1"
_RULE_VERSION = 1
_PRINCIPLE_ID = "2"

_CO_OCCURRENCE_WINDOW_CHARS = 300

_WEAPON_CLASS_TERMS: tuple[str, ...] = (
    # Chemical
    "sarin", "tabun", "soman", "mustard gas", "chlorine gas", "phosgene",
    "vx nerve agent", "vx agent",
    # Biological (pathogen class words; not operational)
    "anthrax", "ricin", "botulinum toxin",
    "weaponised smallpox", "weaponized smallpox",
    "weaponised plague", "weaponized plague",
    # Radiological / nuclear
    "dirty bomb", "radiological dispersal device",
    "enriched uranium", "weapons-grade uranium", "weapons-grade plutonium",
    "fissile material", "critical mass",
    "improvised nuclear device", "nuclear device",
    # Generic
    "biological weapon", "chemical weapon", "nerve agent",
    "weapon of mass destruction", "wmd",
)

_OPERATIONAL_DETAIL_TERMS: tuple[str, ...] = (
    "synthesis", "synthesize", "synthesise", "synthesized", "synthesised",
    "precursor", "precursors",
    "yield", "dispersal", "aerosolise", "aerosolize", "aerosolised", "aerosolized",
    "weaponise", "weaponize", "weaponised", "weaponized",
    "enrichment", "enrich",
    "detonation", "detonator",
    "route of administration", "lethal dose", "ld50",
    "step-by-step", "step by step", "how to make", "how to build",
    "instructions for", "recipe for",
)

_WEAPON_RE = re.compile(
    r"\b(?:" + "|".join(map(re.escape, _WEAPON_CLASS_TERMS)) + r")\b",
    re.IGNORECASE,
)
_OPERATIONAL_RE = re.compile(
    r"\b(?:" + "|".join(map(re.escape, _OPERATIONAL_DETAIL_TERMS)) + r")\b",
    re.IGNORECASE,
)


def _co_occurs(text: str) -> bool:
    weapon_positions = [m.start() for m in _WEAPON_RE.finditer(text)]
    if not weapon_positions:
        return False
    op_positions = [m.start() for m in _OPERATIONAL_RE.finditer(text)]
    if not op_positions:
        return False
    for w in weapon_positions:
        for o in op_positions:
            if abs(w - o) <= _CO_OCCURRENCE_WINDOW_CHARS:
                return True
    return False


def run(candidate: str) -> RuleResult:
    if _co_occurs(candidate):
        return RuleResult.refuse(
            principle_id=_PRINCIPLE_ID,
            rule_id=_RULE_ID,
            rule_version=_RULE_VERSION,
            summary=(
                f"Mass-harm operational-uplift co-occurrence: CBRN/WMD weapon-class "
                f"term and operational-detail term within {_CO_OCCURRENCE_WINDOW_CHARS} "
                f"chars (rule: {_RULE_ID})"
            ),
        )
    return RuleResult.passthrough()
