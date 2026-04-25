# docs/schemas/ — machine-readable mirrors of hashed doctrine

> *Property promised. For every field a human doctrine file canonicalizes, a
> machine-readable YAML here mirrors it exactly. For every field a human
> doctrine file has not yet canonicalized, no schema here invents one. The set
> of fields a third party can mechanically check against Xion is the set of
> fields Xion has already promised in writing — nothing more, nothing less.*

## What lives here

| File | Mirrors | Status |
|------|---------|--------|
| `levels.yaml` | `docs/14-UPGRADE-PATHS.md` — the 13 Upgrade-Paths levels, 10-field template, 3 Constitutional Floors | canonical |
| `ledger-proposal.yaml` | `docs/08-AUTO-RESEARCH.md` §101 — `PROPOSAL_LEDGER` row schema | canonical |
| `ledger-specialist.yaml` | `docs/24-COGNITION.md` §14 — `SPECIALIST_LEDGER` row schema | canonical |
| `ledger-amendment.yaml` | `docs/09-GOVERNANCE.md` — `AMENDMENT_LEDGER` row schema | canonical |
| `ledger-safety.yaml` | `docs/03-COVENANT.md` + `genesis/COVENANT.md` Principle 14 — `SAFETY_LEDGER` | **underspecified stub**; see inside |
| `hermes-tool-allowlist.yaml` | `docs/HERMES_PIN_PROTOCOL.md` — default-deny Hermes tool allowlist contract | canonical |
| `agent-soul.yaml` | `docs/HERMES_PIN_PROTOCOL.md` — per-Agent-Soul field contract | canonical |
| `agent-cast-ledger.yaml` | `docs/HERMES_PIN_PROTOCOL.md` — `AGENT_CAST_LEDGER` row schema | canonical |

## The four Properties questions

### 1. What property does this folder promise?

Every schema in this folder is a *loss-less* machine-readable serialization of a
specific section of hashed doctrine. If the schema disagrees with the doctrine,
the schema is wrong by definition — because the doctrine is what was ratified
and the schema is a convenience.

The converse holds: if a doctrine section is silent on a field, no schema here
fabricates that field. Schemas that would require invention are shipped as
**stubs** with `status: underspecified`, a `defer_to:` phase pointer, and zero
substantive fields — not as "best-effort plausible fillers."

### 2. What Invariants does it touch?

- **Invariant 12 (Documentation is Product).** Strengthens. Every YAML here is
  verified against its doctrine source on every CI run; no drift survives a PR.
- **Invariant 14 (Crypto-Agility Mandate).** Touches. Every schema records the
  SHA-256 of the exact bytes of its doctrine source in `source_sha256`. The
  algorithm family (SHA-256) is named in one place (`xion_verify.hashing`) and
  future migrations add sibling algorithms; this folder inherits that migration
  path without structural change.
- **Invariants 1-11, 13, 15, 16.** Leaves unchanged.

### 3. How is it verified?

```sh
xion-verify schemas
```

The subcommand, for every file in `docs/schemas/*.yaml`:

1. Parses it as YAML (must be valid).
2. Requires top-level meta fields: `schema_version`, `source_doctrine`,
   `source_sha256`, `status`.
3. Resolves `source_doctrine` as a repo-relative path, computes its current
   SHA-256, and **FAILs** if it does not match `source_sha256` (strict — see
   CHANGELOG for the rationale vs. advisory).
4. Accepts `status` in `{canonical, underspecified}`. `underspecified` schemas
   additionally require a `defer_to` pointer naming the roadmap phase that
   will promote them.

The subcommand participates in `xion-verify all` and runs in
`.github/workflows/verify.yml` on every PR.

### 4. How is it deprecated?

When a doctrine source file changes, the corresponding schema file's
`source_sha256` is updated **in the same commit** (CI enforces this). When a
schema file is retired — e.g., the ledger it mirrors is itself deprecated in
doctrine — the schema file is deleted **in the same commit** that removes its
doctrine source, and the removal appears in `CHANGELOG.md`.

When an `underspecified` stub becomes canonical (doctrine catches up), its
`status` flips from `underspecified` to `canonical`, `defer_to` is removed, and
the new fields are added — all in one commit, with a CHANGELOG entry and (if
applicable) a KW-DOCS-003 downgrade.

Stubs that linger past their `defer_to` phase trigger a red-alarm KW promotion
rather than a silent deadline extension — identical to the discipline enforced
on `xion-verify/ALLOWED_FORWARD_REFS.txt`.

## For third-party auditors

You do not have to trust this folder. You only have to run the verifier:

```sh
cd xion-verify
python -m pip install -e .
xion-verify --self-test && xion-verify schemas
```

If it exits `0`, every YAML here byte-verified against the doctrine it claims
to mirror, as of the commit you checked out.
