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

*Hash-locked at genesis alongside the constitutional quartet bundle.*
