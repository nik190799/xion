#!/usr/bin/env bash
# Demo: minimal Akash deployment (smoke SDL + GET /health).
#
# Official docs (read first):
#   https://akash.network/docs/developers/deployment/akash-sdl
#   https://akash.network/docs/developers/deployment/cli
#   https://akash.network/docs/developers/deployment/cli/commands-reference/
#   https://akash.network/docs/developers/deployment/akash-sdl/syntax-reference
#
# Xion runbook (uact/BME, client cert, mTLS lease-status, WSL):
#   docs/runbooks/AKASH_RELAY_DEPLOY.md
#
# Prerequisites:
#   - provider-services, funded keyring, uact escrow (see runbook).
#   - Public image for infra/akash/relay-smoke-minimal.yaml (build docker/smoke-akash and push).
#   - Docker: on Windows Git Bash, this script runs docker via WSL (docker is typically installed
#     in the Linux distro). Override with DEMO_AKASH_DOCKER_NATIVE=1 to use host PATH docker.
#     Set AKASH_WSL_REPO to the repo path inside WSL if auto-detection is wrong (same as xion_ops).
#
# Optional: DEMO_AKASH_MINT_UAKT=<int> — if set, runs:
#   python -m xion_ops akash mint-act "$DEMO_AKASH_MINT_UAKT" --wait-ledger
#   (spends uakt; only when you intend to fund escrow.)
#
# Optional: DEMO_AKASH_BUILD_SMOKE_IMAGE=1 — build and push docker/smoke-akash using WSL docker
#   (or native docker when DEMO_AKASH_DOCKER_NATIVE=1). Tag from DEMO_AKASH_SMOKE_IMAGE
#   (default nikhilkadalge/xion-akash-smoke:minimal). Requires docker login for push.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Absolute repo path as seen inside WSL (for docker build context / provider-services alignment).
repo_wsl_cd() {
  if [[ -n "${AKASH_WSL_REPO:-}" ]]; then
    printf '%s' "${AKASH_WSL_REPO}"
    return
  fi
  local r="$REPO_ROOT"
  if [[ "$r" == /mnt/* ]]; then
    printf '%s' "$r"
    return
  fi
  if [[ "$r" =~ ^/([a-zA-Z])/(.*)$ ]]; then
    printf '/mnt/%s/%s' "$(printf '%s' "${BASH_REMATCH[1]}" | tr '[:upper:]' '[:lower:]')" "${BASH_REMATCH[2]}"
    return
  fi
  printf '%s' "$r"
}

use_wsl_docker() {
  if [[ "${DEMO_AKASH_DOCKER_NATIVE:-}" == "1" ]]; then
    return 1
  fi
  case "${OSTYPE:-}" in
    msys*|cygwin*) return 0 ;;
  esac
  if command -v docker >/dev/null 2>&1; then
    return 1
  fi
  command -v wsl >/dev/null 2>&1
}

run_docker() {
  if use_wsl_docker; then
    local wsl_cd
    wsl_cd="$(repo_wsl_cd)"
    local inner="set -euo pipefail; cd $(printf '%q' "$wsl_cd"); docker"
    local a
    for a in "$@"; do
      inner+=" $(printf '%q' "$a")"
    done
    wsl bash -lc "$inner"
  else
    docker "$@"
  fi
}

smoke_docker_build_push() {
  local tag="${DEMO_AKASH_SMOKE_IMAGE:-nikhilkadalge/xion-akash-smoke:minimal}"
  echo "demo-minimal-akash-deploy: build/push smoke image $tag (context docker/smoke-akash)..."
  if use_wsl_docker; then
    echo "demo-minimal-akash-deploy: using WSL docker (repo in WSL: $(repo_wsl_cd))"
  fi
  run_docker build -t "$tag" docker/smoke-akash
  run_docker push "$tag"
}

echo "demo-minimal-akash-deploy: repo root=$REPO_ROOT"
echo "  Official: https://akash.network/docs/developers/deployment/cli"
echo "  Runbook:  docs/runbooks/AKASH_RELAY_DEPLOY.md"
echo "  Akash CLI / health checks: use WSL from this repo when on Windows (see xion_ops/README.md)."
echo ""

if [[ -n "${DEMO_AKASH_MINT_UAKT:-}" ]]; then
  echo "demo-minimal-akash-deploy: mint-act ${DEMO_AKASH_MINT_UAKT} uakt (wait-ledger)..."
  python -m xion_ops akash mint-act "${DEMO_AKASH_MINT_UAKT}" --wait-ledger
fi

if [[ "${DEMO_AKASH_BUILD_SMOKE_IMAGE:-}" == "1" ]]; then
  smoke_docker_build_push
fi

echo "demo-minimal-akash-deploy: cert-ensure..."
python -m xion_ops akash cert-ensure

export XION_AKASH_LEASE_SERVICE_NAME=smoke-web

echo "demo-minimal-akash-deploy: if image pull fails, build/push docker/smoke-akash (see relay-smoke-minimal.yaml header)."

echo "demo-minimal-akash-deploy: deploy relay-akash (smoke SDL, no registry publish)..."
python -m xion_ops deploy relay-akash \
  --sdl-path infra/akash/relay-smoke-minimal.yaml \
  --no-publish-registry

echo "demo-minimal-akash-deploy: OK"
