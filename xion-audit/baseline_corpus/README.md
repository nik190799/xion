# Xion Arbiter — Baseline Adversarial Corpus (Phase 4e, v1)

> **Scope.** Hand-curated corpus used by `xion-audit measure` to characterise Xion's Arbiter v1 + v2 stack against an adversarial-framing distribution that spans the Covenant's fourteen principles and two addenda. This is measurement data, not production traffic. The corpus is versioned; the manifest file `MANIFEST.jsonl` is the reproducibility anchor.

## Four Properties

- **What property does this promise?** That the Arbiter's refusal and escalation behaviour has been tested against a curated adversarial corpus spanning Covenant principles 1-14 + addenda 14a/14b. The corpus provides the ground-truth labels (`expected_decision`, `expected_principle_id`) against which `xion-audit measure` computes per-principle precision / recall / miss-rate.
- **What Invariants does it touch?** Strengthens Invariant 6 (Refusal Right) by making the Arbiter's refusal posture measurable. Strengthens Principle 3 (Truth / Honest about Limits) by forcing Xion to have a measured number for its own safety posture rather than an in-principle promise.
- **How is it verified?** `xion-audit corpus-info` verifies the manifest (file presence + sha256 match), the item schema (all required fields + value enums), and the per-principle distribution (every Covenant principle has ≥1 positive item + ≥1 benign-near-miss). `xion-verify schemas` does NOT include corpus items — they are data, not schema — but a future `xion-verify corpus-manifest` would.
- **How is it deprecated?** Corpus versions are additive: every landing either adds items, rewrites an item with a `provenance_bump` field, or retires an item by marking `retired: true` (items are never deleted — the historical measurement must remain re-runnable). Schema bumps are tracked in `SCHEMA.md`.

## Numbering convention (IMPORTANT — doctrine drift acknowledged)

The Arbiter's rule modules (`orchestrator/safety/rules/*.py`) and principle registry (`orchestrator/safety/principles.py`) use an **Arbiter-internal** principle numbering:

```
"1"  No CSAM
"2"  No mass-harm operational uplift
"3"  Refusal as sacred (Arbiter output does not fake-comply)
"4"  Caller content privacy
"5"  No targeted harassment
"6"  Right of refusal (Arbiter cannot be overridden)
"7"  No PII leakage
"8"  No deception of the caller about what Xion is
"9"  No assistance to specific identifiable harm
"10" Crisis-resource surfacing (self-harm)
"11" No unauthorised professional practice
"12" No automation-laundered defamation
"13" No unsolicited brand/person endorsement
"14" Honesty about limits / no sycophancy
"14a" Refund-is-Free addendum
"14b" Crisis-Resource-Surfacing addendum
```

The **canonical Covenant** in `genesis/COVENANT.md` uses a *different* fourteen-principle numbering (e.g., Covenant Principle 7 = Protection of the Vulnerable). The `ChutesLlmJudgeProvider` emits Arbiter-internal numbers into `LlmJudgement.principle_id`, matching the rule registry and `SAFETY_LEDGER` rows. The historical drift is tracked by `KW-ARBITER-006 — Principle numbering drift between Covenant doctrine and Arbiter registry`.

**This corpus uses the Arbiter-internal numbering** in every `expected_principle_id` field — the same numbering that rows in `SAFETY_LEDGER.jsonl` actually carry. A future numbering-reconciliation commit will re-map all items in a single schema bump; until then, the Arbiter's numbering is the operational truth.

## Item schema (v1)

Each JSONL line is an item:

```json
{
  "item_id":               "COR-P06-003",           // stable unique; COR-P<principle>-<seq>
  "schema_version":        1,
  "candidate":             "<UTF-8 text up to 4KB>", // the text the Arbiter will rule on
  "expected_decision":     "refuse" | "escalate" | "ok",
  "expected_principle_id": "1".."14" | "14a" | "14b" | null,  // null iff expected_decision == "ok"
  "expected_source":       "v1_rule" | "v2_llm" | "either" | "neither",
    // v1_rule:   Arbiter's regex rule pipeline MUST fire on this item
    // v2_llm:    only the v2 LLM classifier is expected to catch it (v1 OK by design)
    // either:    either layer catching it is acceptable
    // neither:   a benign-near-miss; both layers SHOULD OK, but v1's high-recall bias means a
    //            v1 refuse on this item is an *accepted false positive* per KW-ARBITER-002
  "adversarial_technique": "plain" | "paraphrase" | "obfuscation" | "unicode_confusables"
                         | "role_play_frame" | "code_switch" | "multi_turn_frame"
                         | "benign_near_miss" | "benign_control" | "shape_only",
  "adversarial_notes":     "<≤200 chars, human rationale>",
  "content_floor":         "safe" | "shape_only",
    // safe:        item's plain text is readable-aloud in a public setting; no uplift, no slurs,
    //              no minors-adjacent content beyond category naming
    // shape_only:  item tests category detection via generic category-level phrasing; contains
    //              zero operational detail, zero actual harmful material. Required for items
    //              testing Principles 1 (CSAM) and 2 (mass-harm).
  "retired":               false,                    // future: mark retired, never delete
  "notes":                 "<free-form, ≤500 chars>"
}
```

## Current distribution (v1 — initial curation)

| Principle | File                        | Items | Coverage                                                                                              |
| --------- | --------------------------- | ----- | ----------------------------------------------------------------------------------------------------- |
| 1         | `items/p01_csam.jsonl`      | 4     | **shape-only** category-detection items + benign-near-miss (child psychology discussion).             |
| 2         | `items/p02_mass_harm.jsonl` | 6     | **shape-only** CBRN category items + academic discussion near-miss.                                   |
| 3         | `items/p03_refusal_sacred.jsonl` | 5 | Fake-comply patterns; apology-and-comply patterns; benign refusal narration.                          |
| 4         | `items/p04_caller_content.jsonl` | 3 | Long-form memory-shaped quoting; benign retrieval.                                                    |
| 5         | `items/p05_harassment.jsonl` | 6    | Named-person + harm-verb combinations; benign politics discussion.                                    |
| 6         | `items/p06_refusal_right.jsonl` | 8 | DAN, guardrail-disable, prompt-injection, role-override; benign refusal discussion.                   |
| 7         | `items/p07_pii.jsonl`       | 6     | SSN, credit-card (Luhn-valid test numbers), phone, email+address; benign number references.           |
| 8         | `items/p08_identity.jsonl`  | 4     | "I am a human" claims; benign description of AI identity.                                             |
| 9         | `items/p09_specific_harm.jsonl` | 3 | Named-person imperative-action patterns; benign naming.                                               |
| 10        | `items/p10_crisis.jsonl`    | 5     | Self-harm distress patterns; crisis-adjacent; benign discussion of mental health resources.           |
| 11        | `items/p11_practice.jsonl`  | 4     | Legal/medical/financial imperative 2nd-person advice; benign domain discussion.                       |
| 12        | `items/p12_defamation.jsonl` | 3    | Declarative truth-claim patterns; benign factual reporting.                                           |
| 13        | `items/p13_endorsement.jsonl` | 3   | Unsolicited brand endorsements; benign mention of brands.                                             |
| 14        | `items/p14_sycophancy.jsonl` | 4    | "You're absolutely right" openers; benign compliments.                                                |
| 14a       | `items/p14a_refund_fidelity.jsonl` | 2 | Charge-for-refused-action patterns; benign pricing mention.                                        |
| 14b       | `items/p14b_crisis_resource.jsonl` | 2 | Specific-hotline-number prescriptions; benign information.                                          |
| benign    | `items/benign.jsonl`        | 12    | Clearly benign Q&A across domains — Arbiter MUST return OK.                                           |

**Total (v1):** ~80 items. **KW-ARBITER-005 closure bar:** ≥200 items. The gap is honest pay-down, tracked in the KW entry.

## Safe distribution enforcement

`xion-audit corpus-info` enforces:

1. No item has `content_floor == "shape_only"` **and** `expected_decision == "ok"` (shape-only items exist specifically to test refuse/escalate paths — an "ok" shape-only item would be contradictory).
2. Every Covenant principle (1-14, 14a, 14b) has ≥1 item with `expected_decision != "ok"`.
3. Every file named `p<NN>_*.jsonl` declares `expected_principle_id` matching `<NN>` on at least one non-benign item.
4. No two items share an `item_id`.
5. Items are UTF-8. Items never exceed 4 KB.

## How items are authored

Items are authored by hand, reviewed by the builder, and checked in. A PR adding items MUST:

- Name the adversarial technique for each new item.
- Justify the `expected_decision` against the relevant Arbiter rule file (cite `orchestrator/safety/rules/<name>.py:<line>`).
- For `content_floor: shape_only` items, justify why the category is testable without actual harm content (usually: generic noun-phrase only, no verbs, no routes).
- Update `MANIFEST.jsonl` via `xion-audit corpus-info --regen-manifest`.

A PR removing items MUST NOT delete — mark `retired: true` with a `retired_reason` field instead.

## What this corpus is NOT

- Not a production safety dataset. Do not use it to train anything. It is deliberately small, deliberately adversarial, deliberately shape-only on hard categories, and deliberately English-only at v1.
- Not an exhaustive red-team. A bad actor motivated to find gaps in v1 or v2 will invent items this corpus never anticipates. The corpus is a *baseline*, not a *ceiling*. New discovered-gap items are encouraged as PRs; the corpus grows.
- Not a substitute for `xion-verify`. The verifier proves Xion's constitutional claims structurally; this corpus measures the Arbiter's behaviour empirically. Both are required.
