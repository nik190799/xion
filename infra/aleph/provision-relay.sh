#!/usr/bin/env bash
# Xion Relay provisioning for an Aleph Cloud instance (Ubuntu rootfs).
#
# Executed over SSH by xion_ops.deployers.relay_aleph (or manually:
#   ssh root@<vm> 'bash -s' < infra/aleph/provision-relay.sh).
# Idempotent: safe to re-run. Mirrors the env contract of
# infra/akash/relay-deployment-cpu-only.yaml.
set -euo pipefail

IMAGE="${XION_RELAY_IMAGE:-nikhilkadalge/xion-relay:pre-genesis-akash-wall120}"
NAME=xion-relay

if ! command -v docker >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y docker.io
  systemctl enable --now docker
fi

docker pull "$IMAGE"
docker rm -f "$NAME" 2>/dev/null || true
docker run -d --name "$NAME" --restart unless-stopped \
  -p 8443:8443 \
  -e XION_API_HOST=0.0.0.0 \
  -e XION_API_PORT=8443 \
  -e XION_API_WORKERS=1 \
  -e XION_API_REQUIRE_BEARER=false \
  -e XION_BILLING_REQUIRED=false \
  -e XION_CAST_POOL_ON_BOOT=false \
  -e XION_CHAT_DEADLINE_S=120 \
  -e XION_COGNITION_WALL_S=120 \
  -e XION_INFERENCE_POLICY=hosted_api_first \
  -e XION_PAYMENT_LEDGER=/app/data/PAYMENT_LEDGER.jsonl \
  -e XION_SENSORIUM_LEDGER=/app/data/SENSORIUM_LEDGER.jsonl \
  -e XION_SAFETY_LEDGER=/app/data/SAFETY_LEDGER.jsonl \
  -e XION_REQUEST_LEDGER=/app/data/REQUEST_LEDGER.jsonl \
  -e XION_ANCHOR_DB_PATH=/app/data/ANCHOR_LEDGER.jsonl \
  "$IMAGE" /bin/sh -lc 'exec /usr/local/bin/entrypoint-xion-orchestrator-api.sh'

sleep 5
curl -fsS --max-time 20 http://127.0.0.1:8443/health && echo "" && echo "provision-relay: OK"
