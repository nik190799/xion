# 23 — Hermes peer benchmark runner

> *If usefulness cannot be compared reproducibly, "useful" becomes marketing.*

**Property.** A **quarterly** benchmark suite runs against the pinned Hermes Agent ([`04-ARCHITECTURE.md`](./04-ARCHITECTURE.md)), publishes results to **`BENCHMARK_LEDGER`** on Arweave, and feeds **Service Usefulness** vital signs ([`22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md)).

**Invariants touched.** Supports 14 (operational discipline), 15 (benchmarks must not include revenue signals in prompts).

**Verification.** `xion-verify benchmark-last-quarter` — checks ledger continuity and digest match to published suite version.

**Deprecation.** Individual benchmarks rotate by governance; the **ledger + public runner** shape stays.

---

## Genesis Default suite (Layer 2)

Mix of public benchmarks and **Covenant-aligned** adversarial prompts sourced from `xion-audit` corpus (no user PII):

- MMLU subset (governance-chosen depth)
- HumanEval subset
- MT-Bench style multi-turn slice
- **In-house:** refusal correctness, crisis surfacing triggers, prompt-injection resistance pack

---

## Drift metrics

- **Quarter-over-quarter delta** on each score.
- **Gap vs published peer-agent leaderboard** (external table URL is Genesis Default; methodology records snapshot date).

---

## External feed governance

When NIST or the benchmark ecosystem moves on, governance ratifies a successor methodology and bumps the methodology hash — Layer 3 evolution.

---

## Cross-references

- [`08-AUTO-RESEARCH.md`](./08-AUTO-RESEARCH.md) — model change proposals
- [`22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md) — domain 6
