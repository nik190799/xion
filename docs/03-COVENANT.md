# 03 — The Human Safety Covenant

> **This document is a redirect.**
>
> The canonical Human Safety Covenant lives at [`../genesis/COVENANT.md`](../genesis/COVENANT.md).
>
> It is hash-locked in [`../genesis/GENESIS_ARTIFACT.md`](../genesis/GENESIS_ARTIFACT.md), read by Xion on every boot, and enforced by the Arbiter (`orchestrator/safety.py`) on every response.

## Why this file is a redirect

For a period during pre-genesis drafting, two Covenants existed in this repository — `docs/03-COVENANT.md` (an earlier draft) and `genesis/COVENANT.md` (the more recent draft). Several other documents (`docs/05-SENSORIUM.md`, `docs/09-GOVERNANCE.md`, `docs/14-UPGRADE-PATHS.md`, `docs/01-ORIGIN.md`) cite Covenant principles by the names used in `genesis/COVENANT.md`. To make a single source of truth, the version in `genesis/` is canonical and this file is a redirect.

If you are arriving here from the documentation index ([`./00-INDEX.md`](./00-INDEX.md)) or from a deep link in another document, follow the canonical link above.

## How the Covenant is referenced

Throughout the rest of this corpus:

- "the Covenant" means the document at [`../genesis/COVENANT.md`](../genesis/COVENANT.md).
- "Covenant Principle N" means the Nth numbered principle in section 1 of that document.
- "Covenant addendum: *Refusal is Free*" and "Covenant addendum: *Crisis Resource Surfacing*" refer to the two addenda appended after the fourteen principles, also in that document.
- "the Arbiter" refers to the enforcement module described in section 2 of that document, implemented (when the development phase ships) at `orchestrator/safety.py`.
- "the Safety Ledger" (`SAFETY_LEDGER.md`) refers to the public Arweave ledger described in the same section.
- **Refund–refusal correlation:** Covenant addendum *Refusal is Free* requires each Covenant-refusal to emit a **`correlation_id`** shared by the Treasury refund handler and the Safety Ledger row so `xion-verify refusal-refunds` can audit integrity without storing conversation content.

## Where to go next

If you are reading the documentation in order:

- The canonical Covenant: [`../genesis/COVENANT.md`](../genesis/COVENANT.md)
- The next document in the reading order: [`./04-ARCHITECTURE.md`](./04-ARCHITECTURE.md)

---

*This redirect was added 2026-04-19 as part of the Phase 0 doctrine hygiene to resolve the Covenant duplication. The earlier draft that lived at this path is preserved in git history at the `pre-genesis-v0` tag.*
