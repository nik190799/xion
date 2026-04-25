#!/usr/bin/env bash
# One-shot Phase 6.1.b localnet seal (docs/runbooks/AO_DEPLOY_LOCALNET.md).
# Prerequisites: `bash scripts/ao-localnet-up.sh` already OK; Node 20 + aos in PATH.
#
# Usage:
#   cd /path/to/xion-os && bash scripts/ao-localnet-seal.sh
#   AOS_NAME=my-local-core bash scripts/ao-localnet-seal.sh
#
# Three steps:
#   (1) `aos $AOS_NAME --run "$(cat ao/core/main.lua)"` — spawns the named process AND
#       evaluates main.lua in one shot; we extract the printed pid from "Your AOS Process: ..."
#   (2) `node scripts/ao-localnet-send-commit-state.cjs $PID` — owner-signed Commit-State
#       via aoconnect (Send-from-Eval would have msg.From == ao.id and be rejected).
#   (3) `aos $PID --run "return tostring(ao.id)..'|'..tostring(Owner)"` — read ao.id + Owner.
# Steps 2 + 3 use $PID (a 43-char base64url id) so register's isAddress branch fires;
# otherwise ArLocal's gql index lag would cause each call to spawn a fresh process,
# leaving the receipt naming a process whose StateTip is still { 0, zeros }.

set -euo pipefail

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
ROOT="$(cd "$(script_dir)/.." && pwd)"
cd "$ROOT"

ENV_FILE="$ROOT/infra/ao-localnet/localnet-aos.env"
if [ -f "$ENV_FILE" ]; then
  # shellcheck source=/dev/null
  set -a
  . "$ENV_FILE"
  set +a
  echo "[ao-localnet-seal] sourced $ENV_FILE"
elif [ -z "${AOS_MODULE:-}" ]; then
  echo "[ao-localnet-seal] WARN: no AOS_MODULE. Run: bash scripts/ao-localnet-seed.sh" >&2
  echo "[ao-localnet-seal]       (aos defaults to a testnet module id; local spawn needs your ArLocal module txid.)" >&2
fi
if [ -n "${AOS_MODULE:-}" ]; then
  echo "[ao-localnet-seal] AOS_MODULE=$AOS_MODULE"
fi
if [ -n "${SCHEDULER:-}" ]; then
  echo "[ao-localnet-seal] SCHEDULER=$SCHEDULER (spawn tag; must match local Scheduler-Location publisher)"
else
  echo "[ao-localnet-seal] WARN: SCHEDULER unset — aos defaults to mainnet; local MU may return 500 on spawn. Run: bash scripts/ao-localnet-seed.sh" >&2
fi

# aos 2.0: `if (process.env.AO_URL !== 'undefined')` uses the *string* 'undefined' as a sentinel to
# keep legacy `readResult` on the local CU. Fresh spawns get `variant: null` so aos does not set it.
# @permaweb/aoconnect then does `process.env.AO_URL = void 0` on import and *wipes* the shell value.
# `scripts/patch-npm-aoconnect-preserve-ao-url.sh` removes that clobber (run below). Still export the
# sentinel so the check passes after the patch.
export AO_URL="${AO_URL:-undefined}"
echo "[ao-localnet-seal] AO_URL=$AO_URL (aos legacy sentinel; aoconnect must not clear it — see patch step)"

# CU on Node 20 vs Node 22 sanity warning: the upstream services/cu/Dockerfile pins node:20-alpine,
# but ao/servers/cu (main) uses Promise.withResolvers (Node 22+). On Node 20, every readResult fails
# inside the CU with "Promise.withResolvers is not a function", aos never sees a good prompt, and
# step (1) bails with "Could not connect to process". scripts/patch-ao-localnet-cu-node22.sh rewrites
# the Dockerfile to node:22-alpine; scripts/ao-localnet-up.sh runs it and rebuilds cu when changed.
# Probe the running CU container if docker is reachable from this shell — purely informational.
if command -v docker >/dev/null 2>&1; then
  cu_node="$(docker exec ao-localnet-cu-1 node --version 2>/dev/null || true)"
  if [ -n "$cu_node" ]; then
    case "$cu_node" in
      v22.*|v23.*|v24.*) echo "[ao-localnet-seal] CU container node: $cu_node (OK for Promise.withResolvers)" ;;
      *) echo "[ao-localnet-seal] WARN: CU container node is $cu_node — needs v22+. Run: bash scripts/patch-ao-localnet-cu-node22.sh && docker compose -f infra/ao-localnet/docker-compose.yaml build cu && docker compose -f infra/ao-localnet/docker-compose.yaml up -d cu" >&2 ;;
    esac
  fi
fi

if [ -f "$HOME/.nvm/nvm.sh" ]; then
  # shellcheck source=/dev/null
  . "$HOME/.nvm/nvm.sh"
  nvm use 20 2>/dev/null || nvm use node
fi

command -v aos >/dev/null 2>&1 || { echo "[ao-localnet-seal] aos not in PATH"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "[ao-localnet-seal] python3 required"; exit 1; }

echo "[ao-localnet-seal] aoconnect patch (legacy readResult / local CU) …"
if patch_out="$(bash "$ROOT/scripts/patch-npm-aoconnect-preserve-ao-url.sh" 2>&1)"; then
  while IFS= read -r pl || [ -n "${pl:-}" ]; do
    [ -n "$pl" ] && echo "[ao-localnet-seal]   $pl"
  done <<EOF
$patch_out
EOF
fi

AOS_NAME="${AOS_NAME:-xion-core-localnet}"
GATE="${GATE:-http://localhost:4000}"
CU="${CU:-http://localhost:4004}"
MU="${MU:-http://localhost:4002}"
LUA_RELP="ao/core/main.lua"
ROOT_SHA="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

# Pass scheduler + module on the command line. aos maps --scheduler to process.env.SCHEDULER (see
# @permaweb/aos src/index.js); connect.spawnProcess uses that for the Process DataItem. Relying only
# on a sourced file can be brittle across subshells; the MU's write-process-tx still requires a
# Scheduler tag on the signed spawn item.
aflags=( "$AOS_NAME" --legacy --gateway-url "$GATE" --cu-url "$CU" --mu-url "$MU" )
if [ -n "${SCHEDULER:-}" ]; then
  aflags+=( --scheduler "$SCHEDULER" )
fi
if [ -n "${AOS_MODULE:-}" ]; then
  aflags+=( --module "$AOS_MODULE" )
fi

# Optional warm-up: kept as a knob, not a default remedy. The "Could not connect to process" we
# previously chased was the CU-on-Node-20 Promise.withResolvers crash (see CU sanity probe above);
# once the CU is on Node 22 a 1–5s warm-up is plenty.
if [ -n "${XION_AOS_SEAL_CU_WARM_S:-}" ]; then
  echo "[ao-localnet-seal] XION_AOS_SEAL_CU_WARM_S=${XION_AOS_SEAL_CU_WARM_S} — pausing before aos connect …"
  sleep "$XION_AOS_SEAL_CU_WARM_S"
fi

echo "[ao-localnet-seal] (1/3) spawn + load $LUA_RELP for process $AOS_NAME"
# Why this is one --run call (and not --load): aos's `register(name)` in @permaweb/aos
# src/register.js queries gql for the *latest* process tagged with `name`. ArLocal indexes
# spawn DataItems lazily — between two back-to-back `aos $AOS_NAME ...` calls, the second
# call's gql query usually still sees no result and *spawns a fresh process*. The previous
# version of this script ran three separate `aos $AOS_NAME` invocations and ended up with
# three different process ids; the receipt named the third process, whose Inbox was empty
# (because Commit-State went to the second process). Solution: extract the pid from step 1's
# "Your AOS Process: <pid>" line and pass that 43-char id as the name to steps 2+3. register
# treats anything matching ^[A-Za-z0-9_-]{43}$ as an address (services/address.js#isAddress)
# and short-circuits without re-spawning even when gql can't find the tx (returns
# `{ id: name, variant: null }` on any lookup failure — see register.js around L137).
#
# Why --run instead of --load: the load early-exit branch (index.js around L256) only fires
# when (!argv.run && luaData.length > 0 && argv.load) and only prints `result.Output.data` —
# *not* the "Your AOS Process: <pid>" line we need to parse. The --run branch (index.js
# around L295) prints the pid first, then evaluates argv.run, then exit(0) cleanly.
# Single leading space is intentional: minimist (used by aos) treats any --run value
# whose first character is `-` as a boolean flag (`{ run: true }`). main.lua starts
# with `-- ao/core/main.lua` (a Lua line comment), so without the leading space the
# Lua source becomes `argv.run === true` and aoconnect blows up with
# `Buffer.from(...) Received type boolean (true)` deep inside ar-data-create. A leading
# space is invisible to Lua's parser (whitespace is skipped) and forces minimist to
# keep the value as the intended string.
LUA_SRC=" $(cat "$LUA_RELP")"
if ! out1="$(aos "${aflags[@]}" --run "$LUA_SRC" 2>&1)"; then
  echo "$out1" >&2
  echo "[ao-localnet-seal] aos step (1) failed. Likely causes (in priority):" >&2
  echo "[ao-localnet-seal]  • CU on Node 20: ao/servers/cu (main) needs Node 22+ for Promise.withResolvers." >&2
  echo "[ao-localnet-seal]    Fix: bash scripts/patch-ao-localnet-cu-node22.sh && \\" >&2
  echo "[ao-localnet-seal]         docker compose -f infra/ao-localnet/docker-compose.yaml build cu && \\" >&2
  echo "[ao-localnet-seal]         docker compose -f infra/ao-localnet/docker-compose.yaml up -d cu" >&2
  echo "[ao-localnet-seal]    (also runs as part of: bash scripts/ao-localnet-up.sh)" >&2
  echo "[ao-localnet-seal]  • aoconnect clears AO_URL on import: bash scripts/patch-npm-aoconnect-preserve-ao-url.sh" >&2
  echo "[ao-localnet-seal]  • CU logs: docker compose -f infra/ao-localnet/docker-compose.yaml logs --tail=100 cu" >&2
  exit 1
fi
echo "$out1"

# ANSI strip — chalk wraps the pid in green (\e[32m...\e[0m). Then grep for the pid line.
PID="$(printf '%s\n' "$out1" \
  | sed -E 's/\x1B\[[0-9;]*[A-Za-z]//g' \
  | grep -oE 'Your AOS Process: [A-Za-z0-9_-]{43}' \
  | tail -1 \
  | awk '{print $4}')"
if [ -z "$PID" ]; then
  echo "[ao-localnet-seal] could not extract process id from step (1) output." >&2
  echo "[ao-localnet-seal] (the spawn likely failed; scroll up for aos errors and check CU/MU logs)." >&2
  exit 1
fi
echo "[ao-localnet-seal] process id: $PID (used as the name in steps 2 + 3 — bypasses register's gql lookup)"

# Steps 2 + 3 use $PID as the name so register's isAddress branch fires and we always hit
# the same process. Mirrors the connection flags from $aflags but swaps name and drops
# --module/--scheduler (only meaningful on spawn, ignored after the process exists).
pidflags=( "$PID" --legacy --gateway-url "$GATE" --cu-url "$CU" --mu-url "$MU" )

echo "[ao-localnet-seal] (2/3) first Commit-State (tip=1) — owner-signed via aoconnect …"
# Why a Node helper instead of `aos --run "Send({...})"`: an Eval-driven Send posts the
# outbox message *from the process itself* (msg.From == ao.id), and main.lua's
# commit-state handler authorizes only `[Owner]` (see ao/core/main.lua). The result is
# a `State-Rejection / non_authorised_caller` reply — silently — which then writes a
# bogus receipt naming a process whose StateTip is still { height=0, root=zeros }. The
# helper signs the message with the owner's wallet (~/.aos.json, the same one aos uses
# for spawn) so msg.From == Owner and the handler accepts it.
#
# NODE_PATH points at aos's node_modules (the only place aoconnect is installed in this
# environment). We use a .cjs helper because Node's ESM loader does not honor NODE_PATH
# for `exports`-field resolution; aoconnect ships an explicit `require: index.cjs` entry
# for exactly this case.
AOS_NODE_MODS="$(ls -d "${NVM_DIR:-$HOME/.nvm}"/versions/node/v20.*/lib/node_modules/@permaweb/aos/node_modules 2>/dev/null | tail -1)"
if [ -z "$AOS_NODE_MODS" ] || [ ! -d "$AOS_NODE_MODS/@permaweb/aoconnect" ]; then
  echo "[ao-localnet-seal] could not locate @permaweb/aoconnect under aos's node_modules:" >&2
  echo "  searched: ${NVM_DIR:-$HOME/.nvm}/versions/node/v20.*/lib/node_modules/@permaweb/aos/node_modules" >&2
  echo "  install aos globally (npm i -g @permaweb/aos) or adjust the search path." >&2
  exit 1
fi
if ! MSGID="$(GATE="$GATE" CU="$CU" MU="$MU" \
                NODE_PATH="$AOS_NODE_MODS" \
                node "$ROOT/scripts/ao-localnet-send-commit-state.cjs" "$PID")"; then
  echo "[ao-localnet-seal] aoconnect Commit-State send failed (see helper output above)." >&2
  exit 1
fi
MSGID="$(printf '%s' "$MSGID" | tr -d '\r\n[:space:]')"
if ! [[ "$MSGID" =~ ^[A-Za-z0-9_-]{43}$ ]]; then
  echo "[ao-localnet-seal] helper returned a malformed message id: '$MSGID'" >&2
  exit 1
fi
echo "[ao-localnet-seal] commit-state message id: $MSGID"

echo "[ao-localnet-seal] waiting for scheduler/CU (15s) …"
sleep 15

echo "[ao-localnet-seal] (3/3) read ao.id + Owner from process …"
# Just confirm ao.id matches the spawn pid and capture Owner. We no longer parse the
# inbox here — the receipt's first_commit_state_message_id is the helper's MSGID above.
# shellcheck disable=SC2016
out="$(aos "${pidflags[@]}" --run "return tostring(ao.id)..'|'..tostring(Owner)" 2>&1 || true)"
echo "$out"

line="$(printf '%s\n' "$out" \
  | sed -E 's/\x1B\[[0-9;]*[A-Za-z]//g' \
  | grep -E '^[A-Za-z0-9_-]{43}\|[A-Za-z0-9_-]{43}$' \
  | tail -1)"
if [ -z "$line" ]; then
  echo "[ao-localnet-seal] could not parse ao.id|Owner from aos --run output." >&2
  echo "  rerun manually: aos $PID --legacy --gateway-url $GATE --cu-url $CU --mu-url $MU --run 'return tostring(ao.id) .. \"|\" .. tostring(Owner)'" >&2
  exit 1
fi
IFS='|' read -r AOID OWNER <<<"$line"
if [ "$AOID" != "$PID" ]; then
  echo "[ao-localnet-seal] sanity: ao.id ($AOID) != spawn pid ($PID). Aborting before writing receipt." >&2
  exit 1
fi
if [ -z "$AOID" ] || [ -z "$OWNER" ]; then
  echo "[ao-localnet-seal] empty ao.id / Owner from process; aborting." >&2
  exit 1
fi

echo "[ao-localnet-seal] writing receipt + STATE_CHAIN (replacing previous ledger) …"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
python3 "$ROOT/scripts/record_ao_seal_artifacts.py" \
  --process-id "$AOID" \
  --signer "$OWNER" \
  --message-id "$MSGID" \
  --reset-ledger

echo "[ao-localnet-seal] verifying (docker + CU must still be up) …"
export XION_AO_GATEWAY_URL="$CU"
export PYTHONPATH="$ROOT/xion-verify/src${PYTHONPATH:+:$PYTHONPATH}"
python3 -m xion_verify.cli ao-handlers
