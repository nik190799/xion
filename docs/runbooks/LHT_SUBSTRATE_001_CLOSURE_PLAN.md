# LHT-SUBSTRATE-001 — Closure-Grade Drill Plan

**Status:** scoped 2026-05-15 (operator local; Central time)
**Owner:** Operator
**Target row:** `status: "passed"` in `ledgers/IMMORTALITY_DRILL_LEDGER.jsonl` with Chutes primary, against the criteria in [`docs/runbooks/IMMORTALITY_DRILL.md`](IMMORTALITY_DRILL.md) and [`docs/SUBSTRATE-RESILIENCE.md`](../SUBSTRATE-RESILIENCE.md) Part IV.
**Residual close date:** 2026-07-01 (per [`docs/STATE_OF_XION_PREFLIGHT.md`](../STATE_OF_XION_PREFLIGHT.md))

## Context

Session `8513740` (2026-05-15) committed the strategic call that **Chutes / Bittensor SN64 = primary GPU path, Akash = decentralized-option proof**. The 2026-05-14 third-party-VM drill row landed `failed (honest interim)` with five distinct breakages, only one of which was the Akash-side issue we had assumed. Closure-grade requires understanding all five — not just swapping primary/secondary labels.

This plan derives from a full read of the harness:

- [`scripts/immortality-drill-third-party.sh`](../../scripts/immortality-drill-third-party.sh) (drill runner; pass condition lines 170–171, hardcoded labels lines 180–181)
- [`xion-verify/src/xion_verify/commands/substrate_portability.py`](../../xion-verify/src/xion_verify/commands/substrate_portability.py) (line 18: already accepts Chutes as non-laptop)
- [`ledgers/IMMORTALITY_DRILL_LEDGER.jsonl`](../../ledgers/IMMORTALITY_DRILL_LEDGER.jsonl) (5 rows; 4 rehearsals passed, 1 third-party run failed)
- [`ledgers/RELAY_REGISTRY.json`](../../ledgers/RELAY_REGISTRY.json) (relays[0]=Akash, relays[1]=Chutes-d3 retired)
- [`docs/schemas/ledger-immortality-drill.yaml`](../schemas/ledger-immortality-drill.yaml) (schema)

## Five failure modes in the 2026-05-14 row (cited verbatim from the drill row at `run_id 09bccd3c-4649-41a0-bc83-8a8105440937`)

**Verified reproducible at HEAD (`8513740`) on 2026-05-15 via a venv-installed `xion-verify`:**

| # | Failure | Exit / Status | Root cause | Verified at HEAD? | Fix lane |
|---|---|---|---|---|---|
| 1 | `xion-verify links` | exit 1 | One broken link in `CHANGELOG.md:55` → `xion_ops/services/akash.py:586` (verifier doesn't strip `:line-number` suffix when resolving file targets) | **Yes** — `xion-verify links` exit 1, message: `target does not exist: ...akash.py:586` | **Either:** update CHANGELOG.md to drop the `:586` suffix, OR teach the verifier to strip trailing `:N` before resolving |
| 2 | `xion-verify schemas` | exit 1 | `source_sha256` mismatches: schemas point at docs whose content changed without rehashing | **Yes** — 4 mismatches at HEAD: `docs/runbooks/IMMORTALITY_DRILL.md`, `docs/STATE_OF_XION_PRE_GENESIS.md`, `docs/SPEND-AUTONOMY.md` (×2) | Rehash each affected doc and update `source_sha256` in the same commit — mechanical fix |
| 3 | `xion-verify inference-sovereignty` | exit 2 (`NOT_YET_SEALED`) | `XION_OPEN_WEIGHTS_GGUF_PATH` unset; gemma4-e4b-it-q4-k-m-gguf model blob not local-verified. Verifier marks this `NOT_YET_SEALED`, not `FAIL` — operator-side gap, not bug. | **Yes** — exit 2 at HEAD; structural integrity OK | **Design decision**: relax drill pass condition to accept exit 2, OR seal the gguf pin |
| 4 | `akash-primary-health` | `curl_exit 7` (Failed to connect) | Akash floor unreachable from GCP us-south1; KW-FLOOR-DEPLOY-001 | n/a (network-dependent) | **Substrate swap** — Chutes becomes the probe target |
| 5 | `chutes-secondary-health` | `status_code 401` (bearer not set) | `XION_SECONDARY_HEALTH_BEARER` env var missing on VM (drill script line 105–106 only adds bearer when var is set) | n/a (VM-state-dependent) | **Pre-flight env fix** on the third-party VM |

The substrate-portability verifier (`verifier_results[4]`) **passed** at exit 0 on 2026-05-14 and still passes at HEAD. So the substrate-portability *story* held; the drill row failed for unrelated reasons. Closure-grade is not blocked on a substrate verifier rewrite.

### Concrete Phase 1 fixes (cited from HEAD reproduction)

**Fix 1.1 — `links` (CHANGELOG.md:55):** The link `[xion_ops/services/akash.py:586-617](xion_ops/services/akash.py:586)` parses with `:586` as part of the path. Quickest fix: change the link target to `xion_ops/services/akash.py` (drop the `:586`) and keep the line-range in the label only. Bigger fix: extend `xion-verify/src/xion_verify/commands/links.py:149` (`path_part = stripped.split("#", 1)[0].split("?", 1)[0]`) to also strip `:NNN` suffix before path resolution — but that risks false positives on Windows drive paths.

**Fix 1.2 — `schemas` (4 sha256 mismatches):** Rehash the four underlying docs and update `source_sha256` in:
- `docs/schemas/ledger-immortality-drill.yaml` (source: `docs/runbooks/IMMORTALITY_DRILL.md`)
- `docs/schemas/ledger-pre-genesis-drill.yaml` (source: `docs/STATE_OF_XION_PRE_GENESIS.md`)
- `docs/schemas/ledger-spend-authority.yaml` (source: `docs/SPEND-AUTONOMY.md`)
- `docs/schemas/spend-posture.yaml` (source: `docs/SPEND-AUTONOMY.md`)

Use `sha256sum <doc> | awk '{print $1}'` (or the equivalent Python one-liner) for each.

**Fix 1.3 — `inference-sovereignty` exit 2 treatment:** Recommended option (3a from earlier section): edit `scripts/immortality-drill-third-party.sh` line 170 from `all_verifiers_ok = all(int(row["exit_code"]) == 0 for row in results)` to a per-verifier policy that accepts exit 2 from `inference-sovereignty` specifically (allowlist by name). Reason: `NOT_YET_SEALED` is a doctrinal state surfaced by the verifier as a non-failure (its own message labels it as "operator-side gaps the verifier surfaces but does not treat as failures").

## The architectural question this plan does NOT decide

Per [`docs/SUBSTRATE-RESILIENCE.md`](../SUBSTRATE-RESILIENCE.md) Part IV line 133, future Invariant 20 promotion requires **at least one warm secondary substrate must exist for each role**. The drill harness probes two endpoints (`relays[0]` and `relays[1]`) and both must return 200–299 for the row to pass.

If Chutes becomes `relays[0]` (primary), what is `relays[1]` (secondary)?

| Option | Cost | Honest? | Decision needed |
|---|---|---|---|
| (a) Keep Akash CPU-only as warm secondary | Low (CPU SDL exists at [`infra/akash/relay-deployment-cpu-only.yaml`](../../infra/akash/relay-deployment-cpu-only.yaml)) | Yes — Akash is genuinely a different substrate | But: same provider economics caused this session's manifest-refusal / ingress problems on CPU and GPU alike |
| (b) A second independent Chutes endpoint | Trivial | **No** — violates Part IV.2 "diversity" intent; both substrates on Bittensor SN64 | Reject without further analysis |
| (c) Build an Aleph or alternate-substrate deployment | High (new substrate evaluation, funding, deploy) | Yes | Outside this sprint's scope |
| (d) Re-frame the row as "Chutes-primary attestation" not "closure-grade LHT-SUBSTRATE-001" — explicitly mark `residual_closed: false` and accept that closure is multi-quarter | Zero | Yes — matches what the doctrine actually requires | Recommended for this sprint |

**This plan adopts option (d) for the next drill run** and flags option (a) as the natural follow-up once the Akash CPU pathway is verified separately. Option (c) is parked for the post-2026-07-01 horizon.

## Execution sequence

### Phase 1 — Verifier-fix pre-flight (1 session, no chain spend)

Required before any third-party-VM run, since `links` and `schemas` failing is a blanket veto on `all_verifiers_ok`.

1. **Reproduce the failures locally.**
   ```
   xion-verify links 2>&1 | tee /tmp/links.log
   xion-verify schemas 2>&1 | tee /tmp/schemas.log
   ```
   Read the actual failure messages. Most likely: schema-drift since the 2026-05-13 doc sweep, or new links added without anchors.

2. **Decide per-failure:** is it a bug in the verifier (fix the code), or a real schema/link drift in the repo (fix the doc)? Don't paper over a real verifier with `|| true`.

3. **Decide `inference-sovereignty` exit 2 treatment.** Two options:
   - **3a.** Accept `NOT_YET_SEALED` (exit 2) as a passing condition by changing the drill script's pass check at [`scripts/immortality-drill-third-party.sh`](../../scripts/immortality-drill-third-party.sh) line 170 from `int(row["exit_code"]) == 0` to `int(row["exit_code"]) in (0, 2)`. Document the rationale inline.
   - **3b.** Seal inference-sovereignty (much larger lift; out of this plan).

   Recommended: **3a**. Pin the change with a comment citing this plan + the doctrinal note in [`docs/runbooks/IMMORTALITY_DRILL.md`](IMMORTALITY_DRILL.md).

4. **Verify locally:** `xion-verify --self-test`, all verifiers exit 0 (or 2 for sovereignty). Append a per-fix evidence note under `genesis/DEPLOYMENT_RECORDS/verifier-fixes-2026-05-XX.json`.

**Acceptance:** all five `xion-verify` subcommands (`discovery`, `gateway-conformance`, `links`, `schemas`, `substrate-portability`) exit 0; `inference-sovereignty` exits 0 or 2 (per Phase 1.3 decision); `--self-test` exits 0.

### Phase 2 — Fresh Chutes primary deployment (1 session, requires Chutes credit)

Current `relays[1]` entry in [`ledgers/RELAY_REGISTRY.json`](../../ledgers/RELAY_REGISTRY.json) points to `nikhilkadalge-xion-relay-pre-genesis-d3.chutes.ai` (image tag `pre-genesis-d3-10`, last_seen 2026-04-25). That's the retired chute (KW-RELAY-CHUTES-D3-001).

1. **Confirm Chutes credit.** Per [`genesis/FUNDING_TARGETS.json`](../../genesis/FUNDING_TARGETS.json) lines 74–81: SS58 `5DP1emNNEEnttzLCNNp1mUt9RNe2SzH5T1ebdsWomtEqxybq`, target $5.00. Run a balance check (`python -m xion_ops chutes balance` or `chutes status`) before deploying.

2. **Deploy fresh chute via [`scripts/demo-minimal-chutes-deploy.sh`](../../scripts/demo-minimal-chutes-deploy.sh).** Capture the new chute_id, image_id, endpoint, and bearer-token-protected `/health` evidence. Verify the new endpoint returns HTTP 200 with `Authorization: Bearer $XION_CHUTES_API_KEY` and a non-empty body.

3. **Record deployment evidence** at `genesis/DEPLOYMENT_RECORDS/relay-chutes-genesis-2026-05-XX.json`, matching the shape of [`genesis/DEPLOYMENT_RECORDS/relay-akash-smoke-2026-05-15.json`](../../genesis/DEPLOYMENT_RECORDS/relay-akash-smoke-2026-05-15.json).

**Acceptance:** New chute returns 200 on `/health` with bearer; deployment record committed; KW-RELAY-CHUTES-D3-001 status flips from `open` to `mitigated`.

### Phase 3 — Primary-swap configuration (½ session)

Two coordinated edits, plus a verifier change:

1. **[`ledgers/RELAY_REGISTRY.json`](../../ledgers/RELAY_REGISTRY.json):** Move the new Chutes entry to `relays[0]`, the Akash entry to `relays[1]`. Update `payload_sha256`. Add the Akash CPU-only entry as `relays[1]` if the operator picks option (a) from the architectural question above; otherwise leave the existing Akash entry there to be probed (it will fail health-check honestly).

2. **[`scripts/immortality-drill-third-party.sh`](../../scripts/immortality-drill-third-party.sh) lines 180–181:** Change to `"primary_substrate": "chutes-sn64-primary"`, `"secondary_substrate": "akash-cpu-secondary"` (or whatever option (a)/(d) decides).

3. **No verifier change required.** `substrate_portability.py` line 18 already accepts `("akash", "aleph", "chutes")` regardless of primary/secondary role. Verifier change in the earlier plan draft was unnecessary.

**Acceptance:** `scripts/substrate-portability-dry-run.sh` writes a row to `SUBSTRATE_DRYRUN_LEDGER.jsonl` with `secondary_substrate_id` matching the new layout; `xion-verify substrate-portability` exits 0.

### Phase 4 — Third-party-VM drill (1 session, requires cloud VM)

1. **Spin a non-operator VM.** GCP us-south1 e2-small Debian 12 (matches the 2026-05-14 fingerprint pool), or equivalent. Cloud-init template at [`scripts/cloud-vm-immortality-drill.cloud-init.yaml`](../../scripts/cloud-vm-immortality-drill.cloud-init.yaml). Cold start ~3–5 min.

2. **Set required env vars on VM:**
   - `XION_SECONDARY_HEALTH_BEARER=<chutes API key>` — fixes the 2026-05-14 401.
   - `XION_REPO_URL=https://github.com/nik190799/xion.git`, `XION_REPO_REF=main` (defaults are fine).

3. **Run [`scripts/immortality-drill-third-party.sh`](../../scripts/immortality-drill-third-party.sh).** Capture stdout. The script appends one row to `IMMORTALITY_DRILL_LEDGER.jsonl`.

4. **Destroy the VM.** Nothing on it is worth preserving (per [`docs/runbooks/IMMORTALITY_DRILL.md`](IMMORTALITY_DRILL.md) line 101).

5. **Commit and push the new ledger row.**

**Acceptance per row in the ledger:**
- `event: "immortality_drill_third_party_v1"`
- `primary_substrate: "chutes-sn64-primary"`
- `status: "passed"`
- All `verifier_results[].exit_code` in (0, 2) per Phase 1.3
- All `relay_health_results[].curl_exit == 0` and `status_code` in 200–299
- `third_party_machine_fingerprint` differs from operator's daily machine
- Valid hash chain: `prev_hash` matches prior row's `row_hash`
- `residual_closed: false` (closure-grade is later)

### Phase 5 — Iterate or escalate (conditional, 1–2 sessions)

If Phase 4 lands `failed`: diagnose with the same five-failure-modes table above. Do not blind-retry. Common second-attempt root causes:
- Phase 1 fix incomplete — a verifier still flakes
- Bearer env not propagated to the script's curl call
- Chute endpoint genuinely down (revisit Phase 2)
- Akash secondary 401/connection-refused (the operator decides whether to swap secondary)

### Beyond Phase 5 — Path to actual LHT-SUBSTRATE-001 closure

Per [`docs/SUBSTRATE-RESILIENCE.md`](../SUBSTRATE-RESILIENCE.md) Part IV, closure-grade requires:

1. **Three successful drills across different substrate pairs** (line 132). One Chutes-primary pass is one of three. Schedule the remaining two over 4–8 weeks.
2. **A working warm secondary for each role** (line 133). This sprint's option (d) leaves the secondary genuinely unhealthy; full closure requires fixing that — either via KW-FLOOR-DEPLOY-001 closure (revisits Akash, parked), or an alternate substrate (Aleph, etc.).
3. **`xion-verify substrate-portability` live, not NOT_YET_SEALED** (line 134). Already passing at exit 0 today; phrase as "live."
4. **Cost-Pressure ladder substrate-cutover step documented** (line 135). Out of this plan.

`residual_closed: true` is signaled only when all four pre-conditions are met. This drill plan moves item 1 forward by 1 of 3 and unblocks the next two attempts; it does not fully close LHT-SUBSTRATE-001 on its own.

## Critical files

**Phase 1 (verifier fixes):**
- [`xion-verify/src/xion_verify/commands/links.py`](../../xion-verify/src/xion_verify/commands/links.py) (diagnose)
- [`xion-verify/src/xion_verify/commands/schemas.py`](../../xion-verify/src/xion_verify/commands/schemas.py) (diagnose)
- [`scripts/immortality-drill-third-party.sh`](../../scripts/immortality-drill-third-party.sh) line 170 (`inference-sovereignty` exit code relaxation)

**Phase 2 (Chutes redeploy):**
- [`scripts/demo-minimal-chutes-deploy.sh`](../../scripts/demo-minimal-chutes-deploy.sh)
- New: `genesis/DEPLOYMENT_RECORDS/relay-chutes-genesis-2026-05-XX.json`

**Phase 3 (primary swap):**
- [`ledgers/RELAY_REGISTRY.json`](../../ledgers/RELAY_REGISTRY.json)
- [`scripts/immortality-drill-third-party.sh`](../../scripts/immortality-drill-third-party.sh) lines 180–181

**Phase 4 (drill run):**
- [`scripts/cloud-vm-immortality-drill.cloud-init.yaml`](../../scripts/cloud-vm-immortality-drill.cloud-init.yaml)
- [`scripts/immortality-drill-third-party.sh`](../../scripts/immortality-drill-third-party.sh) (no edit, run)
- Append row to [`ledgers/IMMORTALITY_DRILL_LEDGER.jsonl`](../../ledgers/IMMORTALITY_DRILL_LEDGER.jsonl)

## Functions / utilities to reuse

- `ChutesService` and `AkashService` in [`xion_ops/services/`](../../xion_ops/services/) — already split env vars correctly per commit `6a41c10`.
- `evaluate_substrate_portability()` in [`xion-verify/src/xion_verify/commands/substrate_portability.py`](../../xion-verify/src/xion_verify/commands/substrate_portability.py) (lines 33–84) — verifier accepts Chutes/Akash/Aleph; no modification needed.
- Existing closure-record shape in [`genesis/DEPLOYMENT_RECORDS/relay-akash-smoke-2026-05-15.json`](../../genesis/DEPLOYMENT_RECORDS/relay-akash-smoke-2026-05-15.json) — Phase 2 record matches this shape.
- Existing rehearsal rows in [`ledgers/IMMORTALITY_DRILL_LEDGER.jsonl`](../../ledgers/IMMORTALITY_DRILL_LEDGER.jsonl) lines 1–4 — schema reference; do not edit.

## Verification

- **Phase 1 done when:** `xion-verify discovery gateway-conformance links schemas substrate-portability --self-test` all exit 0; `inference-sovereignty` exits 0 or 2 per design choice.
- **Phase 2 done when:** new Chutes endpoint returns 200 with bearer; deployment record committed; ledger row in RELAY_REGISTRY updated.
- **Phase 3 done when:** `scripts/substrate-portability-dry-run.sh` produces a clean row with new substrate layout; `xion-verify substrate-portability` exits 0.
- **Phase 4 done when:** new `IMMORTALITY_DRILL_LEDGER.jsonl` row has `status: "passed"`, valid hash chain, Chutes-primary labels, third-party fingerprint differs from operator's.
- **Full closure (LHT-SUBSTRATE-001):** *not* achieved by this plan alone — requires items 1–4 in "Beyond Phase 5" section above. Mid-2026 horizon.

## Out of scope (explicit)

- **KW-FLOOR-DEPLOY-001 closure** — Akash GPU live floor. Parked per [`genesis/DEPLOYMENT_RECORDS/relay-akash-smoke-2026-05-15.json`](../../genesis/DEPLOYMENT_RECORDS/relay-akash-smoke-2026-05-15.json) "Akash = evidence-of-option, not primary."
- **Sealing `inference-sovereignty`** — large doctrinal lift; out.
- **New substrate evaluation (Aleph, io.net, Render Dispersed.com)** — post-2026-07-01.
- **`residual_closed: true` on this row** — not achievable until "Beyond Phase 5" items 1–4 land.

## Decision points during execution

- **After Phase 1.3:** confirm operator wants `inference-sovereignty` exit 2 accepted as "pass," or wants sealing prioritized.
- **After Phase 2:** if Chutes credit is insufficient (target $5.00, deposit needed first), pause and either fund or defer Phase 2.
- **At Phase 3 architectural choice:** operator picks option (a), (c), or (d) for the warm-secondary slot. This plan defaults to (d) — re-frame as attestation-grade and accept `residual_closed: false`.
- **After Phase 4 outcome:** if `passed`, this plan succeeds for the sprint; schedule the remaining two substrate-pair drills. If `failed`, diagnose specifically before retry.
