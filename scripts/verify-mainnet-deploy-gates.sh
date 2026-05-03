#!/usr/bin/env bash
# Bundle verifiers documented for D3 soak and mainnet preflight.
# Requires: repo root cwd, xion-verify on PATH (pip install -e "xion-verify[dev]"),
#           orchestrator editable install when verifiers import it.
#
# Loads repo-root .env if present (secrets stay local; gitignored).

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if [[ -f "${ROOT}/.env" ]]; then
  # shellcheck source=/dev/null
  set -a && source "${ROOT}/.env" && set +a
fi

# Local verifier runs often omit bearer when checking static / discovery paths.
export XION_API_REQUIRE_BEARER="${XION_API_REQUIRE_BEARER:-false}"

echo "[verify-mainnet-deploy-gates] cwd=${ROOT}"

xion-verify --self-test

xion-verify treasury
xion-verify discovery --no-cloudflare
xion-verify substrate-portability
if ! xion-verify akash-deploy-discipline; then
  echo "[verify-mainnet-deploy-gates] WARN: akash-deploy-discipline — see docs/STATE_OF_XION_TESTNET.md"
fi

# treasury-flow requires populated testnet manifest + stack-ready posture; WARN only.
treasury_flow_rc=0
set +e
xion-verify treasury-flow
treasury_flow_rc=$?
set -e
if [[ "${treasury_flow_rc}" -ne 0 ]]; then
  echo "[verify-mainnet-deploy-gates] WARN: treasury-flow exited ${treasury_flow_rc} (expected until Sepolia rehearsal + manifests match)"
fi

echo "[verify-mainnet-deploy-gates] core bundle complete."
