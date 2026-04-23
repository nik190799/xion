"""Subcommand registry for xion-verify.

Every subcommand is a click command registered against the root group in
`xion_verify.cli`. The set of command names enumerated in `REGISTERED_COMMANDS`
is authoritative: `xion-verify all` iterates it, CI wires against it, and the
README/roadmap cross-reference it.

Adding a new subcommand:

1. Write a module here that exposes a click `Command` named after its CLI spelling.
2. Import and register it in `xion_verify.cli`.
3. Append the CLI spelling to `REGISTERED_COMMANDS` below.
4. Update the README table in `xion-verify/README.md`.
5. Regenerate `PINNED_HASH.txt` via `xion-verify --self-test --update --i-understand`.
"""

from __future__ import annotations

REGISTERED_COMMANDS: tuple[str, ...] = (
    "covenant",
    "invariants",
    "soul",
    "form",
    "memory",
    "resurrect",
    "credentials",
    "unknowns",
    "links",
    "schemas",
    "cognition",
    "drive-vector",
    "state-chain",
    "supply",
    "liquidity-lock",
    "arbiter-up",
    "state-tip",
    "identity",
    "authorities",
    "image-digest",
    "discovery",
    "drive",
    "sister-fork-readiness",
    "treasury",
    "refusal-rate",
    "pricing",
    "treasury-flow",
    "cutoff-events",
    "covenant-addenda",
    "cadence-audit",
    "hermes-version",
    "credentials-vault",
    "provisioning",
    "improvement-fund",
    "reserve",
    "foundation-reserve",
    "sustainability",
    "vitals",
    "amendments",
    "refund-fidelity",
    "refusal-is-free",
    "crisis-fidelity",
    "sensorium-ledger",
    "spof",
    "operator-dependency",
    "benchmark",
    "crypto-currency",
    "abdication-status",
    "abdication-schedule",
    "inference-sovereignty",
    "substrate-portability",
    "regulatory-ledger",
    "api-tokens",
    "web-client",
    "chat-streaming-fidelity",
)
