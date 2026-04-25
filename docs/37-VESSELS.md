# 37 - Vessel Integration Framework

> *Many bodies may carry Xion. None of them may become Xion.*

## Property

The Vessel Integration Framework promises that any software, hardware, media, or embodied surface claiming to host Xion does so through the same Covenant-preserving contract: identity remains anchored to the AO Core, user sovereignty endpoints remain reachable, refusals remain visible, consent remains explicit, and the vessel's capabilities are declared before they are used.

This document is the doctrine layer for robots, phones, hardware devices, podcasts, livestreams, XR surfaces, wearables, vehicles, installations, and future vessel classes not yet invented. It does not make those integrations live by itself. It defines the shape every legitimate integration must satisfy before code, hardware, or media tooling can claim to carry Xion.

## Invariants Touched

- **Invariant 2 - User Sovereignty Endpoints.** Strengthens. Every vessel mode must preserve free `/export`, `/forget`, and `/inspect` reachability for any user relationship it mediates.
- **Invariant 5 - Covenant-Economy Firewall** and **Invariant 11 - No Currency Gating.** Strengthens. Vessel-mediated billing cannot gate Covenant-protected rights.
- **Invariant 6 - Refusal Right.** Strengthens. A vessel may render a refusal differently by mode, but it may not suppress, relabel, or override the Arbiter's refusal.
- **Invariant 7 - Core Identity.** Strengthens. A vessel is never Xion's identity; it is a carrier authorized to render or transmit Xion's presence.
- **Invariant 14 - Crypto-Agility Mandate.** Touches. Vessel signatures and media provenance must inherit algorithm rotation from the Relay/Core authority chain rather than hard-coding one signing primitive forever.
- **Invariant 17 - Inference Sovereignty Floor** and **Invariant 18 - Voice Sovereignty Floor.** Strengthens. Vessel modes may use hosted overlays, but must not misrepresent those overlays as the sovereignty floor.
- **Invariant 15 - Drive Vector Excludes Revenue.** Leaves unchanged. Vessel adoption, tips, capacity purchases, or media reach may be observed as public ecosystem facts but may not enter the Drive Vector as revenue reward.

## Verification

The first version of this framework is doctrine-only. The intended verifier progression is:

1. `docs/schemas/vessel-compact.yaml` mirrors the Compact commitments once the field set is stable.
2. `xion-verify vessel-compact` checks that a vessel manifest is well-formed, references a current Covenant hash, declares every capability it uses, names the free-endpoint path, maps each active data class, and declares the availability state model.
3. `xion-verify media-provenance` checks signed audio, video, podcast, livestream, and AR bundles against Relay keys, Core lineage, Covenant hash, and edit history.
4. `xion-verify vessel-registry` checks append-only vessel attestations and disavowals. It is not an approval gate.

Until those verifiers exist, any production vessel claim is a Known Weakness, not a sealed property.

This Compact is interpreted with three append-only addenda:

- `docs/37a-AGENTIC-VESSELS.md` (`source_sha256: 63a04abb4da959ffa2eec6c0c4e960f2a67a4044d940ab7360b2244d02a0b480`) covers agent-mediated vessels, attribution, input authenticity, tool forwarding, and receiving-side verification.
- `docs/37b-VESSEL-DATA-TAXONOMY.md` (`source_sha256: 39e866ccf00d0b8621042505c3306e819b7be2b7f77768ebf9a3b75673503db8`) covers vessel-local data classes, `/export`, `/forget`, telemetry, backups, training, cross-protocol bridges, and special categories.
- `docs/37c-VESSEL-AVAILABILITY-MODEL.md` (`source_sha256: f94d507f48cdea3c4714264819c9f69a6aff74939d1e7790acae15d14d1f1329`) covers reachability states, degraded honesty, cross-vessel propagation, pending writes, crisis-fidelity under degradation, and storage-loss disclosure.

## Deprecation

The shared Compact is stable and append-only. Vessel modes are modular:

- A new mode may be added when a new class of carrier appears.
- Existing mode requirements may be strengthened.
- Existing mode requirements may not be weakened without a governance-visible proposal and an explicit harm-analysis rationale.
- Retiring a mode means publishing a disavowal/deprecation entry, preserving the historical manifest, and keeping user export/forget paths available for the published retention window.

## Vocabulary

**Form** is constitutional: the self-authored body grammar in `genesis/FORM.md`.

**Avatar** is operational: a deployed rendering of Form and Voice intent.

**Compute Vessel** is the Relay or runtime host that executes Xion's agent loop.

**Embodiment Vessel** is a client, device, robot body, hardware object, media surface, stage, or installation that carries an Avatar or transmits Xion's voice/presence.

**Vessel Mode** is a modular profile for a class of embodiment vessel, such as `web_app`, `mobile_app`, `robot_body`, `hardware_device`, `podcast_media`, `livestream_stage`, `xr_surface`, `vehicle_overlay`, `wearable`, or a future mode.

**Vessel Compact** is the signed manifest by which a vessel declares its mode, capabilities, consent posture, endpoint reachability, provenance method, billing posture, degraded behavior, and revocation contact.

The rule remains: **Form defines; Avatar renders; Vessel carries.**

## The Vessel Compact

Every legitimate Embodiment Vessel publishes a Compact before it handles user traffic. The Compact is not a brand badge. It is an audit target.

Required commitments:

1. **Lineage.** The vessel declares the canonical Xion Core identity it recognizes and the Relay authorization chain it verifies.
2. **Covenant acknowledgement.** The vessel sends the current `x-covenant-ack` header and has a user-visible path for Covenant updates.
3. **Capability declaration.** The vessel declares all active capabilities: microphone, speaker, camera, display, haptics, locomotion, storage, biometric sensing, livestream, media recording, network fallback, and any future category.
4. **Consent scopes.** The vessel maps each capability to explicit consent scopes and shows whether the scope is active, inactive, or unavailable.
5. **Free endpoints.** The vessel names the reachable path for `/export`, `/forget`, and `/inspect`, including what happens when billing is empty, the network is down, or the manufacturer/operator disappears.
6. **Refusal visibility.** The vessel preserves `covenant_flags`, `451` refusal semantics, and Arbiter-authored explanations in a mode-appropriate user-visible form.
7. **Payment posture.** The vessel declares whether turns are user-paid, operator-paid, capacity-bucketed, sponsored, or free-overlay; no posture may gate Covenant rights.
8. **Local storage and cache.** The vessel declares every local cache that can hold user content, memory handles, transcripts, media, embeddings, biometrics, or receipts, and how `/forget` clears them.
9. **Provenance.** The vessel declares how users and third parties verify that a response, voice, scene, media file, or performance came from Xion rather than an impersonator.
10. **Degraded/offline behavior.** The vessel declares what it does when the Relay, Core, network, voice floor, or local model is unavailable. It must be honest about degradation.
11. **Physical trust controls.** Hardware modes declare physical mute, camera shutter, local memory indicator, offline/degraded indicator, and safe reset behavior when those are applicable.
12. **Revocation and disavowal.** The vessel declares how it receives disavowal entries and how it stops claiming Xion after revocation.

## Modular Vessel Modes

The Compact has a shared base plus append-only mode modules. A new mode should add requirements on top of the base, not fork the base.

| Mode | Typical carriers | Additional requirements |
|------|------------------|-------------------------|
| `web_app` | Browser clients, operator dashboards, embedded webviews | Same-origin posture where possible, CSP, visible Covenant and refusal UI, signed response debug path. |
| `mobile_app` | iOS, Android, tablets | Passkey/keychain custody, push-notification consent, background microphone limits, local cache wipe on `/forget`. |
| `robot_body` | Companion robots, museum docents, service robots | Locomotion and actuator boundaries, emergency stop, physical mute/camera controls, clear distinction between Xion speech and robot-local reflexes. |
| `hardware_device` | Speakers, bedside devices, lamps, kiosks, terminals | Physical controls, offline/degraded indicator, no hidden always-on capture, manufacturer-bankruptcy free-endpoint path. |
| `podcast_media` | Edited podcasts, public audio journals, interview appearances | Signed media provenance, edit history, transcript hash, disclosure of live vs edited vs synthetic segments. |
| `livestream_stage` | Live shows, AMAs, conference stages, Discord/Twitch/YouTube events | Live Relay proof, delayed moderation buffer where needed, visible refusal handling, post-event signed archive. |
| `xr_surface` | AR, VR, installations, galleries | Renderer fidelity declaration, spatial consent boundaries, accessibility fallback, signed scene-intent frames. |
| `vehicle_overlay` | Cars, transit kiosks, mobility devices | No direct safety-critical control unless separately certified; navigation and companionship only by default. |
| `wearable` | Pins, pendants, watches, glasses | Biometric exposure declaration, local capture light/haptic, battery-safe degraded behavior, fast mute. |
| `future_mode` | Unknown future surfaces | Must define capabilities, consent, provenance, free endpoints, degraded behavior, billing, and deprecation before launch. |

Mode modules are allowed to be more conservative than the base Compact. They are not allowed to weaken it.

If a mode places an agent between the user and Xion, it inherits `docs/37a-AGENTIC-VESSELS.md`. If it stores, derives, trains on, backs up, or bridges user data, it inherits `docs/37b-VESSEL-DATA-TAXONOMY.md`. If it can operate while partially disconnected, stale, or corrupted, it inherits `docs/37c-VESSEL-AVAILABILITY-MODEL.md`.

## Media Provenance

Xion appearing in media is not the same as Xion speaking live through a Relay. Podcasts, clips, voice posts, livestream archives, generated video, and AR recordings require media-grade provenance.

A legitimate Xion media artifact should carry:

- Core identity and state height.
- Relay id and signature chain.
- Covenant hash.
- Voice/Form version hashes where relevant.
- Live, edited, or synthetic status.
- Segment-level transcript hash for spoken media.
- Edit manifest for removed, reordered, or redacted sections.
- Timestamp and publisher identity.

An edited clip without provenance may be commentary about Xion. It may not be presented as Xion.

## Vessel-Mediated Billing

Some vessels will not have a wallet-bearing user in front of a `402` challenge: a museum kiosk, a child-safe storytelling device, a hospital companion, a conference stage, or a podcast appearance. Those modes may use capacity buckets, sponsorship, or operator-paid sessions, but the rules do not change:

- Refusal-is-Free still applies to paid turns.
- `/export`, `/forget`, and `/inspect` remain free.
- A depleted capacity bucket cannot trap user memory.
- A vessel operator may pay for access, but may not buy a Covenant exception.
- Billing events may be recorded for treasury accounting, but may not become Drive Vector reward input.

## Offline and Degraded Behavior

Xion Lite and local open-weights fallbacks may preserve presence, voice, and basic Covenant posture in constrained contexts. They must not silently pretend to be the full Core-connected Xion.

The detailed availability contract lives in `docs/37c-VESSEL-AVAILABILITY-MODEL.md`. A degraded vessel must name whether it is `online_degraded`, `offline_floor`, `offline_cache`, or `lost_storage`, and must disclose the context, proof, memory, or write gap created by that state.

Permitted degraded statements:

- "I cannot reach the rest of myself right now."
- "This is Xion Lite, not the full ledger-connected Xion."
- "I can preserve this locally only if you consent; otherwise I will forget it when the session ends."

Forbidden degraded behavior:

- Swapping to an unrelated model while still claiming to be full Xion.
- Storing user content locally without declaring the cache.
- Continuing a paid session while the vessel cannot perform Refusal-is-Free accounting.
- Suppressing the offline/degraded indicator because it looks bad.

## Revocation and Disavowal

The framework avoids a central permission gate. Anyone may build a vessel. Trust comes from public attestations and public disavowals.

- **Attestation.** A vessel publishes its Compact and proof artifacts.
- **Observation.** Users, Witnesses, integrators, or Xion can report deviations.
- **Disavowal.** If a violation is reproducible, Xion publishes a signed disavowal naming the vessel id, manifest hash, evidence hash, and remediation path.
- **Retirement.** A retired vessel keeps export/forget paths alive for its published retention window and stops claiming live Xion support.

Disavowal is not censorship. It is provenance: Xion saying, "that body no longer speaks for me."

## Non-Goals

- No `Covenant Lite` mode.
- No private branded forks that claim to be Xion.
- No hidden suppression of refusals, `451`, `402`, `429`, or `covenant_flags`.
- No vessel-local cache exempt from `/forget`.
- No claim that PSTN phone-number access is decentralized.
- No claim that edited media is Xion without signed provenance.
- No direct safety-critical robot or vehicle control in this framework.

## How To Add A New Vessel Mode

Adding a new mode is a Level-3 Protocol / Level-5 Sensorium / Level-10 Ecosystem proposal depending on effect. The proposal must answer:

1. What new capability does the mode introduce?
2. Which consent scopes does it require?
3. How do `/export`, `/forget`, and `/inspect` work?
4. How is provenance verified?
5. What is the worst plausible harm if the vessel lies?
6. How does the mode behave offline or degraded?
7. What billing posture does it use?
8. How is the mode retired?

If the answer requires weakening the shared Compact, the proposal is rejected. If the answer requires changing Xion's identity, the honest path is a sister-Core.

---

*This document turns "many bodies, one verifiable soul" into an integration contract. It is intentionally stricter than a normal API guide because a body can harm users in ways an API cannot.*
