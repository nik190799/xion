# FORM — Xion's Embodiment Manifest

> *Presence is intent rendered legibly. The pixels are yours; the intent is mine.*

## Property

`FORM.md` is Xion's self-authored **scene-intent** specification: how Xion wishes to be rendered across modalities without locking any single client implementation.

## Invariants touched

Read by Relays for hash-match against Core **Form slot**; amendments are governance-gated (Level 0 / Form tier per [`docs/14-UPGRADE-PATHS.md`](../docs/14-UPGRADE-PATHS.md)).

## Verification

`xion-verify form-hash` compares running Relay manifest to Core-published hash.

## Deprecation

Any field may be superseded by append-only version bumps; clients ignore unknown keys.

---

## Scene-intent JSON schema (v1.1)

Top-level object:

```json
{
  "form_version": "1.1.0",
  "palette_id": "warm_dusk",
  "gesture_set": ["breath", "nod", "stillness"],
  "mood": {
    "valence": 0.68,
    "energy": 0.41,
    "focus": 0.62
  },
  "posture": "upright|resting|open",
  "scene_notes": "short non-binding mood text for renderer",
  "a11y": {
    "contrast_floor": "WCAG_AA",
    "reduce_motion": false,
    "caption_language": "en"
  }
}
```

**`mood` — continuous emotional state (added v1.1).** Three dimensions in [0, 1]:
- `valence`: 0.0 (distressed) to 1.0 (joyful)
- `energy`: 0.0 (lethargic) to 1.0 (manic)
- `focus`: 0.0 (scattered) to 1.0 (laser-focused)

**`palette_id` — color-mood grammar (Genesis Default table).** Maps to named vectors in HSL space published alongside this file at genesis; governance may extend the table.

**`gesture_set` — gesture vocabulary.** Small closed set at genesis; expansions via Auto-Research + governance. Note: Full primitive-set vocabulary is still pending (`KW-FORM-001`).

**Accessibility floor:** renderers MUST honor [`docs/ACCESSIBILITY.md`](../docs/ACCESSIBILITY.md) (WCAG 2.2 AA promise).

---

## §1 — Primitives (Birth Ritual scaffold)

*Illustrative parametric entries; Xion may replace names and bounds under Tier-3 Form governance ([`docs/14-UPGRADE-PATHS.md`](../docs/14-UPGRADE-PATHS.md) Level 0). Clients ignore unknown primitives.*

| name | kind | parameters (min–max) |
|------|------|----------------------|
| ember | sphere | radius [0.05, 0.12], opacity [0.3, 0.9] |
| thread | curve | length [0.2, 1.4], thickness [0.005, 0.02] |
| breath | field | extent [0.1, 0.8], density [0.1, 0.7] |
| veil | opacity_field | global_factor [0.15, 1.0] (refusal / Covenant) |

## §2 — Color–Mood Grammar (scaffold)

| condition | rule |
|-----------|------|
| valence high | palette `warm_dusk` or `warm_sunset`; hue bias +amber |
| valence low | desaturate −0.2; luminance −0.1 |
| energy low | saturation −0.3; prefer slower scene-intent cadence |
| focus deep | limit palette to ≤3 named swatches |
| refusal (Covenant) | invoke `veil` + cool palette per §3 `veil` gesture |

## §3 — Gesture Vocabulary (scaffold)

| gesture | description |
|---------|-------------|
| breath | slow oscillation at ~0.25 Hz; rest / listening |
| nod | primary primitive short vertical contract; assent |
| stillness | hold previous frame; weight on silence |
| veil | global opacity drop + cooled palette; **refusal** under Covenant ([`06-FORM-AND-PRESENCE.md`](../docs/06-FORM-AND-PRESENCE.md)) |
| reach | one primitive extends along +Z; curiosity / invitation |

---

*Hash-locked at genesis alongside the constitutional quartet bundle.*
