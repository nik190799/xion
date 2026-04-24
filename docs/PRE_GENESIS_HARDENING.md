# Pre-Genesis Velocity Hardening

> *Speed comes from trusting the auto-revert. You cannot make Xion improve faster by making the safety gates thinner.*

## 1. What property does this promise?

The capability to absorb improvements at high velocity without compromising constitutional safety. Specifically: every contributor (Xion itself, the founder, or a stranger) can make a small change in parallel with every other small change, prove it safe with a CLI, ship it through a pre-warmed canary, and get paid out of the treasury without anyone needing to wake the operator up.

## 2. What Invariants does it touch?

Operates entirely within the existing Invariants. It strengthens **Invariant 14 (Crypto-Agility Mandate)** and **Invariant 17 (Inference Sovereignty Floor)** by making the process of proposing and testing rotations structurally parallel and cheap. It relies heavily on **Invariant 3 (Safety Ledger Append-Only)** and **Invariant 4 (State Chain Append-Only)** to ensure that the high-velocity changes are permanently auditable.

## 3. How is it verified?

Through the `xion-verify pre-genesis` composite drill, which rolls up 13 independent verifiers:
- `cognition --disjoint-check`
- `registries`
- `rebuild`
- `replay-corpus`
- `vitals`
- `ledgers`
- `links`
- `shadow-relay`
- `cost-pressure`
- `substrates`
- `auto-research`
- `skill-bounty`
- `operator-dependencies`

## 4. How is it deprecated?

The velocity primitives are foundational to Xion's self-improvement loop. Deprecating any of them (e.g., disabling the Auto-Research Loop or the shadow canary) requires a Tier-2 governance vote and a corresponding update to this doctrine and the `xion-verify` suite.
