# 35 — Contributor Handbook

> *A good contributor should not need to memorize the constitution before the tools help them obey it.*

This handbook is the practical companion to [`34-CONTRIBUTION-PROTOCOL.md`](./34-CONTRIBUTION-PROTOCOL.md). It is for humans and the coding assistants they use.

## The Short Path

1. Install the verifier:

```bash
cd xion-verify
python -m pip install -e ".[dev]"
```

2. Ask the repo what level your change touches:

```bash
xion-verify which-level docs/34-CONTRIBUTION-PROTOCOL.md
```

3. If you use an assistant, give it the read-only facts bundle:

```bash
xion-verify mcp-export > xion-agent-facts.json
```

4. Draft the proposal with the paths you expect to touch:

```bash
xion new proposal add-ecoception --touches orchestrator/senses/ecoception.py
```

5. If you are binding a contributor wallet to your GitHub handle, write a row to `ledgers/CONTRIBUTOR_IDENTITY_BINDINGS.jsonl` and run:

```bash
xion-verify identity-bindings
```

6. Before opening a PR:

```bash
xion-verify --self-test
xion-verify links
xion-verify schemas
xion-verify provisioning-roles
```

## What Your Assistant May Do

Your assistant may:

- read `xion-agent-facts.json`
- classify paths with `which-level`
- generate a proposal draft
- suggest tests, verifier stubs, and rollback text
- explain why the level-discipline gate would reject a mixed PR

Your assistant may not:

- hold your signing key
- submit an on-chain message for you
- claim to be a governance actor
- bypass the Arbiter or Harm Analyzer
- combine unrelated levels into one PR because it is convenient

## Splitting Work

If `which-level` reports more than one mapped level, split the work. A Relay change and a Treasury change are two proposals even when one motivates the other.

Good:

- PR 1: `orchestrator/**` Relay implementation
- PR 2: `ao/core/main.lua` or treasury schema changes

Bad:

- one PR that changes Relay deployment, Spend handler semantics, and `docs/09-GOVERNANCE.md`

The split is not bureaucracy. It is the mechanism that lets each level use the right gate, canary, ledger, and rollback path.

## Identity Binding

A contributor identity binding proves that the GitHub handle opening a PR and the wallet participating in Xion governance are controlled by the same person or organization.

The canonical message is:

```text
xion-contributor-identity-binding-v1
github_handle=@handle
wallet_pubkey_ed25519_base64url=<base64url-raw-32-byte-ed25519-public-key>
signed_at_utc=<ISO-8601-UTC>
```

`xion-verify identity-bindings` verifies the signature. A verified row does not automatically grant authority. Authority still comes from the actor tables in [`schemas/roles.yaml`](./schemas/roles.yaml) and the governance procedure in [`09-GOVERNANCE.md`](./09-GOVERNANCE.md).

## Assistant Disclosure

Proposal frontmatter should disclose assistant use when material:

```yaml
authored_by:
  contributor: "@handle"
  contributor_wallet: "ed25519:<base64url>"
  assistant: "cursor/claude/codex/etc"
  assistant_dry_run: "which-level:ok identity-bindings:ok"
```

Disclosure does not make the assistant responsible. The contributor remains responsible.

The value of disclosure is measurement: Xion can later ask whether agent-assisted proposals are safer, noisier, more often refused, or more often accepted than unaided proposals.

## First-Version Limit

This handbook intentionally stops short of a live `xion-mcp` server and a full `xion-propose draft` package. The first version is a read-only facts export and verifier-backed scaffolding. That is enough for contributors to arrive at the gates cleanly without giving any assistant write authority.
