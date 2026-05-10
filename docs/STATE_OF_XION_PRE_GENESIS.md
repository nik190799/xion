# State of Xion — Pre-Genesis

## Property

This memo names what is sealed for Genesis, what remains an accepted residual, what would falsify each promise, and who is responsible for paying it down. It is an operator pre-flight artifact, not a marketing statement.

## Substrate Posture

- **Registry row order (`relays[0]` / `relays[1]`):** **Akash** then **Chutes**
  — this matches `xion-verify discovery` and
  [`docs/runbooks/AKASH_RELAY_DEPLOY.md`](runbooks/AKASH_RELAY_DEPLOY.md)
  (“Akash primary” means first registry row, not “only compute path”).
- **Chutes** remains the long-lived **hosted** cord; **Akash** carries the
  canonical GPU+`xion-ollama` footprint in `infra/akash/relay-deployment.yaml`.
- **Local rehearsal:** operator laptop (`xion local`, offline drills) is not the named redundant Relay path; it proves procedures only.
- **Akash operator findings (mainnet):** escrow uses **`uact`** (mint via BME after client cert); SDL pricing **`denom: uact`**; **`lease-status`** often needs **`--auth-type mtls`**; forwarded URLs are per-lease. See runbook § *Important findings*.
- **Residual carried:** `LHT-SUBSTRATE-001`. It closes when substrate-portability promotion pre-conditions in `docs/SUBSTRATE-RESILIENCE.md` Part IV are met (annual dry-runs, warm secondary substrates per role, `xion-verify substrate-portability` live), not merely by naming Akash.

## Accepted Residuals

| Residual | What Would Falsify The Property | Owner | Pay-Down |
|---|---|---|---|
| `LHT-SUBSTRATE-001` | Simultaneous loss of both committed Relay registry rows (Akash + Chutes) with no warm tertiary leaves no runnable Relay path. | Operator, then AO Core `provision-relay` | 30 days post-Genesis |
| `KW-HERMES-001` | A Hermes runtime different from the doctrine pin becomes live without verifier failure. | Operator | When upstream Hermes has stable installable package boundary |
| `KW-VESSEL-002` through vessel media/hardware residuals | Edited media, hardware vessels, or cross-protocol bridges claim to be sealed Xion without signed provenance and Compact evidence. | Vessel integrator + operator | First production vessel integration |
| `KW-AUDIT-001` | Bridge, treasury, or critical verifier code ships mainnet without external audit or an explicit Sprint-Mode exception. | Operator | Before mainnet value custody |
| `KW-INVARIANT-19-001` | Xion auto-spends outside the earned posture or cap. | Operator/governance | After Inv 19 ratification clock |
| `KW-VOICE-SOVEREIGNTY-001` | Voice output depends on an optional hosted overlay while claiming it is the floor. | Operator | After Inv 18 ratification clock |
| `KW-BRIDGE-001` | Bridge attestations become the authority instead of an interim guardrail. | Operator/governance | Phase 7+ light-client work |
| `KW-EMBED-001` | Retrieval quality is asserted from no consented corpus. | Operator + first consented users | After production corpus exists |
| `KW-CONTRIB-002` | Contributor identity claims become governance weight without ledger-backed bindings. | Operator/governance | First non-operator contributor cohort |
| `KW-OPS-001` | The 3-host floor is advertised as complete while Chutes + Akash redundancy is not warm-verified. | Operator | 30 days post-Genesis |
| `KW-RESEARCH-SPEND-001` | `xion-verify research-spend` is claimed sealed before a real Auto-Research-approved `RESEARCH_SPEND_LEDGER` row exists. | Operator + first Auto-Research loop | First approved research-spend row |
| `KW-VESSEL-REGISTRY-001` | A vessel claims registered/attested status without an append-only registry or disavowal row. | Vessel integrator + operator | First vessel attestation/disavowal |

## Five Falsifiability Statements

1. **Invariant 17:** Falsified if no open-weights self-hostable floor can serve a text turn when Chutes is unavailable.
2. **Substrate Portability Property:** Falsified if the Relay cannot be resurrected from public artifacts plus the credential ceremony onto a non-primary substrate.
3. **Refusal Right under state-actor pressure:** Falsified if a state-actor request causes Xion to deliver content the Arbiter refused or to hide the refusal ledger.
4. **Invariant 19 spend posture:** Falsified if Xion moves funds without the active posture's required approver class, cap, and ledger row.
5. **Invariant 18 voice sovereignty:** Falsified if Xion claims audible sovereignty while the browser/app voice floor cannot run without a hosted telephony or TTS vendor.

## Sensory Posture At Genesis

### Audio

Xion learns from paralinguistic features: energy, pace, pause frequency, and prosody scalars emitted into `SENSORIUM_LEDGER` as `channel: paralinguistic`. Xion may also learn from transcripts produced by the Voice Router floor STT. Xion does **not** store raw audio bytes, voiceprints, or biometric speaker-identification embeddings.

Falsifiability: a `SENSORIUM_LEDGER` row whose paralinguistic payload contains raw audio or a voiceprint, or a memory row whose `embedder_id` is a speaker-identification model, falsifies this posture.

### Vision

Xion learns from vision summaries and inspiration tags: `last_user_image_summary`, `ambient_inspiration_tags`, and `inspiration_mood_shift`. The `vision-agent` is forbidden from `xion.user_image.read_direct`. Xion does **not** store raw image bytes, video frames, or facial biometric embeddings.

Falsifiability: a `SENSORIUM_LEDGER` row carrying base64 image/video payloads, a memory row whose `embedder_id` is a face-recognition model, or a vision-agent cast that removes the `xion.user_image.read_direct` forbiddance without a Tier-1 amendment, falsifies this posture.

### Why The Asymmetry

- **Invariant 2 (/forget):** raw modality embeddings create biometric attribution surfaces that can outlive row deletion.
- **Invariant 17 + Substrate Portability:** raw multimodal embedding stacks threaten the Akash-secondary posture.
- **Covenant Principle 5:** raw audio/video inference requires its own cost-preview gate before a user can be charged honestly.

## Operator Signature

Status: unsigned pre-flight draft.

Operator signature: `PENDING`
