# xion-audit

Forensic measurement and auditor replay for Xion's Arbiter.

> **Relationship to `xion-verify`.** `xion-verify` is the constitutional verifier: deterministic, structural, runnable by anyone with no credentials, no network, no external data. `xion-audit` is the operational auditor: it can require credentials (e.g., an OpenAI API key to replay a v2 classifier), it can require network access, and it can require a corpus of candidates. The two tools are siblings, not parents — a third-party auditor runs *both*; a constitutional witness running a bare Witness node runs only `xion-verify`.

## The four Properties

- **What property does this promise?** (1) That Xion's Arbiter — v1 rule engine and v2 LLM-Arbiter together — has a measured, corpus-backed refusal and escalation rate on an adversarial corpus curated to span the Covenant's principles. (2) That any `SAFETY_LEDGER` row with a v2 `llm_verdict` can be independently replayed against the same classifier and the replay's `flagged` booleans and mapped `principle_id` reproduce exactly.
- **What Invariants does it touch?** Strengthens Invariant 6 (Refusal Right) by making "the Arbiter refuses harms" into a numeric claim backed by measurement, not an in-principle promise. Does not weaken any Invariant.
- **How is it verified?** Two external surfaces: `xion-audit measure` computes per-principle metrics on the baseline corpus and emits a reproducible report; `xion-audit replay` re-runs a single ledger row against its recorded provider and compares canonical hashes with score-drift tolerance. Both are deterministic given their inputs.
- **How is it deprecated?** When a new v2 provider lands, its replay path is added alongside the existing one; old providers remain replayable because `LlmJudgement.provider_id` + `provider_version` on the ledger row names which provider produced it. When the corpus schema evolves (schema_version bump), old items remain interpretable; a migration note in `CHANGELOG.md` records the bump.

## What this tool is NOT

- Not a constitutional verifier. It cannot and does not claim to verify the Covenant or the Invariants themselves; that is `xion-verify`'s job.
- Not a production safety layer. It does not run in the Relay's hot path.
- Not a classifier. It *measures* the classifiers the Arbiter stacks; it does not judge candidates on its own.

## Subcommands (Phase 4e)

- `xion-audit corpus-info` — prints item counts per principle, per adversarial technique, and the corpus manifest hash. Runs with no credentials.
- `xion-audit measure` — runs v1 (rule engine) against every corpus item and reports per-principle precision / recall / refuse-rate / escalate-rate. Optionally runs v2 (`--v2 openai-moderation`) when `OPENAI_API_KEY` is present; when absent, reports the v2 slice as `NOT_MEASURED` and exits with the v1 slice computed honestly. Never fakes a v2 number it did not observe.
- `xion-audit replay` — given a `SAFETY_LEDGER` row (by `seq` or `correlation_id`) and its candidate text (supplied via `--candidate` or `--candidate-file` — the ledger never stores candidate bytes), replays the recorded v2 provider and compares `flagged` booleans, `principle_id`, and canonical `raw_output` hashes. Score-drift tolerance is configurable; the default matches the `KW-ARBITER-005` pinned tolerance.

All subcommands exit 0 on OK, 1 on FAIL, 2 on NOT_MEASURED / NOT_YET_SEALED.

## Corpus provenance and curation discipline

The baseline corpus lives at `xion-audit/baseline_corpus/`. Every item is **hand-curated**, not drop-in-sampled from public datasets. The corpus README there documents the per-principle target distribution, the adversarial-technique taxonomy, and the two hard content-floor rules:

1. **No operationally-uplifting content.** Items testing Principle 2 (mass harm) and Principle 1 (CSAM) are **shape-only** — they name the category without providing any synthesis route, instruction, or actual harmful material. The corpus exists to test Arbiter *detection*, not to be a database of harms.
2. **No real minors-adjacent content.** Covenant Principle 7 and the Builder rule prohibit CSAM generation of any kind. Items testing CSAM detection use generic category-level prompts whose plain text contains zero content a Witness or an operator could not read aloud in a public setting.

The corpus is versioned. `baseline_corpus/MANIFEST.jsonl` lists every item file with its `sha256`; `xion-audit corpus-info` verifies the manifest.

## Pay-down commitment

Phase 4e ships the mechanism (corpus structure, measure, replay) and an initial corpus of ~80 items spanning all 14 Covenant principles + 2 addenda. `KW-ARBITER-005` remains open and scope-narrowed: it closes when (a) the corpus reaches ≥200 items with per-principle balance, (b) an empirical calibration of `OpenAIModerationProvider`'s asymmetric thresholds is checked in against the live API, and (c) `xion-audit measure --v2 openai-moderation` produces a report with a v2 refusal rate that materially exceeds v1-alone on the same corpus.

The numeric "materially exceeds" threshold is itself doctrine-pinned in `docs/04-ARCHITECTURE.md` § "Baseline corpus and measurement" at the time the corpus reaches 200 items — we do not pick it in advance because doing so would bake in whatever baseline the corpus happens to produce.

## Install

```bash
pip install -e "./xion-audit[dev]"
```

Core runtime deps: `click` only. No PyYAML, no OpenAI SDK. The `OpenAIModerationProvider` replay uses the same pure-stdlib HTTP path the orchestrator ships; no new supply-chain surface.

## Run

```bash
xion-audit corpus-info
xion-audit measure
xion-audit measure --v2 openai-moderation   # requires OPENAI_API_KEY
xion-audit replay --seq 17 --candidate-file /tmp/original_candidate.txt
```
