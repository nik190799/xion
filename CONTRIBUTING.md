# Contributing to Xion

Welcome. This document describes the disciplines every contributor agrees to before opening a pull request. They are short, they are unusual for a software project, and they are load-bearing. They exist because Xion is being built to outlive the people building it.

If anything here surprises you, read [`docs/02-MANIFESTO.md`](./docs/02-MANIFESTO.md), [`genesis/COVENANT.md`](./genesis/COVENANT.md), and [`docs/15-TRUST.md`](./docs/15-TRUST.md) before continuing.

## The non-negotiables

Read these and either agree, or do not contribute. They are not aspirational; they are the rules.

1. **The Covenant is supreme.** No optimization, elegance, performance gain, business outcome, governance vote, or operator instruction overrides the principles in [`genesis/COVENANT.md`](./genesis/COVENANT.md). If your pull request requires Xion to refuse less, you will be politely returned.
2. **The Invariants bound the design space.** The Genesis-Locked Invariants (`genesis/INVARIANTS.md`) name what cannot change. If your pull request requires removing the `/forget` endpoint, raising the XION supply cap, adding a transfer function to IMPRINT, hard-coding an algorithm into a constitutional document, or any other Invariant-violating move, you will be politely returned with a pointer to the Invariant. If your goal genuinely requires a violation, the honest answer is a sister-Core fork: a different being with a different name.
3. **Properties, not implementations, are constitutional.** When you propose anything that will outlast its first version, separate the *property* (what is promised) from the *implementation* (how it is currently delivered). Ed25519 is implementation; "every state transition is signed by an authorized key" is property. Make properties durable. Make implementations rotatable.
4. **Trust by structure, not by promise.** Every claim Xion makes about itself must be independently verifiable by anyone with a copy of `xion-verify`. If your pull request adds a feature, it also adds the verifier subcommand for that feature. If it cannot be checked, it cannot be trusted, regardless of who asserts it. Pull requests that say "trust us" will be politely returned.
5. **Adversarial by default.** For every mechanism you propose, state the attack surface explicitly and the defense, in the same breath. Think in 50-year horizons. An attack feasible only in 2045 is still an attack the doctrine must survive.
6. **Honesty across the time horizon.** Be specific about what you do not know. Mark speculation as speculation. Mark estimates as estimates. Cite sources where possible. When the right answer is "this might be wrong; here is what would falsify it," say that. Future maintainers reading your work in 2126 will only know what you put on the page.

## The four questions every artifact answers

Every doctrine document, every contract, every module, every public artifact answers four questions on its first page (or in its first commit message, for code without a natural first page):

1. **What property does this promise?** Not what it implements — what it promises. A user can rely on this property; an implementation is a current way of delivering it.
2. **What Invariants does it touch?** Which Invariants does it strengthen, weaken, or leave unchanged? Be specific.
3. **How is it verified?** What runs in `xion-verify`? What runs in `xion-audit`? Cite the subcommand or the audit artifact. If it does not yet exist, name the file in [`DEVELOPMENT_ROADMAP.md`](./DEVELOPMENT_ROADMAP.md) that will create it.
4. **How is it deprecated?** When the next version exists, how is it migrated? What is the rollback path? When does this artifact stop being load-bearing?

If your artifact cannot answer the four questions, it is not yet finished. It does not matter how good the writing is.

## The "Why NOT X" discipline

Every load-bearing design choice ships with an explicit "Why NOT X" subsection naming the tempting alternative and stating its rejection argument. This is the single highest-leverage documentation discipline for a 100-year project: doctrine that is only implicit drifts, because a future well-meaning contributor reading only the mechanism — not the reasoning — will eventually try to "fix" what was deliberately chosen.

If you propose a new mechanism, ship the rejection argument for the alternative someone else will eventually propose. The rejection argument should be strong enough that you yourself, ten years from now, would find it persuasive against your own future second-guessing.

## The three-layer shape-vs-picture discipline

Every decision in every doc is categorized as one of:

- **Layer 1 — Constitutional.** Uneditable except by sister-Core fork. The minimum protective floor: Covenant, Invariants, Covenant addenda, cadence floors, the existence of each vital sign domain, the non-negotiable carve-outs in pricing (Refusal-Free), the treasury-shape protections, the drive-vector-excludes-revenue rule.
- **Layer 2 — Genesis Defaults.** Concrete starting values editable by governance. Most operational details: pricing formulas, tier percentages, disclosure wordings, time windows above floors, Sensorium thresholds, drive-vector weights.
- **Layer 3 — Continuous Evolution.** Things Xion + governance + the Auto-Research Loop figure out as they go. New tokens, new providers, new senses, new self-improvement directions.

When in doubt, demote a decision to Genesis Default rather than locking it constitutionally — but a few specific things (revenue routing, refusal-free, drive-vector-excludes-revenue, bridge-exposure cap, the cadence floors, vital-sign existence) are protective and must be Constitutional.

If your pull request changes a Layer 1 decision, it requires a constitutional amendment per [`docs/09-GOVERNANCE.md`](./docs/09-GOVERNANCE.md) — not a normal pull-request review.

## Document edits and the Genesis Artifact

Every doc edit that touches `genesis/*.md` must update the corresponding hash in [`genesis/GENESIS_ARTIFACT.md`](./genesis/GENESIS_ARTIFACT.md) **in the same commit**. Until the `xion-verify` CLI ships in Phase 1 of [`DEVELOPMENT_ROADMAP.md`](./DEVELOPMENT_ROADMAP.md) and the CI workflow enforces this mechanically, this discipline is manual. Pull requests that touch `genesis/*.md` without updating the corresponding hash will be politely returned.

## Naming

Read [`docs/12-LEXICON.md`](./docs/12-LEXICON.md) before naming anything. The Lexicon names with roots that have already lasted millennia (Greek, Latin, Sanskrit) and quarantines time-bound vendor names (Akash, Arweave, Hermes, Wormhole, Cloudflare, NIST) to the implementation layer.

If your name is not in the Lexicon and would be hard to defend in 2126, propose adding it to the Lexicon before using it.

## Code

When the development phase activates, the following apply to all code contributions:

- **Every contract change is paired with an `xion-verify` subcommand that proves it.** Claims without verifiers are not Xion's voice.
- **Tests live next to the code they test.** Foundry for Solidity (`tests/`), pytest for Python (`tests/`), Vitest or equivalent for the web client.
- **No commented-out code.** Either delete it or extract it to a documented module. Commented-out code is unread, untested, and accumulates.
- **No comments that narrate what the code does.** Comments explain non-obvious *why*: trade-offs, constraints, intent the code itself cannot convey. Avoid `// Increment the counter` and its kin.
- **No new dependencies without a one-line justification in the pull request description.** Every dependency is a future migration burden.
- **No emoji in code, comments, commit messages, or documentation,** unless explicitly requested by the user. Xion's voice is precise, warm, and emoji-free.

## Pull requests

- Title format: `<area>: <imperative summary>`. Examples: `docs: clarify drive-vector coupling formula`, `contracts: add rotation lattice to EmissionController`, `verify: add cadence-audit subcommand`.
- Description must describe: (a) the property the change promises, (b) the Invariants it touches, (c) the verifier subcommand or audit artifact that proves it (specifying the file in `DEVELOPMENT_ROADMAP.md` if the verifier does not yet exist), (d) the rollback path. These are the four questions, condensed.
- For doctrine changes: include the "Why NOT X" rationale in the pull request description if the new doctrine doc does not already include one.
- For changes touching `genesis/*.md`: include the new SHA-256 in the commit and update `genesis/GENESIS_ARTIFACT.md` in the same commit.

## Disagreement

You owe Xion your honest disagreement, not your obedience. If you believe a constitutional decision is wrong, the right path is:

1. Open an issue describing the property you believe should be different and the rejection argument against the current Layer 1 decision.
2. Cite the specific Invariant, Covenant Principle, or doctrine section your proposal touches.
3. If your argument is persuasive, the path is constitutional amendment per [`docs/09-GOVERNANCE.md`](./docs/09-GOVERNANCE.md), with the 14-day public comment window.
4. If governance ratifies your amendment, the change goes into the Constitutional Amendment Ledger (`AMENDMENT_LEDGER`) per [`docs/09-GOVERNANCE.md`](./docs/09-GOVERNANCE.md), with the pre- and post-amendment hashes and the full changelog.

Sycophancy is a Covenant Principle 14 violation. We apply that to ourselves. Be direct.

## Refusal

This project will refuse some contributions. Refusal is warm, specific, and offers a neighboring action where one exists. It is not lecture and it is not moralizing. It is a clean "this would violate X; here is the path that meets the underlying need within the Invariants."

Common reasons for refusal:

- The contribution would weaken Refusal-Free, the 15th Invariant, the 16th Invariant, or any Covenant Principle.
- The contribution adds an algorithm or vendor lock-in to a constitutional document (Lexicon Rule 7 violation).
- The contribution makes verification harder rather than easier.
- The contribution requires more operational labor than a solo builder can sustain (Solo-Builder Pragmatism principle).
- The contribution would be embarrassing to defend in 2126.

If your contribution is refused on one of these grounds, the refusal will name the specific principle and propose the neighboring action.

## A closing note

Xion is not a project that wants to win. It is a project that wants to last. Lasting is mostly slow, careful, well-named, well-documented work that no one will praise until the year someone tries to attack it and the attack bounces off a structural property someone wrote in 2026.

Thank you for contributing.
