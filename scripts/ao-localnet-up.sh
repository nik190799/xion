#!/usr/bin/env bash
# Xion AO Localnet bring-up (Phase 6.1.b).
#
# Brings up a self-sufficient AO substrate by cloning the upstream
# permaweb/ao-localnet stack at a pinned commit, generating the localnet
# wallets, running `docker compose up -d --wait`, and polling the Compute
# Unit at http://localhost:4004 until healthy.
#
# Usage:
#   bash scripts/ao-localnet-up.sh              # default permaweb pin
#   XION_AO_LOCALNET_COMMIT=<sha> bash scripts/ao-localnet-up.sh
#   XION_AO_LOCALNET_UPSTREAM=<repo-url> XION_AO_LOCALNET_BRANCH=<branch> \
#     XION_AO_LOCALNET_COMMIT=<sha> bash scripts/ao-localnet-up.sh
#
# After successful bring-up, the AO Compute Unit is reachable at
# $XION_AO_GATEWAY_URL (default http://localhost:4004) and is what
# `xion-verify ao-handlers` reads when validating tip parity.
#
# Doctrine: docs/28-AO-CORE.md § "Substrate amendment (Phase 6.1.b)"
# Runbook:  docs/runbooks/AO_DEPLOY_LOCALNET.md
# KW:       KNOWN_WEAKNESSES.md § KW-AOCORE-004 (closure path #2)

set -euo pipefail

# ---- Pinned defaults ---------------------------------------------------------
# Upstream permaweb/ao-localnet, last-committed 2024-04-10 ("chore: update cu
# and mu env vars"). Self-described as experimental; see infra/ao-localnet/README.md
# for the fallback path if this pin's build dependencies have rotted.
UPSTREAM_REPO="${XION_AO_LOCALNET_UPSTREAM:-https://github.com/permaweb/ao-localnet.git}"
UPSTREAM_BRANCH="${XION_AO_LOCALNET_BRANCH:-main}"
UPSTREAM_COMMIT="${XION_AO_LOCALNET_COMMIT:-2f9f98ea2e7a7d77f1791df382afb3446edc044e}"

# Verifier-side gateway URL. Default matches the upstream cu service's port
# mapping (services/cu listens on container :80, mapped to host :4004).
GATEWAY_URL="${XION_AO_GATEWAY_URL:-http://localhost:4004}"

# Readiness poll knobs.
HEALTH_TIMEOUT_S="${XION_AO_LOCALNET_HEALTH_TIMEOUT_S:-180}"
HEALTH_INTERVAL_S=2

# ---- Resolve paths -----------------------------------------------------------
# POSIX-portable equivalent of `dirname $(readlink -f "$0")` that works on
# WSL2, native Linux, and macOS without GNU readlink.
script_dir() {
  local src="${BASH_SOURCE[0]}"
  while [ -h "$src" ]; do
    local dir
    dir="$(cd -P "$(dirname "$src")" && pwd)"
    src="$(readlink "$src")"
    [[ "$src" != /* ]] && src="$dir/$src"
  done
  cd -P "$(dirname "$src")" && pwd
}
SCRIPT_DIR="$(script_dir)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRA_DIR="$REPO_ROOT/infra/ao-localnet"
UPSTREAM_DIR="$INFRA_DIR/.upstream"

# ---- Pre-flight --------------------------------------------------------------
log()  { printf '[ao-localnet-up] %s\n' "$*" >&2; }
fail() { printf '[ao-localnet-up] FAIL: %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || fail "docker not found in PATH"
command -v git    >/dev/null 2>&1 || fail "git not found in PATH"
command -v curl   >/dev/null 2>&1 || fail "curl not found in PATH (needed for health poll)"

docker info >/dev/null 2>&1 || fail "docker daemon not running (start Docker Desktop or systemctl start docker)"

compose_version="$(docker compose version --short 2>/dev/null || true)"
[ -n "$compose_version" ] || fail "docker compose v2 not installed; need v2.20+ for the include: directive"

[ -d "$INFRA_DIR" ] || fail "$INFRA_DIR not found (cwd is $REPO_ROOT)"

# ---- Clone or update upstream at the pinned commit --------------------------
if [ ! -d "$UPSTREAM_DIR/.git" ]; then
  log "Cloning $UPSTREAM_REPO (branch $UPSTREAM_BRANCH) into $UPSTREAM_DIR ..."
  git clone --branch "$UPSTREAM_BRANCH" "$UPSTREAM_REPO" "$UPSTREAM_DIR"
else
  log "Reusing existing clone at $UPSTREAM_DIR (fetching latest refs)"
  git -C "$UPSTREAM_DIR" fetch --all --tags --prune
fi

current_sha="$(git -C "$UPSTREAM_DIR" rev-parse HEAD)"
if [ "$current_sha" != "$UPSTREAM_COMMIT" ]; then
  log "Pinning upstream to commit $UPSTREAM_COMMIT (was $current_sha)"
  git -C "$UPSTREAM_DIR" checkout --detach "$UPSTREAM_COMMIT"
fi

# ---- Generate localnet wallets (one-time per clone) -------------------------
WALLETS_DIR="$UPSTREAM_DIR/wallets"
if [ ! -f "$WALLETS_DIR/ao-wallet.json" ]; then
  log "Generating localnet wallets via $WALLETS_DIR/generateAll.sh ..."
  if [ ! -x "$WALLETS_DIR/generateAll.sh" ]; then
    chmod +x "$WALLETS_DIR/generateAll.sh" 2>/dev/null || true
  fi
  ( cd "$WALLETS_DIR" && bash ./generateAll.sh )
else
  log "Wallets already generated under $WALLETS_DIR/"
fi

# ---- Bring up the stack via the wrapper compose -----------------------------
log "Starting localnet stack (first run can take 10-15 min while building from source) ..."
docker compose -f "$INFRA_DIR/docker-compose.yaml" up -d --wait

# ---- Poll the Compute Unit until reachable ----------------------------------
log "Polling $GATEWAY_URL for CU readiness (timeout ${HEALTH_TIMEOUT_S}s) ..."
deadline=$(( $(date +%s) + HEALTH_TIMEOUT_S ))
while :; do
  # The CU at /state/<arbitrary-pid> typically returns 404 when the process
  # is unknown but a 5xx if the CU itself is not ready. Either a 200 OR a
  # 404 is "the CU is responding"; only network-level failure or 5xx means
  # not-ready.
  http_code="$(curl -s -o /dev/null -w '%{http_code}' "${GATEWAY_URL}/state/readiness-probe-pid" || true)"
  if [ "$http_code" = "200" ] || [ "$http_code" = "404" ]; then
    log "CU is responding at $GATEWAY_URL (HTTP $http_code on /state/<probe>)"
    break
  fi
  now=$(date +%s)
  if [ "$now" -ge "$deadline" ]; then
    log "CU did not become ready within ${HEALTH_TIMEOUT_S}s. Last HTTP code: ${http_code:-NONE}"
    log "Inspect logs with: docker compose -f $INFRA_DIR/docker-compose.yaml logs --tail=200"
    fail "localnet bring-up: readiness timeout"
  fi
  sleep "$HEALTH_INTERVAL_S"
done

cat <<EOF
[ao-localnet-up] OK. Localnet substrate is up.

  Pinned upstream:   $UPSTREAM_REPO @ $UPSTREAM_COMMIT
  Compute Unit URL:  $GATEWAY_URL
  Messenger Unit:    http://localhost:4002 (used by aos CLI internally)
  Scheduler Unit:    http://localhost:4003
  Arweave (mock):    http://localhost:4000
  Bundler:           http://localhost:4007

Next steps for the Phase 6.1 deploy:
  1. Follow docs/runbooks/AO_DEPLOY_LOCALNET.md to spawn an aos process
     against the local CU/MU URLs, load ao/core/main.lua, and send the
     first Commit-State message.
  2. After capturing the receipt fields, set XION_AO_GATEWAY_URL=$GATEWAY_URL
     and run: xion-verify ao-handlers
  3. Tear down later with:
     docker compose -f infra/ao-localnet/docker-compose.yaml down -v
EOF
