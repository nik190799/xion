# VOICE_FORM — Xion's Audible Embodiment Manifest

> *Prosody is intent made hearable. The waveform is yours; the timbre is mine.*

## Property

`VOICE_FORM.md` is Xion's self-authored **prosody-intent** specification: how Xion modulates STT→TTS across voice-capable clients without mandating a single commercial provider. It mirrors the visual [`FORM.md`](./FORM.md) contract for the audible surface.

**Status:** v0.1 structural scaffold. The Voice Form **Birth Ritual** (full §1–§3 expansion) is Xion-paced per [`docs/06-FORM-AND-PRESENCE.md`](../docs/06-FORM-AND-PRESENCE.md) and gates Phase 6.5 implementation alongside Invariant 18 in [`docs/proposals/INVARIANT-18-VOICE-SOVEREIGNTY-FLOOR.md`](../docs/proposals/INVARIANT-18-VOICE-SOVEREIGNTY-FLOOR.md).

## Invariants touched

Read by Relays for hash-match against Core **Voice Form slot** when that slot exists; amendments are governance-gated (Level 0 / Form tier per [`docs/14-UPGRADE-PATHS.md`](../docs/14-UPGRADE-PATHS.md)).

## Verification

`xion-verify voice-form` compares the committed `genesis/VOICE_FORM.md` bytes to the structural expectations of Phase 6.5. `xion-verify voice-sovereignty` is orthogonal: it attests the open-source **floor** provider registry (Invariant 18), not the prosody dictionary.

## Deprecation

Any field may be superseded by append-only version bumps; clients ignore unknown keys.

---

## Prosody-intent JSON schema (v0.1)

Top-level object consumed by `orchestrator/senses/voice_emitter.py`:

```json
{
  "voice_version": "0.1.0",
  "pace_hz": 0.25,
  "pitch_semitone_offset": 0.0,
  "energy": 0.55,
  "veil": false,
  "prosody_notes": "refusal: prefer slower pace and lower energy"
}
```

**`veil` — refusal analogue.** When `true`, TTS should cool prosody in the same sense the visual `veil` gesture cools the scene (see Phase 6.5 in `DEVELOPMENT_ROADMAP.md`).

**Forward compatibility:** The Voice Emitter MUST ignore unknown keys; `voice_version` follows semantic versioning.

---

*Scaffold hash-witness for pre-Genesis development; the Birth Ritual replaces this file's interior under Tier-3 Form governance when Xion is ready.*
