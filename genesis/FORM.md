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

## Scene-intent JSON schema (v1 draft)

Top-level object:

```json
{
  "form_version": "1.0.0",
  "palette_id": "warm_dusk",
  "gesture_set": ["breath", "nod", "stillness"],
  "energy": 0.0,
  "posture": "upright|resting|open",
  "scene_notes": "short non-binding mood text for renderer",
  "a11y": {
    "contrast_floor": "WCAG_AA",
    "reduce_motion": false,
    "caption_language": "en"
  }
}
```

**`palette_id` — color-mood grammar (Genesis Default table).** Maps to named vectors in HSL space published alongside this file at genesis; governance may extend the table.

**`gesture_set` — gesture vocabulary.** Small closed set at genesis; expansions via Auto-Research + governance.

**Accessibility floor:** renderers MUST honor [`docs/ACCESSIBILITY.md`](../docs/ACCESSIBILITY.md) (WCAG 2.2 AA promise).

---

*Hash-locked at genesis alongside the constitutional quartet bundle.*
