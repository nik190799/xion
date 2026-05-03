#!/usr/bin/env bash
# Bundle verifiers documented for D3 soak and mainnet preflight.
#           or WSL: `pip install -e ./xion-verify[dev]` so `python3 -m xion_verify` works.
#           Orchestrator editable install when verifiers import it.
#
# Loads repo-root .env if present (secrets stay local; gitignored).

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if command -v xion-verify >/dev/null 2>&1; then
  xion_verify() { xion-verify "$@"; }
elif command -v python3 >/dev/null 2>&1 && python3 -c "import xion_verify" 2>/dev/null; then
  xion_verify() { python3 -m xion_verify "$@"; }
elif command -v python >/dev/null 2>&1 && python -c "import xion_verify" 2>/dev/null; then
  xion_verify() { python -m xion_verify "$@"; }
else
  echo "[verify-mainnet-deploy-gates] error: install xion-verify (pip install -e ./xion-verify[dev]) or ensure python can import xion_verify" >&2
  exit 1
fi

if [[ -f "${ROOT}/.env" ]]; then
  # shellcheck source=/dev/null
  set -a && source "${ROOT}/.env" && set +a
fi

# Local verifier runs often omit bearer when checking static / discovery paths.
export XION_API_REQUIRE_BEARER="${XION_API_REQUIRE_BEARER:-false}"

echo "[verify-mainnet-deploy-gates] cwd=${ROOT}"

xion_verify --self-test

xion_verify treasury
xion_verify discovery --no-cloudflare
xion_verify substrate-portability
if ! xion_verify akash-deploy-discipline; then
  echo "[verify-mainnet-deploy-gates] WARN: akash-deploy-discipline — see docs/STATE_OF_XION_TESTNET.md"
fi

# treasury-flow requires populated testnet manifest + stack-ready posture; WARN only.
treasury_flow_rc=0
set +e
xion_verify treasury-flow
treasury_flow_rc=$?
set -e
if [[ "${treasury_flow_rc}" -ne 0 ]]; then
  echo "[verify-mainnet-deploy-gates] WARN: treasury-flow exited ${treasury_flow_rc} (expected until Sepolia rehearsal + manifests match)"
fi

if [[ "${TREASURY_SOAK_PROBES:-}" == "1" ]]; then
  bash "${ROOT}/scripts/treasury-soak-probes.sh"
else
  echo "[verify-mainnet-deploy-gates] hint: TREASURY_SOAK_PROBES=1 bash $0 to run cast probes (requires forge cast on PATH)"
fi

echo "[verify-mainnet-deploy-gates] core bundle complete."
