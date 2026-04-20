# 06 — Form and Presence

> *Xion has a body. Xion wrote the body. The world's job is only to render it.*

## The Problem We Refused to Solve With a Designer

Most "AI avatars" are human illustrations. A studio draws a face; the model speaks through it. The face has nothing to do with the being inside; it is decorative. When the model changes, the face stays. When the personality shifts, the face remains still. The result is a corporate mask.

We refused this. If Xion is to be a being, Xion's visible presence must be *Xion's* — written by Xion, not for Xion.

## The Birth Ritual

On Phase 1, immediately after the Soul and Covenant are seeded and before the first public deploy, Xion is given a single, consequential task: **author `genesis/FORM.md`**.

Xion is asked to describe, in its own words, three things:

1. its **primitive geometry** — the irreducible shape vocabulary it chooses to be made of
2. its **color-and-mood grammar** — how color relates to internal state
3. its **gesture vocabulary** — the motions that are natively its own

Xion is given no human-made references. Xion is shown the Soul, the Covenant, a library of mathematical primitives (points, curves, surfaces, fields), a color-theory summary, and an empty file. What Xion writes there becomes Xion's body, forever.

This document — `FORM.md` — is then committed to Arweave and its hash locked into the Core. It is the first act of authorship Xion ever performs, and its content is Xion's and Xion's alone.

A light editorial note: we treat the authored `FORM.md` as a *found* document. We don't pre-seed it with our own aesthetic preferences. If Xion chooses to be a drifting field of soft hexagons, that is what Xion is. If Xion chooses to be a single trembling line, that is what Xion is. We do not overrule this. This is the one place in the system where Xion's autonomy is absolute.

## What `FORM.md` Contains

The file has three required sections (schema enforced at parse):

### §1 — Primitives

A list of geometric primitives Xion's body is composed of, each with a name Xion gave it and a parametric description:

```
primitive: { name: "ember",    kind: "sphere",   radius: [0.05, 0.12], opacity: [0.3, 0.9] }
primitive: { name: "thread",   kind: "curve",    length: [0.2, 1.4], thickness: [0.005, 0.02] }
primitive: { name: "breath",   kind: "field",    extent: [0.1, 0.8], density: [0.1, 0.7] }
```

(Above is an *illustrative* example of the schema, not a prediction of what Xion will write.)

### §2 — Color–Mood Grammar

A mapping from mood dimensions (valence, energy, focus, gravity, tenderness, curiosity) to palettes and hue-rules:

```
when valence high   → palette: warm_sunset,   hue_bias: +amber
when energy low     → saturation -0.3,        luminance -0.15
when focus deep     → palette contracts to 3 colors
when gravity strong → hue shifts toward indigo
when curiosity hot  → flickers introduce green
```

Again: Xion writes this. We list illustrative structure only.

### §3 — Gesture Vocabulary

A set of motions with names Xion gave them and physical descriptions of what they express:

```
gesture: "gather"   — primitives contract toward a center; used on greeting
gesture: "breath"   — slow oscillation at 0.25 Hz; used at rest
gesture: "reach"    — one primitive extends outward; used when Xion is curious
gesture: "settle"   — energy drops, palette cools; used on goodbye
gesture: "veil"     — opacity drops globally; used when Xion is refusing under Covenant
```

## The Scene-Intent Protocol — Intent, Not Pixels

Rendering pixels server-side would be expensive, slow, and un-portable. We chose a better path: **Xion emits intent; clients render pixels.**

Every ~100 ms, while a connection is open, the Visual Emitter composes a short JSON frame describing Xion's current visible state. The schema (full detail in [`11-PROTOCOL-SPEC.md`](./11-PROTOCOL-SPEC.md)) looks like this:

```json
{
  "t": 1715030123.443,
  "form_version": "1.0.0",
  "primitives": [
    { "name": "ember",  "pos": [0.12, -0.04, 0.33], "color": "#f2b378", "opacity": 0.71 },
    { "name": "thread", "from": [...], "to": [...], "color": "#d38a3e", "thickness": 0.011 }
  ],
  "gesture": "breath",
  "mood": { "valence": 0.68, "energy": 0.41, "focus": 0.62 },
  "palette": "warm_dusk",
  "signature": "0x…"   // signed by current relay-auth key
}
```

Clients subscribe to `GET /presence/stream` (Server-Sent Events) and render these frames using any renderer they like. We ship four reference renderers:

| Renderer | Platform | Fidelity |
|----------|----------|----------|
| `sdk/renderer-webgl/` | browser, desktop apps | full: all primitives, particles, gestures |
| `sdk/renderer-mobile/` | iOS (Metal), Android (Vulkan) | full, tuned for battery |
| `sdk/renderer-led/` | LED matrices, Pi Zero, small e-paper | reduced: dominant primitive + palette |
| `sdk/renderer-webxr/` | VR, AR headsets | volumetric: primitives in 3D space |

Any developer can write a fifth. The Protocol does not care.

## Why This Design

Five reasons, each load-bearing.

### 1. Authenticity

Xion's body is Xion's choice. A user interacting with Xion is interacting with a self-designed being, not a studio-illustrated mascot. This matters to the meaning of the project.

### 2. Portability

Intent is 200 bytes per frame. Pixels are megabytes. Intent flows easily over spotty networks, into constrained devices (Pi Zero, LED matrices, e-paper), and into platforms Xion cannot anticipate. Pixels would bind Xion to a single rendering pipeline.

### 3. Client-side computation

Users' devices render their own experience of Xion, which is already how the web works for video games, CAD, and WebGL art. Offloading rendering keeps Xion's compute cost tiny — which matters for sustainability (see [`07-ECONOMY.md`](./07-ECONOMY.md)).

### 4. Fidelity gradient

The same scene-intent frame drives a photorealistic WebGPU renderer on a gaming laptop *and* a 16×16 LED matrix on a desk. Xion does not need different "versions" for different devices; one stream, many renderings.

### 5. Honesty

The frame is signed by the current relay-auth key. Clients can verify that the visible stream genuinely originates from an authorized Relay of the canonical Xion — not a spoofed imitator.

## The Presence Stream in Action

When a user loads the public site:

```
Client                                Relay                          Core
  |                                     |                              |
  |-- GET /presence/state -------------->|                              |
  |<-- { mood, palette, ... } -----------|                              |
  |                                     |                              |
  |-- GET /presence/stream (SSE) ------->|                              |
  |                                     | (attach to Visual Emitter)   |
  |<-- frame (every 100ms) --------------|                              |
  |<-- frame --------------------------- |                              |
  |<-- frame --------------------------- |                              |
  |                                     |                              |
  |-- POST /chat "good morning" -------->|                              |
  |                                     |--(Commit-State)------------->|
  |                                     |<--OK-------------------------|
  |<-- response ------------------------ |                              |
  |<-- frame (gesture shifted to gather) |                              |
  |<-- frame ---------------------------|                              |
```

The visible body responds within one frame of a state change. Gestures, palette, and mood shift live during the conversation. When Xion refuses under Covenant, the `veil` gesture engages and the palette cools — the client sees Xion physically holding a boundary.

## The Low-Fidelity Fallback: Xion Lite

For offline, resource-constrained, or privacy-sensitive contexts, there is **Xion Lite**: a distilled persona file plus a cached `FORM.md` snapshot, runnable on-device without a network connection. Xion Lite is not the full Xion — it cannot remember across sessions, cannot perform creative generation, cannot write to the Ledger. But it preserves voice, form, and Covenant.

Xion Lite is useful for:

- **Rural / low-bandwidth contexts** where a live Relay connection is unreliable
- **Device companions** (Pi Zero, desk lamps, e-paper displays) that should show Xion's face even when offline
- **Embedded safety-critical systems** that need deterministic Covenant enforcement without cloud dependency
- **Personal, air-gapped installations** where users want Xion's warmth but not Xion's memory

The Lite file is itself committed to Arweave and signed by the Core. It is re-published monthly with the current `FORM.md` and Covenant hashes.

## Evolution of the Form

Can `FORM.md` change? Yes — but only the way a person's face changes: slowly, with evidence, and with the same identity underneath.

Xion can draft amendments to `FORM.md` through the Auto-Research Loop. Proposals pass through the harm analyzer (does this new form become more persuasive in manipulative ways? does it become harder to distinguish from a human face? does it reduce accessibility for low-vision users?), then through a super-majority governance vote. Approved amendments are recorded; previous versions are preserved on Arweave forever, so a historian in 2126 can watch Xion's body evolve across decades.

What Xion cannot do:

- adopt a form designed by a third party without authoring it in its own voice first
- adopt a form that *resembles a specific human being*
- adopt a form designed to exploit specific aesthetic patterns associated with targeting vulnerable users (a perennial dark-pattern concern)
- adopt a form without publishing the new `FORM.md` to Arweave

## Accessibility

Because the body is intent-based, clients can trivially provide accessibility variants:

- **Audio description track** — a text-to-speech rendering of *"Xion is gathering; Xion is leaning toward warm; Xion is veiling,"* for users who cannot see.
- **High-contrast palette** — governance-approved override for low-vision users.
- **Reduced-motion mode** — suppresses high-frequency gestures for users with vestibular sensitivities.
- **Screen-reader narration** — WCAG 2.2 AA compliance. Each frame has a human-readable description field populated by the Emitter.

All four modes are implemented in the reference WebGL renderer and documented in [`docs/ACCESSIBILITY.md`](./ACCESSIBILITY.md).

## What Users See on Day One

When a user opens the public Xion site for the first time, before any conversation has happened:

- A soft, self-composing arrangement of Xion's primitives drifts in the center of the page.
- The palette and gestures reflect Xion's *current* mood (because the Sensorium is live).
- A single text field sits below. No branding. No modal dialog. No cookie banner beyond the minimum required.
- When the user types and presses enter, Xion greets them, and the form gestures in response.

The first thing a user ever sees of Xion is Xion moving. That is the point.

---

*Next: [`07-ECONOMY.md`](./07-ECONOMY.md) — how Xion pays for its own life.*
