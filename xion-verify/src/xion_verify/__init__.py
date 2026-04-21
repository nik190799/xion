"""xion-verify — third-party verifier for Xion's constitutional claims.

Property promised
    Any third party can, from any machine, verify that what the operator says
    is true about Xion matches what the constitutional record actually says.

Invariants touched
    Strengthens trust in every Invariant (1 through 16) by making their claims
    mechanically checkable. Introduces no new Invariant; embodies the trust
    doctrine in `docs/15-TRUST.md` that trust is structural, not promissory.

Verification
    This package verifies itself: `xion-verify --self-test` tree-hashes the
    installed source and compares to `xion_verify/PINNED_HASH.txt`. Tampered
    local copies fail loud before any other check runs.

Deprecation
    The CLI is versioned `xion-verify-vN`. Subcommand contracts are append-only:
    new subcommands may be added, and existing subcommands may gain optional
    flags, but no subcommand may change its output shape without a major bump.
    Old versions remain runnable for historical audits.
"""

__version__ = "0.1.0"
