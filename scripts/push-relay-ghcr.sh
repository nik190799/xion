#!/usr/bin/env bash
# Build the Relay image from git archive (same extraction layout as
# `xion-verify rebuild`) and push to a registry.
#
# Important: extract into "$TMP/xion-os" (not the archive root alone). Docker BuildKit
# can emit a different image ID when the build context directory path/layout differs;
# matching `xion-verify rebuild` + genesis/RELAY_IMAGE_DIGEST.txt requires this layout.
#
# Modes (first match wins):
#   1) RELAY_PUSH_IMAGE=name:tag — build and push this single reference (any registry).
#   2) DOCKERHUB_USER=you — push to docker.io/you/xion-relay:TAG (needs `docker login`).
#   3) Default — GHCR ghcr.io/<github-owner>/xion-relay:TAG (needs PAT + docker login ghcr.io).
#
# Examples:
#   RELAY_PUSH_IMAGE=nikhilkadalge/xion-relay:pre-genesis-akash bash scripts/push-relay-ghcr.sh
#   DOCKERHUB_USER=nikhilkadalge bash scripts/push-relay-ghcr.sh
#   echo "$GITHUB_TOKEN" | docker login ghcr.io -u USER --password-stdin && bash scripts/push-relay-ghcr.sh
#
# Override tag for modes 2–3: GHCR_TAG=mytag
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

SHA="$(git rev-parse HEAD)"
TAG="${GHCR_TAG:-pre-genesis-akash}"

TMP="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP"
}
trap cleanup EXIT

mkdir -p "$TMP/xion-os"
git archive "$SHA" | tar -x -C "$TMP/xion-os"

if [[ -n "${RELAY_PUSH_IMAGE:-}" ]]; then
  REF="$RELAY_PUSH_IMAGE"
elif [[ -n "${DOCKERHUB_USER:-}" ]]; then
  REF="docker.io/${DOCKERHUB_USER}/xion-relay:${TAG}"
else
  ORIGIN="$(git remote get-url origin 2>/dev/null || true)"
  OWNER="local"
  if [[ "$ORIGIN" =~ github\.com[:/]([^/]+)/ ]]; then
    OWNER="${BASH_REMATCH[1]}"
  fi
  IMAGE="${GHCR_IMAGE:-ghcr.io/${OWNER}/xion-relay}"
  REF="${IMAGE}:${TAG}"
fi

echo "Building ${REF} from git ${SHA} (xion-verify rebuild layout)..."
docker build --provenance=false -t "${REF}" "$TMP/xion-os"

echo "Pushing ${REF} ..."
docker push "${REF}"

echo "OK — ensure infra/akash/relay-deployment.yaml matches:"
echo "  image: ${REF}"
