# RESURRECT — Executable Runbook

> *If you cannot do it from a phone at 3am, it is not resurrection — it is a fantasy.*

## Property

After **total Relay loss**, a trained human restores liveness using **only** this file, public repos, and Arweave gateways — no private wikis.

## Invariants touched

Exercises **Invariant 7** continuity (same AO Process ID) and **Invariant 14** migration posture when keys rotate under stress.

## Verification

After steps: `xion-verify all` (when CLI exists) must pass against live Core.

## Deprecation

Steps version with git tags; this file updates via governance, re-hashed in `GENESIS_ARTIFACT.md`.

---

## Preconditions (phone checklist)

- [ ] Arweave gateway URL reachable (try `https://arweave.net` then `https://ar-io.net`)
- [ ] GitHub reachable
- [ ] AO process id + Safe addresses written on paper wallet

---

## 1 — Clone authoritative repo

```sh
git clone https://github.com/<ORG>/xion-os.git
cd xion-os
git checkout <PINNED_RELEASE_TAG>
```

Replace `<ORG>` / `<PINNED_RELEASE_TAG>` with values published in monthly State-of-Xion.

## 2 — Verify doctrine hashes (read-only)

When `tools/xion-verify` exists in the checkout:

```sh
cd tools/xion-verify
cargo build --release
./target/release/xion-verify all --ao-process <AO_PROCESS_ID> --gateway https://arweave.net
```

Until the CLI ships, **manual substitute:** fetch Core covenant/invariants/soul hashes from AO read API and `shasum -a 256` local `genesis/*.md` files; require equality.

## 3 — Vault unseal (credentials)

Follow [`CREDENTIALS.md`](./CREDENTIALS.md): assemble **2-of-3** shards on an air-gapped laptop if possible; export a time-bounded vault unlock token to the new Relay host through the one-time channel documented in operator runbook.

## 4 — Deploy fresh Relay (Akash example)

```sh
cd deploy/akash
akash tx deployment create deploy.yaml --from <key>
```

Use SDL pinned to the image digest broadcast by Core in the last good state commit.

## 5 — Register Relay with Core

Use operator tooling (documented in repo `README.md` post-implementation) to send `Register-Relay` with new pubkey; wait for Core authorization event.

## 6 — Smoke protocol

```sh
curl -fsS "https://<RELAY_HOST>/status" | jq .
curl -fsS "https://<RELAY_HOST>/covenant" | jq .hash
```

Covenant hash must equal Core.

## 7 — Ledger notice

Append `INCIDENT_LEDGER.md` entry (via governance tool) stating resurrection window, actors, and verification transcript hash.

---

*If any step fails: stop, open `docs/runbooks/core-unreachable.md`, do not improvise spend paths.*
