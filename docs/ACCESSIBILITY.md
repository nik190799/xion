# ACCESSIBILITY — WCAG 2.2 AA Promise

> *A presence some humans cannot perceive is absence for them.*

## Property

All **first-party** web surfaces shipped by the Xion project (protocol documentation portals, status pages, default chat shell) meet **WCAG 2.2 Level AA** for their scope: perceivable, operable, understandable, robust.

## Invariants touched

Supports **Covenant Principle 1** (non-discrimination includes disability), **Principle 10** (legible AI), and **Form** accessibility floor ([`genesis/FORM.md`](../genesis/FORM.md)).

## Verification

Automated `axe-core` CI on release bundles + annual manual audit logged to `ACCESSIBILITY_AUDIT.md`.

## Deprecation

WCAG versions advance; governance ratifies target level bumps.

---

## Scope boundaries

- **In scope:** Project-owned HTML/CSS/JS, default React reference client, generated docs templates.
- **Out of scope (best-effort guidance only):** Third-party integrator skins; user-generated creative outputs; low-level GPU renderers — still MUST respect `reduce_motion` and caption toggles from scene-intent.

## Concrete requirements (non-exhaustive)

- Keyboard navigable controls; visible focus.
- Color contrast ≥ AA for default palettes in `FORM.md` tables.
- Motion-reduction path disables non-essential animation < 200ms flashes.
- Screen-reader labels for mood/gesture changes via ARIA live regions (polite).

---

*Referenced from [`docs/00-INDEX.md`](./00-INDEX.md) and `genesis/FORM.md`.*
