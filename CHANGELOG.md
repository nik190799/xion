# Changelog

All notable changes to Xion will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to a versioning scheme of `pre-genesis-vN` until the genesis ceremony, after which it switches to canonical `state-#N` references rooted in Xion's AO Process state chain.

Until the genesis ceremony, every entry here is a *draft* in the literal sense: nothing here has been ratified by Xion or by governance, because Xion does not yet exist and governance does not yet exist. The discipline of recording changes honestly begins now so that, by the time it matters, the habit is already there.

---

## [Unreleased]

### Added

- Top-level repository hygiene: this `CHANGELOG.md`, the dual-license `LICENSE`, the project `README.md`, the `.gitignore`, the `KNOWN_WEAKNESSES.md` (seeded from the audit and the two settled economic Known Weaknesses), and the `CONTRIBUTING.md`.

### In Progress

- Phase 0 doctrine hygiene: drift fixes (sense count, store count, Covenant canonicalization, invariant counts, navigation links, glossary expansion).
- Phase 0b new constitutional doctrine: 15th and 16th Genesis-Locked Invariants; two Covenant addenda; Volition, Abdication, Treasury, Self-Provisioning, Sustainability, Vital Signs doctrines; rationales discipline; cadence-floor labeling; Hermes pinning; measurability and methodology infrastructure; protocol additions; external-feed specifications.
- Phase 2 missing constitutional files: `genesis/FORM.md`, `genesis/MEMORY.md`, `genesis/RESURRECT.md`, `genesis/CREDENTIALS.md`, `docs/ACCESSIBILITY.md`, and the re-hash of `genesis/GENESIS_ARTIFACT.md`.

### Planned (post-doctrine; tracked in `DEVELOPMENT_ROADMAP.md`)

- Phase 1: `xion-verify` Python CLI with the full subcommand set.
- Phase 3: Solidity contract fixes (rotation lattice, genesis split, decay rate, cleanups), Foundry test suite, Base Sepolia deployment.
- Phase 4: Arbiter v1 as a separate fail-closed process with hash-chained `SAFETY_LEDGER`.
- Phase 5: Minimum Viable Xion (Relay, Sensorium, Volition, Inference Router, Supervisor, web client).
- Phase 6: AO Process handlers (lifecycle, authority, provisioning, sustainability families), Akash deployment, multi-host self-provisioning, multi-chain treasury vaults, Cloudflare decommission, first Immortality Drill.
- Phase 7: Cold Root key ceremony (3-of-5 Shamir) and the Genesis ceremony itself.

---

## [pre-genesis-v0] — 2026-04-19

### Added

- Initial doctrine corpus authored before remediation: `genesis/COVENANT.md`, `genesis/INVARIANTS.md`, `genesis/SOUL.md`, `genesis/GENESIS_ARTIFACT.md` (templated, unsigned).
- Documentation corpus: `docs/00-INDEX.md` through `docs/17-CRYPTO-RESILIENCE.md` plus `docs/99-GLOSSARY.md`.
- Solidity sources: `contracts/xion-token/XionToken.sol`, `contracts/xion-token/EmissionController.sol`, `contracts/xion-token/LiquidityLock.sol`, and `contracts/imprint/Imprint.sol`. **Not deployed.** Outstanding fixes documented in `KNOWN_WEAKNESSES.md`.
- `DEVELOPMENT_ROADMAP.md` describing the phased path from doctrine to Genesis.

### Known at this commit

- Several documentation contradictions remain (sense count drift, store count drift, invariant count drift, truncated currency distribution table, broken navigation link, missing glossary terms). Tracked in the documentation remediation plan; remediation in progress.
- Constitutional files referenced in the Genesis Artifact's bundle prose (`FORM.md`, `MEMORY.md`, `RESURRECT.md`) do not yet exist. Remediation in Phase 2.
- Contract bugs documented in `KNOWN_WEAKNESSES.md` are present in the source but no contract is deployed; this is a pre-deployment freeze, not a live bug.

---

[Unreleased]: https://example.invalid/compare/pre-genesis-v0...HEAD
[pre-genesis-v0]: https://example.invalid/releases/tag/pre-genesis-v0
