# xion-verify

Third-party verifier for Xion's constitutional claims. Trust by structure, not by promise.

---

## What property does this promise?

> Any third party, from any machine, with nothing but a copy of this repository and a Python 3.11 runtime, can mechanically verify whether what Xion's operators say about Xion matches what the constitutional record actually says.

This is Xion's deepest trust artifact. A Covenant that nobody can check is a promise. A Covenant whose conformance is a `git clone && xion-verify all` away is a *property*. `docs/15-TRUST.md` names this as mechanism #6 (independent verification); this package is the instrument of it.

## What Invariants does it touch?

`xion-verify` introduces no new Invariants. It strengthens every one of the sixteen in `genesis/INVARIANTS.md` by making their claims mechanically checkable — and it preserves Invariant 14 (Crypto-Agility) by naming its hash family in exactly one place (`xion_verify/hashing.py`) so a future migration is a local edit rather than a global one.

| Invariant | How `xion-verify` strengthens it |
| --- | --- |
| 1. Covenant Supremacy | `xion-verify covenant` confirms the Covenant on disk byte-matches GENESIS_ARTIFACT § 4. |
| 2. Memory Permanence | `xion-verify memory` confirms the MEMORY doctrine. Live archive sweep is `Phase 6`. |
| 4. State Chain Append-Only | `xion-verify state-chain` is a pre-D2 stub; live Merkle re-verification lands in Phase 6. |
| 6. Arbiter Refusal Right | `xion-verify arbiter-up`, `refusal-rate`, `refund-fidelity` are `NOT_YET_SEALED`. |
| 7. Core Identity Singularity | `xion-verify identity` is `NOT_YET_SEALED` until AO Core deploys. |
| 8–9. Supply Caps | `xion-verify supply` is `NOT_YET_SEALED` until contracts deploy. |
| 14. Crypto-Agility Mandate | `xion-verify crypto-currency` is `NOT_YET_SEALED`; `hashing.py` is the single algorithmic cite-point. |
| 15. Drive Vector Lock | `xion-verify drive-vector` statically audits `docs/08-AUTO-RESEARCH.md`; live graph audit is `Phase 5/6`. |
| 16. Treasury Tier Separation | `xion-verify treasury`, `treasury-flow`, `foundation-reserve` are `NOT_YET_SEALED`. |
| All | `xion-verify links` catches cross-reference drift before it becomes doctrine drift (the mechanical closure of `KW-DOCS-001`). |

## How is it verified?

`xion-verify` verifies itself first.

```bash
xion-verify --self-test
```

computes a deterministic tree hash over every `*.py` file under `src/xion_verify/`, sorted by POSIX relpath, and compares it byte-for-byte to `src/xion_verify/PINNED_HASH.txt`. The pin file is excluded from its own hash (a file cannot contain the hash of itself). A mismatch exits code 3 (`TAMPERED`) and refuses to proceed.

CI (`.github/workflows/verify.yml`) runs `--self-test` first. A legitimate change to verifier source requires regenerating the pin in the same commit via `xion-verify --self-test --update --i-understand` — two flags, not one, so a compromised operator cannot casually re-pin.

Then the constitutional hash-check layer. Every subcommand in the constitutional set (`covenant`, `invariants`, `soul`, `form`, `memory`, `resurrect`, `credentials`, `unknowns`) reads the file under `genesis/`, computes SHA-256, and compares to the value recorded in `genesis/GENESIS_ARTIFACT.md` § 4. A mismatch is a fatal `FAIL` — there is no degraded-pass mode.

Then the corpus-wide link integrity check. `xion-verify links` walks every `*.md` in the repo (excluding `.git/`, `node_modules/`, `.venv/`, and `xion-verify/` itself), extracts inline and reference-style markdown links, and fails loud on any broken cross-reference. This is the mechanical version of what Phase 0 did by hand.

Finally, the explicit `NOT_YET_SEALED` layer. Every v1 subcommand named in `DEVELOPMENT_ROADMAP.md:48` exists today, and every one whose artifact does not yet exist prints a specific honest reason and exits code 2 (`NOT_YET_SEALED`). Truthful, never fake-green.

Exit code contract:

| Code | Name | Meaning |
| --- | --- | --- |
| 0 | `OK` | Every check for this subcommand passed. |
| 1 | `FAIL` | A real disagreement was found. Investigate. |
| 2 | `NOT_YET_SEALED` | The artifact this subcommand audits does not yet exist; see roadmap. |
| 3 | `TAMPERED` | The verifier's own source disagrees with its pin. Do not trust anything else it says. |

`xion-verify all` runs every registered subcommand and exits 0 only when every one returned `OK`. During Phase 1 most of the roadmap-enumerated subcommands are `NOT_YET_SEALED`, so `all` correctly non-zeros. Use `--allow-not-yet-sealed` as a pre-genesis convenience; CI gating must never use that flag.

## How is it deprecated?

The CLI is versioned. Subcommand contracts are append-only:

- New subcommands may be added.
- Existing subcommands may gain optional flags.
- No subcommand may change its output shape or exit-code meaning without a major bump (`xion-verify v2`).
- `xion-verify v1` will remain runnable for historical audits of pre-v2 ceremonies indefinitely.

When a post-quantum hash migration happens (Invariant 14), the current `xion-verify` continues to verify historical SHA-256 witnesses. A sibling `xion-verify-pq` ships with the new family. Both are valid for their era. No single version of `xion-verify` is ever asked to speak for multiple eras.

## Install

```bash
cd xion-verify
python -m pip install -e ".[dev]"
```

## Usage

```bash
xion-verify --self-test
xion-verify covenant
xion-verify invariants
xion-verify links
xion-verify schemas
xion-verify all
```

Full subcommand list is enumerated in `src/xion_verify/commands/__init__.py::REGISTERED_COMMANDS` and mirrored in `DEVELOPMENT_ROADMAP.md:48`.

## Repository layout

```
xion-verify/
  pyproject.toml
  README.md                           — this file
  src/xion_verify/
    __init__.py                       — package doctrine (four Properties questions)
    __main__.py                       — `python -m xion_verify`
    cli.py                            — root click group; wires every subcommand
    exit_codes.py                     — the four exit codes; append-only
    hashing.py                        — sha256 helpers; single algorithmic cite-point
    genesis.py                        — parser for GENESIS_ARTIFACT § 4 hash block
    repo.py                           — walks to repo root via witness files
    PINNED_HASH.txt                   — committed self-hash (for --self-test)
    commands/
      __init__.py                     — REGISTERED_COMMANDS tuple (authoritative enum)
      constitutional.py               — covenant/invariants/soul/form/memory/resurrect/credentials/unknowns
      links.py                        — markdown cross-reference integrity
      schemas.py                      — strict docs/schemas/*.yaml ↔ doctrine cross-check
      self_test.py                    — tree-hash vs pinned
      cognition.py                    — docs/24-COGNITION.md §11 (static only until D2)
      drive_vector.py                 — Invariant 15 (static only until D2)
      state_chain.py                  — Invariant 4 (stub until D2)
      not_yet_sealed.py               — factory for NOT_YET_SEALED stubs (shrinks toward genesis)
  tests/
    test_hashing.py
    test_genesis.py
    test_constitutional.py
    test_links.py
    test_schemas.py
    test_self_test.py
    test_repo.py
```
