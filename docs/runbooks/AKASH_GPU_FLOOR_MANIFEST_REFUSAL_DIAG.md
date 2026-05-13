# Akash GPU floor — manifest/ingress refusal diagnostic

**KW reference:** [KW-FLOOR-DEPLOY-001](../../KNOWN_WEAKNESSES.md#kw-floor-deploy-001---open-weights-floor-akash-lease-is-not-currently-reachable). Currently `mitigated-residual`, dated residue **2026-05-10 → 2026-07-09**.

**Purpose:** Synthesize four reproduction rounds (2026-05-03, 2026-05-06, 2026-05-10, 2026-05-12) into a structural diagnosis. This file does **not** close the KW and does **not** authorize another retry. It's the evidence base for the 2026-07-09 decision.

**Scope:** read-only investigation. No Akash deploys, no SDL changes, no escrow spent.

## Symptom

The GPU-backed open-weights floor SDL ([`infra/akash/relay-deployment.yaml`](../../infra/akash/relay-deployment.yaml)) — which adds an `xion-ollama` sidecar with an NVIDIA-class GPU constraint to the working CPU SDL — fails to reach an externally-reachable `/health` endpoint after lease acceptance. Same SDL minus the GPU sidecar ([`infra/akash/relay-deployment-cpu-only.yaml`](../../infra/akash/relay-deployment-cpu-only.yaml)) succeeds at `dseq=26770709` (Akash CPU + Chutes hybrid lease, live since 2026-05-10).

## Four-round evidence table

| Round | Date | Attempts | Closure record | Outcome distribution |
|---|---|---|---|---|
| 1 | 2026-05-03 | 3 GPU attempts | (in STATE_OF_XION_PREFLIGHT, Runtime Relight Evidence) | 3× ingress-unreachable post-deploy |
| 2 | 2026-05-06 | 3 | [`relay-akash-closure-2026-05-06.json`](../../genesis/DEPLOYMENT_RECORDS/relay-akash-closure-2026-05-06.json) | 2× manifest-refused, 1× ingress-unreachable |
| 3 | 2026-05-10 | 3 | [`relay-akash-closure-2026-05-10.json`](../../genesis/DEPLOYMENT_RECORDS/relay-akash-closure-2026-05-10.json) | 3× ingress-unreachable post-deploy |
| 4 | 2026-05-12 | 1 | [`relay-akash-closure-2026-05-12.json`](../../genesis/DEPLOYMENT_RECORDS/relay-akash-closure-2026-05-12.json) | 1× manifest-refused |

**Provider exclusions accumulated across rounds:** `akash12v6…fv3fx`, `akash17wh…4qejw`, `akash1rja…wt8d`, `akash1sevd…dwd4e`, `akash1ta6…nr5d`, `akash18ga…sz6xc`. **Preferred-provider** `akash1st7…t3r5g` was named in rounds 2–4 and did not bid in round 4; bid only intermittently in earlier rounds.

**Spend:** ~0.9 AKT gas per round on average, all `uact` escrow refunded by `AkashService.deploy_relay()` auto-close. No funds lost; only gas and operator time.

## Two distinct failure modes

### Mode A — Manifest refusal at submit-time (rounds 2, 4)

Lease accepts on-chain. Then `provider-services send-manifest` returns **exit 1** with stderr `submit manifest to some providers has been failed`. The provider's HTTPS manifest endpoint rejects the SDL before the pod is ever scheduled.

[`xion_ops/services/akash.py:465`](../../xion_ops/services/akash.py) (`AkashService.send_manifest`) wraps the underlying `provider-services send-manifest` call with `XION_AKASH_SEND_MANIFEST_TIMEOUT_SEC` (default 120s, raised to 300s in retry recipe). Increasing the timeout did not change the outcome in round 4 — the provider returns the failure *fast*, not via timeout.

This mode is consistent with the provider's manifest controller either (a) being misconfigured for GPU profiles, (b) hitting a cluster-side quota/admission rule, or (c) the underlying Kubernetes ingress class not accepting GPU-tainted nodes.

### Mode B — Forwarded port unreachable post-deploy (rounds 1, 3)

Manifest accepts, lease is healthy from Akash's view, pod likely runs. But the provider-published forwarded URL (`provider.<host>:<port>`) returns **curl exit 7** — TCP-level connection refused, not HTTP-level error. The port is not actually open at the provider's ingress IP.

**Load-bearing observation** from the 2026-05-10 record on `akash1rja3y2…`:

> Same provider successfully closed dseq=26595076 on 2026-04-29 at port 31503; the port changes per lease and recent leases route to closed ports.

That is: the *same provider* served a working lease in April but published a non-routing port on a new lease in May. The provider's NAT / reverse-proxy mapping table for new leases is not being honored by upstream networking.

## Why this is provider-side, not Xion-side

1. **The CPU SDL works on the same Akash market.** [`relay-deployment-cpu-only.yaml`](../../infra/akash/relay-deployment-cpu-only.yaml) uses the same image, the same `expose: port: 8443 / as: 443 / to: global: true` stanza, the same `placement.akash.pricing.denom: uact` configuration. Only the GPU sidecar and resource profile differ. CPU lease `dseq=26770709` is currently reachable at `https://provider.akash-palmito.org:31301`.

2. **The failure varies by *lease*, not by *provider*.** Provider `akash1rja3y2…wt8d` was reachable on dseq 26595076 (port 31503), unreachable on dseq 26769739 (port 31253). The provider didn't change; the lease did. This is inconsistent with "Xion's SDL is wrong" and consistent with "the provider's new-lease NAT mapping is broken."

3. **No SDL change has moved the needle.** Across four rounds, the GPU SDL has been substantially the same shape (the model list under `gpu.attributes.vendor.nvidia` was widened to include rtx3090/4090/a4000/a5000/a6000/l4/l40/a100 — strictly more permissive than the original a100-only — and that helped attract bids but did not improve the post-acceptance failure rate).

4. **No flag we control addresses provider-side NAT misconfiguration.** The `--exclude-provider`, `--prefer-provider`, and timeout knobs in [`xion_ops/services/akash.py:628`](../../xion_ops/services/akash.py) (`AkashService.deploy_relay`) bias provider selection but cannot make a chosen provider's ingress work.

## Root-cause hypothesis (structural)

The Akash GPU provider market at sub-$0.05/hr equivalent (≤ ~250 uact/block on RTX 3090/4090) is dominated by under-resourced operators running consumer/home-lab Kubernetes clusters. Two failure surfaces correlate with that infrastructure profile:

- **Mode A** is consistent with provider-side `akash-provider` versions that handle GPU manifests inconsistently, especially when the SDL requests GPU + storage + memory profiles that hit cluster admission policies the operator hasn't tuned.
- **Mode B** is consistent with `kube-router` / Nginx ingress on home-lab clusters where new lease ports are allocated in Kubernetes but the upstream ISP NAT / port-forwarding doesn't propagate. The provider's published `forwarded_url` references a port that is reserved on their cluster but not open on their public IP.

The "professional" GPU providers on Akash (a100/l40 dedicated hosting) bid in the **2034 uact/block** range — roughly 9× the cheap-GPU price. At those rates the relay-floor budget is uneconomical, but those providers are the ones who would not exhibit either failure mode.

## Why retries don't help (and shouldn't continue)

- The provider pool at cheap-GPU price points is structurally the wrong infrastructure for our requirement.
- The preferred provider `akash1st7…t3r5g` does not reliably bid on demand — round 4 confirmed this. We can't pin to a known-good provider via flags alone.
- Each round burns gas + lease rent for no closer evidence than we already have. Four rounds, ~3.6 AKT total. A fifth round under identical flags will produce a fifth row with the same shape.
- This is exactly the failure mode KW pay-down requirements were written to detect: "Re-close only after a fresh Akash GPU lease passes the probe-first provider discipline, exposes a reachable `/health`, and returns an `open_weights_only` `/chat` smoke turn from outside the provider network." None of the four rounds satisfy that bar.

## Valid next moves (not retries)

Ranked by what they actually pay down:

1. **Hold the dated residue to 2026-07-09 and let Chutes/SN64 + CPU-only Akash CPU+Chutes hybrid stand as the operational floor.** (Operator-selected on 2026-05-12 per the closure record.) Chutes/Bittensor SN64 is decentralized via Bittensor; the Akash CPU lease `dseq=26770709` satisfies Invariant 17 substrate-portability evidence. KW-FLOOR-DEPLOY-001 stays `mitigated-residual` until 2026-07-09. **Cost:** zero spend, well-documented honesty residue.

2. **Pursue a bilateral relationship with a known-good GPU provider out-of-band.** Identify a single Akash provider with reliable GPU ingress (e.g. by direct contact at `akash1st7…t3r5g`'s control plane, or via an Akash community channel). Sign an off-Market lease at agreed pricing. **Cost:** operator time, possibly higher fixed price; would close KW-FLOOR-DEPLOY-001 with one successful deploy.

3. **Investigate a different decentralized GPU substrate** (Render Network, io.net, Akash via private bilateral agreement, etc.). Out of scope for KW-FLOOR-DEPLOY-001 *as currently scoped* (the KW names Akash specifically), but a candidate for a new KW + substrate-portability expansion. **Cost:** new substrate adapter work; substantial.

4. **Passive wait for Akash market structural improvement.** Re-test every ~3 weeks (next read-only test target: **2026-06-02**) by running one single retry under existing flags. Not to close — to confirm the structural failure still applies. If 2026-06-02 fails identically, that's evidence for an *explicit dated slip past 2026-07-09* rather than another flag tweak. **Cost:** ~0.9 AKT every three weeks.

## Explicit non-recommendations

- **Do not retry under identical flags inside the dated residue window.** The four-round evidence is sufficient; further rounds add gas burn without diagnostic value.
- **Do not mark KW-FLOOR-DEPLOY-001 closed by assertion**, by widening the SDL further, or by re-framing Chutes/SN64 as the "deployed Akash floor." Chutes is a separate substrate; the KW is scoped to Akash.
- **Do not message externally that the Akash GPU floor is operational** until a successful lease passes the probe-first discipline. Falsifier in `docs/STATE_OF_XION_PREFLIGHT.md` § Sprint Mode Falsification Statements applies.

## What would change this diagnostic

The diagnostic should be revisited if:

- A bilateral provider relationship lands a successful lease (closes the KW outright).
- A round at the **2026-06-02 read-only test target** succeeds with *no flag changes* — that would suggest the Akash market self-corrected and the residue can be paid down before 2026-07-09.
- A round at 2026-06-02 fails identically — that suggests filing a dated slip past 2026-07-09 *now* rather than at the deadline.
- A new failure mode appears (e.g. lease accepts and forwarded ingress is reachable but `xion-ollama` itself fails to pull `gemma4:e4b-it-q4_K_M`). That would shift the KW from infrastructure to substrate, and the response would change.

## Cross-references

- KW entry: [KNOWN_WEAKNESSES.md → KW-FLOOR-DEPLOY-001](../../KNOWN_WEAKNESSES.md)
- D4 shortcut ledger: [docs/D4_PREFLIGHT.md](../D4_PREFLIGHT.md) (no specific GPU-floor row; covered under Akash floor evidence in `KW-FLOOR-DEPLOY-001`)
- Service code: [xion_ops/services/akash.py](../../xion_ops/services/akash.py) `AkashService.deploy_relay`, `send_manifest`
- SDL files: [`relay-deployment.yaml`](../../infra/akash/relay-deployment.yaml) (GPU), [`relay-deployment-cpu-only.yaml`](../../infra/akash/relay-deployment-cpu-only.yaml) (working CPU baseline), [`relay-deployment-cpu-hybrid.yaml`](../../infra/akash/relay-deployment-cpu-hybrid.yaml) (current live lease shape)
- Survey ledger: [`ledgers/AKASH_DEPLOY_SURVEY_LEDGER.jsonl`](../../ledgers/AKASH_DEPLOY_SURVEY_LEDGER.jsonl)
- Closure evidence: `genesis/DEPLOYMENT_RECORDS/relay-akash-closure-2026-05-{06,10,12}.json`
