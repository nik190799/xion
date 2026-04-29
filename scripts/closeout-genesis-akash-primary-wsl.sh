#!/usr/bin/env bash
# Complete substrate dry-run (Chutes as genesis secondary) and refresh the
# Akash-primary row in ledgers/RELAY_REGISTRY.json. Run from repo root in WSL.
#
# Required:
#   XION_AKASH_HTTPS_BASE   — https://lease-host:port  (no trailing slash)
#
# Chutes /health uses Bearer; provide either chutes.env or a bearer:
#   XION_CHUTES_SECRETS_FILE — default: /mnt/c/Users/16823/Documents/xion/xion-secrets/chutes.env
#   XION_SECONDARY_HEALTH_BEARER — overrides CHUTES_API_KEY
#
# Optional: CHUTE_PUBLIC_URL, XION_DEPLOYMENT_EVIDENCE, XION_*_STATE_TIP
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

AKASH_BASE="${XION_AKASH_HTTPS_BASE:-}"
if [[ -z "$AKASH_BASE" ]]; then
  echo "closeout: set XION_AKASH_HTTPS_BASE (see docs/runbooks/AKASH_RELAY_DEPLOY.md)" >&2
  exit 2
fi

SECRETS="${XION_CHUTES_SECRETS_FILE:-/mnt/c/Users/16823/Documents/xion/xion-secrets/chutes.env}"
if [[ -f "$SECRETS" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$SECRETS"
  set +a
fi

if [[ -z "${XION_SECONDARY_HEALTH_BEARER:-${CHUTES_API_KEY:-}}" ]]; then
  echo "closeout: need CHUTES_API_KEY in secrets or XION_SECONDARY_HEALTH_BEARER" >&2
  exit 2
fi

export XION_SECONDARY_SUBSTRATE_ID="${XION_SECONDARY_SUBSTRATE_ID:-chutes-d3-standby}"
export XION_SECONDARY_PROVIDER=chutes
CHUTE_URL="${CHUTE_PUBLIC_URL:-https://nikhilkadalge-xion-relay-pre-genesis-d3.chutes.ai}"
export XION_SECONDARY_HEALTH_URL="${CHUTE_URL}/health"
export XION_DEPLOYMENT_EVIDENCE="${XION_DEPLOYMENT_EVIDENCE:-chutes://89866bfc-5ddd-5382-b887-116d8901808f/98f0cdf3-e8a0-461d-8a75-a4d3240e0389}"
TIP="${XION_PRIMARY_STATE_TIP:-local-pre-genesis-tip}"
export XION_PRIMARY_STATE_TIP="$TIP"
export XION_SECONDARY_STATE_TIP="${XION_SECONDARY_STATE_TIP:-$TIP}"
export XION_SECONDARY_HEALTH_BEARER="${XION_SECONDARY_HEALTH_BEARER:-$CHUTES_API_KEY}"

bash scripts/substrate-portability-dry-run.sh

export CLOSEOUT_AKASH_BASE="$AKASH_BASE"
python3 -c "
import json, os, time, hashlib
from pathlib import Path
reg = Path('ledgers/RELAY_REGISTRY.json')
data = json.loads(reg.read_text(encoding='utf-8'))
base = os.environ['CLOSEOUT_AKASH_BASE'].rstrip('/')
data['relays'][0]['endpoint'] = base
data['relays'][0]['last_seen_utc_ns'] = time.time_ns()
data['as_of_utc_ns'] = time.time_ns()
body = {k: v for k, v in data.items() if k != 'payload_sha256'}
data['payload_sha256'] = hashlib.sha256(
    json.dumps(body, sort_keys=True, separators=(',', ':')).encode()
).hexdigest()
reg.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print('closeout: updated', reg)
"
echo "Next:  xion-verify discovery && xion-verify substrate-portability"
echo "        (or: python -m xion_verify.cli discovery from xion-verify package path)"
