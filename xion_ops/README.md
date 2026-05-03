# xion-ops

`xion_ops` is Xion's operator automation layer. It keeps load-bearing external
integrations behind stable Python interfaces so the operator CLI, thin legacy
scripts, the local HTTP API, and future Xion runtime code all call the same
methods.

The package follows `.cursor/rules/gateway-pattern.mdc`: callers must use the
service or deployer interface and the central registry. They must not branch on
concrete vendors directly.

## Layers

- `services/` wraps one external substrate: Akash, Arweave, Chutes, Base EVM.
- `deployers/` composes services into end-to-end deploys of Xion-owned systems.
- `cli.py` and `server.py` expose the same methods for operator and API callers.

## Add A Vendor Service

1. Create `xion_ops/services/<vendor>.py` and subclass `OpsService`.
2. Implement `addresses()`, `balances()`, and `health()` plus vendor-specific primitives.
3. Register the class in `xion_ops/registry.py` `ALL_SERVICES`.
4. Add CLI commands in `xion_ops/cli.py` and, if needed, routes in `xion_ops/server.py`.
5. Add wallet rows to `genesis/FUNDING_TARGETS.json`.
6. Add offline tests that mock commands or gateways.

## Add A Deployer

1. Create `xion_ops/deployers/<name>.py` and subclass `Deployer`.
2. Implement `prepare()`, `deploy()`, `verify()`, and `rollback()` by composing services.
3. Register the class in `xion_ops/deployers/__init__.py` `ALL_DEPLOYERS`.
4. Add a `xion-ops deploy <name>` subcommand and a `POST /deploy/<name>` route.
5. Write mocked tests that cover success and rollback.

## Operator Commands

```bash
python -m xion_ops balances
python -m xion_ops balances --service base-evm
python -m xion_ops base-evm prepare-sepolia-env
python -m xion_ops base-evm preflight-treasury --network base-sepolia
python -m xion_ops base-evm deploy-treasury --network base-sepolia
python -m xion_ops akash deploy --sdl-path infra/akash/relay-deployment.yaml

# Akash CLI mirrors provider-services flows (see docs/runbooks/AKASH_RELAY_DEPLOY.md).
# Typical env: AKASH_NODE, AKASH_CHAIN_ID, AKASH_GAS / AKASH_GAS_PRICES / AKASH_GAS_ADJUSTMENT,
# XION_AKASH_KEY, XION_AKASH_OWNER, AKASH_WSL_REPO (Windows WSL cwd override).
python -m xion_ops akash cert-ensure
python -m xion_ops akash mint-act 10000000 --wait-ledger
python -m xion_ops akash deployment-list --json-output
python -m xion_ops akash deployment-get <dseq>
python -m xion_ops akash lease-list --dseq <dseq>
python -m xion_ops akash tx <txhash>
python -m xion_ops akash lease-status <dseq> <provider> [--service-name xion-relay]

# Wait tuning (defaults in parentheses): bids ~25s initial delay then poll every 10s up to 300s
# (XION_AKASH_FIRST_BID_DELAY_SEC, XION_AKASH_BID_POLL_SEC, XION_AKASH_BID_WAIT_SEC); readiness poll 15s up to 900s
# (XION_AKASH_READY_POLL_SEC, XION_AKASH_WAIT_READY_SEC); tx inclusion poll (XION_AKASH_TX_POLL_SEC / XION_AKASH_TX_WAIT_SEC);
# disable inclusion wait with XION_AKASH_WAIT_TX=0 (tests only).

# End-to-end relay (Akash/Chutes compose deployers; relay registry publishes by default)
python -m xion_ops deploy relay-akash                       # `--exclude-provider ...`, `--no-publish-registry`
python -m xion_ops deploy relay-chutes --help               # default ref, `--build-wait`, cord poll ~600s / warmup CLI ~660s (see .env.example)
python -m xion_ops chutes images-list --limit 5             # `chutes images list` (quota / build status)
python -m xion_ops chutes chutes-get <name_or_id>           # `chutes chutes get` (instances)
python -m xion_ops registry update-chutes-row --help        # patch committed `ledgers/RELAY_REGISTRY.json` Chutes row (`relays[1]`)

python -m xion_ops arweave publish-relay-registry
```

## HTTP Server

```bash
export XION_OPS_BEARER=change-me
xion-ops-server
```

The server binds to `127.0.0.1:9100` by default. Public exposure and multi-operator
auth are separate hardening work.

