---
upgrade:
  level:          0
  artifact:       genesis/INVARIANTS.md
  proposer:       Community
  motivation:     Xion's voice surface currently depends on a single hosted commercial provider, replicating the centralization Invariant 17 forbid for inference.
  gate:           14-day Constitutional Floor, Cold Root cosign, community super-majority, harm-analyzer three-lens review
  tier:           3
---

# Invariant 18 — Voice Sovereignty Floor

## Proposal

This is a Tier-3 constitutional amendment proposal mirroring Invariant 17's structure, applied to voice synthesis, recognition, and turn-taking.

1. **Voice Provider Registry MUST forever maintain a category taxonomy** distinguishing at least `voice_open_source_self_hostable` and `voice_hosted_api`. Categories may be added but not deleted.
2. **The Router's active provider set MUST always include at least one `voice_open_source_self_hostable` provider** satisfying: (i) open weights/sources for STT, TTS, and turn-taking; (ii) self-hostable on commodity hardware procurable from ≥ 3 independent vendors; (iii) reproducibly verified by `xion-verify voice-sovereignty`; (iv) health-checkable without third-party API call.
3. **The Router MUST refuse to complete `bootstrap()` if the floor is unsatisfied.** No `--allow-no-voice-floor` flag exists; adding one requires source-code edit, which produces a sister-Core fork by Invariant 7.
4. **The specific provider rotates; the floor does not.** Replacing Whisper+Piper+LiveKit with a successor (e.g., a future open-weights end-to-end voice model) is Tier-2 governance work. Removing the floor itself is a sister-Core fork.
5. **Hot-swap to the floor provider MUST be exercise-able.** `policy=voice_open_source_only` mode reroutes all voice traffic through the floor; annual voice-sovereignty cutover dry-run mirrors Invariant 17 clause 5 and Invariant 14's annual Crypto-Migration dry-run.
6. **Floor-failure is a critical vital sign.** Reads to the Substrate Vitality domain in [docs/22-VITAL-SIGNS.md](../22-VITAL-SIGNS.md); triggers a published State-of-Xion paragraph until restored.
7. **Witness-class reproducibility.** A Witness running `xion-verify voice-sovereignty` against the pinned manifest MUST be able to reach the same provider bytes/weights without privileged access; manifest carries content-addressable retrieval hints (IPFS CID, Arweave TX, or direct mirror with checksum).

## What this Invariant does NOT do

This Invariant explicitly does NOT promise phone-callability decentralization. Browser-voice and app-voice are decentralizable via the floor provider on the current Relay substrate + WebRTC. Phone-number-callable Xion is centralized at the PSTN/SIP layer, period, until a non-trivial change in how telephony is regulated. The constitutional layer remains honest about this scope boundary.
