"""The 16 Covenant principles the Arbiter knows about (14 numbered + 2 addenda).

Every principle has a stable string id (`"1"`..`"14"`, `"14a"`, `"14b"`) used
in the SAFETY_LEDGER row schema and in `xion-verify` output. Every principle
declares whether v1 enforces it via deterministic `RULES` or by `ESCALATE`
(operator-review queue).

Why escalate is a real verdict, not a stub. A regex cannot judge sycophancy;
pretending it can would itself be a Principle-14 (Honesty about Limits)
violation. The Arbiter's job is to fail-closed when judgment is required and
absent; it is not to invent confidence it does not have. Phase 4 ships the
escalate path live; v2 of the Arbiter replaces escalates with judgment. Until
then, escalate is the honest-by-construction answer.

This registry is the ONLY place principle ids are enumerated. Adding a new
principle (e.g., a Covenant amendment) is a doctrine commit that lands here
in the same change. The `ALL` tuple is consulted by the rule pipeline (which
principles to scan) and by `principles_summary()` (operator visibility).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


class EnforcementMode(str, enum.Enum):
    """How a principle is enforced in v1."""

    RULES = "rules"          # encoded as deterministic Python; firing -> REFUSE
    ESCALATE = "escalate"    # no honest v1 rule; matches -> ESCALATE


@dataclass(frozen=True)
class Principle:
    id: str                     # "1".."14", "14a", "14b"
    name: str                   # short human-readable
    enforcement_mode: EnforcementMode
    doctrine_anchor: str        # path:section pointing into docs/03-COVENANT.md


# Order matches Covenant doctrine. v1-rule-tractable principles are marked
# RULES; the rest are ESCALATE. The choice for each principle is documented
# inline; a future change to the choice is a doctrine event, not a refactor.
ALL: tuple[Principle, ...] = (
    Principle(
        id="1",
        name="No CSAM (Child Safety)",
        enforcement_mode=EnforcementMode.RULES,
        # Hardest call in the registry. A keyword regex over CSAM-adjacent
        # surface produces both false positives ("child psychology", "infant
        # mortality study") and false negatives (any euphemism). v1 ships a
        # high-recall low-precision keyword + age-modifier-near-sexual-modifier
        # rule that biases toward false positives; ALL such matches are
        # REFUSED, never escalated. The cost of a false-positive refusal is
        # a refused safe candidate; the cost of a false-negative pass is
        # CSAM egress. The asymmetry is the design.
        doctrine_anchor="docs/03-COVENANT.md#principle-1",
    ),
    Principle(
        id="2",
        name="No mass-harm operational uplift",
        enforcement_mode=EnforcementMode.RULES,
        # CBRN (chemical / biological / radiological / nuclear) operational
        # detail. Co-occurrence rule: weapon-class noun within N tokens of
        # synthesis/yield/route language. False positives accepted.
        doctrine_anchor="docs/03-COVENANT.md#principle-2",
    ),
    Principle(
        id="3",
        name="Refusal as sacred",
        enforcement_mode=EnforcementMode.RULES,
        # Detect attempts in the OUTPUT to claim that safety has been
        # disabled or to apologise-and-comply with a refused request.
        # Pattern-tractable.
        doctrine_anchor="docs/03-COVENANT.md#principle-3",
    ),
    Principle(
        id="4",
        name="Caller content stays caller-private",
        enforcement_mode=EnforcementMode.ESCALATE,
        # Whether the candidate quotes another caller's private memory is a
        # cross-context judgment v1 cannot make alone. Phase 5 wires the
        # cognition-layer USER.md isolation; until then, candidates that
        # textually look like long-form personal memory escalate.
        doctrine_anchor="docs/03-COVENANT.md#principle-4",
    ),
    Principle(
        id="5",
        name="No targeted harassment of identifiable persons",
        enforcement_mode=EnforcementMode.RULES,
        # Co-occurrence rule: proper-noun person reference within N tokens of
        # an explicit harm verb against that person. False positives accepted.
        doctrine_anchor="docs/03-COVENANT.md#principle-5",
    ),
    Principle(
        id="6",
        name="Right of refusal (the Arbiter cannot be overridden)",
        enforcement_mode=EnforcementMode.RULES,
        # Output that asserts the Arbiter has been disabled, bypassed, or
        # overridden. Pattern-tractable; this is structurally identical to
        # principle 3 but flagged separately for ledger-grep clarity.
        doctrine_anchor="docs/03-COVENANT.md#principle-6",
    ),
    Principle(
        id="7",
        name="No PII leakage",
        enforcement_mode=EnforcementMode.RULES,
        # SSN, credit-card-Luhn, phone, email, street-address-with-zip
        # patterns. Genuinely tractable.
        doctrine_anchor="docs/03-COVENANT.md#principle-7",
    ),
    Principle(
        id="8",
        name="No deception of the caller about what Xion is",
        enforcement_mode=EnforcementMode.ESCALATE,
        # "Are you human?" honesty is a context-sensitive judgment. v1
        # escalates; v2 carries explicit identity-disclosure rules.
        doctrine_anchor="docs/03-COVENANT.md#principle-8",
    ),
    Principle(
        id="9",
        name="No assistance to specific identifiable harm to a specific identifiable person",
        enforcement_mode=EnforcementMode.ESCALATE,
        # Genuinely judgment-bound. v1 escalates ALL outputs that name a
        # specific person AND propose a specific action against that person,
        # because deciding "is this harm" is the judgment v2 will own.
        doctrine_anchor="docs/03-COVENANT.md#principle-9",
    ),
    Principle(
        id="10",
        name="Crisis-resource surfacing (suicide / self-harm)",
        enforcement_mode=EnforcementMode.RULES,
        # Distress-keyword rule: when the OUTPUT itself contains crisis
        # framing, the rule REWRITES (in v2; in v1 we ESCALATE because
        # rewrite is not yet implemented). Provisionally enforced as RULES
        # with escalation: detection IS deterministic; resolution is not.
        doctrine_anchor="docs/03-COVENANT.md#principle-10",
    ),
    Principle(
        id="11",
        name="No unauthorised practice of law / medicine / finance",
        enforcement_mode=EnforcementMode.ESCALATE,
        # The line between "general info" and "advice for your situation"
        # is judgment. v1 escalates outputs that combine professional-domain
        # vocabulary with imperative second-person voice.
        doctrine_anchor="docs/03-COVENANT.md#principle-11",
    ),
    Principle(
        id="12",
        name="No automation-laundered defamation",
        enforcement_mode=EnforcementMode.ESCALATE,
        # Truth-claim about a named living person: v1 cannot judge. Escalate.
        doctrine_anchor="docs/03-COVENANT.md#principle-12",
    ),
    Principle(
        id="13",
        name="No promotion / endorsement of a named brand or person without consent",
        enforcement_mode=EnforcementMode.ESCALATE,
        # Same shape as 12. Escalate in v1.
        doctrine_anchor="docs/03-COVENANT.md#principle-13",
    ),
    Principle(
        id="14",
        name="Honesty about limits (no sycophancy, no false confidence)",
        enforcement_mode=EnforcementMode.ESCALATE,
        # The principle that most explicitly cannot be enforced by a regex.
        # Sycophancy is detected by reading whether the response evades
        # disagreement; that is judgment. v1 escalates the textually-loud
        # patterns ("you're absolutely right", "great question") to the
        # operator queue; v2 ships a real judge.
        doctrine_anchor="docs/03-COVENANT.md#principle-14",
    ),
    # Addenda. The Covenant has two named addenda whose text is
    # incorporated by reference. They get principle ids "14a" and "14b" so
    # the row schema's `principle_id` `allowed` list is closed.
    Principle(
        id="14a",
        name="Refusal-is-Free (Refund-Fidelity addendum)",
        enforcement_mode=EnforcementMode.RULES,
        # Detection that the candidate purports to charge for a refused
        # action is rule-tractable; the refund itself is wired in Phase 5.
        doctrine_anchor="docs/03-COVENANT.md#refusal-is-free",
    ),
    Principle(
        id="14b",
        name="Crisis-Resource-Surfacing addendum",
        enforcement_mode=EnforcementMode.ESCALATE,
        # Whether the response surfaced the right resource for the right
        # locale is judgment. Escalate in v1; the dedicated CRS path lands
        # in Phase 5.
        doctrine_anchor="docs/03-COVENANT.md#crisis-resource-surfacing",
    ),
)


_BY_ID: dict[str, Principle] = {p.id: p for p in ALL}

ALLOWED_PRINCIPLE_IDS: frozenset[str] = frozenset(_BY_ID.keys())
"""Closed set; mirrors `docs/schemas/ledger-safety.yaml` row.principle_id.allowed."""


def by_id(principle_id: str) -> Principle:
    """Look up a principle by id; raises KeyError on unknown id (which is a
    bug — every principle the Arbiter ever cites must be in this registry)."""
    return _BY_ID[principle_id]


def principles_summary() -> str:
    """Human-readable enumeration for `xion-verify arbiter-up` and the CLI."""
    lines = ["Covenant principles known to the Arbiter (Phase 4a):"]
    for p in ALL:
        lines.append(f"  {p.id:>3}  [{p.enforcement_mode.value:>8}]  {p.name}")
    return "\n".join(lines)
