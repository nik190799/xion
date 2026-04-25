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

# ---- Patch upstream MU: GraphQL fallback for `Scheduler` on process (localnet) --
# On ArLocal, getProcess() can cache gateway data without a `Scheduler` tag; aos then
# hits "No Scheduler tag found on process ...". Upstream only vendors services/mu/Dockerfile
# (MU source is cloned inside the image from permaweb/ao); the patch script fetches
# schedulerLocations.js, writes schedulerLocations.xion.js into the build context, and
# injects COPY into the Dockerfile. Rebuild mu when the overlay or Dockerfile changed.
_MU_DF="$UPSTREAM_DIR/services/mu/Dockerfile"
if [ ! -f "$_MU_DF" ]; then
  log "warn: MU patch skipped (missing $_MU_DF). Clone upstream first (this script normally creates .upstream/)."
else
  log "scheduling getProcess GraphQL tag patch (MU Dockerfile: $_MU_DF)"
  if patch_log="$(XION_AO_LOCALNET_UPSTREAM_DIR="$UPSTREAM_DIR" bash "$SCRIPT_DIR/patch-ao-localnet-mu-graphql-fallback.sh" 2>&1)"; then
    if [ -n "$patch_log" ]; then
      while IFS= read -r pline; do
        [ -n "$pline" ] && log "  $pline"
      done <<EOF
$patch_log
EOF
    fi
    if echo "$patch_log" | grep -qE " patched |injected Dockerfile" 2>/dev/null; then
      log "Rebuilding ao-localnet-mu (Xion GraphQL tag fallback) — required for local aos; may take a few minutes …"
      docker compose -f "$INFRA_DIR/docker-compose.yaml" build mu
    elif echo "$patch_log" | grep -qF "already up to date" 2>/dev/null; then
      log "MU schedulerLocations overlay already current; no rebuild."
    elif echo "$patch_log" | grep -qE "pattern not found|skip|layout changed" 2>/dev/null; then
      log "warn: MU patch did not apply (see lines above). aos may fail with 'No Scheduler tag found on process' until fixed."
    fi
  else
    log "warn: patch-ao-localnet-mu-graphql-fallback.sh failed; continuing (see above)"
  fi
fi

# ---- Patch upstream CU: Node 22+ (current ao/servers/cu main uses Promise.withResolvers) ----
# Upstream pins FROM node:20-alpine. Main-branch CU then throws in readResult:
#   Promise.withResolvers is not a function → aos "Could not connect to process" (not a timing race).
if [ -f "$SCRIPT_DIR/patch-ao-localnet-cu-node22.sh" ]; then
  set +e
  cu_log="$(XION_AO_LOCALNET_UPSTREAM_DIR="$UPSTREAM_DIR" bash "$SCRIPT_DIR/patch-ao-localnet-cu-node22.sh" 2>&1)"
  cu_rc=$?
  set -e
  if [ -n "$cu_log" ]; then
    while IFS= read -r cline; do
      [ -n "$cline" ] && log "  $cline"
    done <<EOF
$cu_log
EOF
  fi
  if [ "$cu_rc" -eq 2 ]; then
    log "Rebuilding ao-localnet-cu (Node 22 base) …"
    docker compose -f "$INFRA_DIR/docker-compose.yaml" build cu
  fi
fi

# ---- Bring up the stack via the wrapper compose -----------------------------
log "Starting localnet stack (first run can take 10-15 min while building from source) ..."
docker compose -f "$INFRA_DIR/docker-compose.yaml" up -d --wait

# ---- Poll the Compute Unit until reachable ----------------------------------
log "Polling $GATEWAY_URL for CU readiness (timeout ${HEALTH_TIMEOUT_S}s) ..."
deadline=$(( $(date +%s) + HEALTH_TIMEOUT_S ))
while :; do
  # The CU is expected to be reachable; depending on the upstream `ao/servers/cu`
  # build, `/state/<pid>` for an unknown or synthetic PID may be 200, 404, or
  # 500. A connection-level failure (no TCP response) is what this poll is
  # really guarding against, so we treat *any* HTTP response code 200–599 as
  # "CU is speaking HTTP on the gateway port."
  http_code="$(
    curl -sS -m 2 -o /dev/null -w '%{http_code}' "${GATEWAY_URL}/state/readiness-probe-pid" 2>/dev/null || true
  )"
  if [ -n "$http_code" ] && [ "$http_code" != "000" ]; then
    if [ "$http_code" -ge 200 ] 2>/dev/null && [ "$http_code" -le 599 ] 2>/dev/null; then
      log "CU is responding at $GATEWAY_URL (HTTP $http_code on /state/<probe>)"
      break
    fi
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
  0. Seed the mock ArLocal chain (required once per fresh volume; otherwise
     aos spawn often fails with "Invalid Return 'undefined'"):
       bash scripts/ao-localnet-seed.sh
  1. Follow docs/runbooks/AO_DEPLOY_LOCALNET.md to spawn an aos process
     against the local CU/MU URLs, load ao/core/main.lua, and send the
     first Commit-State message (or: bash scripts/ao-localnet-seal.sh).
  2. After capturing the receipt fields, set XION_AO_GATEWAY_URL=$GATEWAY_URL
     and run: xion-verify ao-handlers
  3. Tear down later with:
     docker compose -f infra/ao-localnet/docker-compose.yaml down -v
EOF
