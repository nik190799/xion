#!/usr/bin/env bash
# Build the Relay image from git archive (same extraction layout as
# `xion-verify rebuild`) and push to GitHub Container Registry.
#
# Prerequisite auth:
#   echo "$GITHUB_TOKEN" | docker login ghcr.io -u GITHUB_USERNAME --password-stdin
# Use a classic PAT or fine-grained token with write:packages (and read:packages).
#
# Override defaults:
#   GHCR_IMAGE=ghcr.io/myorg/xion-relay GHCR_TAG=mytag bash scripts/push-relay-ghcr.sh
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

SHA="$(git rev-parse HEAD)"
ORIGIN="$(git remote get-url origin 2>/dev/null || true)"
OWNER="local"
if [[ "$ORIGIN" =~ github\.com[:/]([^/]+)/ ]]; then
  OWNER="${BASH_REMATCH[1]}"
fi

IMAGE="${GHCR_IMAGE:-ghcr.io/${OWNER}/xion-relay}"
TAG="${GHCR_TAG:-pre-genesis-akash}"

TMP="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP"
}
trap cleanup EXIT

mkdir -p "$TMP/xion-os"
git archive "$SHA" | tar -x -C "$TMP/xion-os"

echo "Building ${IMAGE}:${TAG} from git ${SHA} (xion-verify rebuild layout)..."
docker build --provenance=false -t "${IMAGE}:${TAG}" "$TMP/xion-os"

echo "Pushing ${IMAGE}:${TAG} ..."
docker push "${IMAGE}:${TAG}"

echo "OK — update infra/akash/relay-deployment.yaml if IMAGE or TAG differs from:"
echo "  image: ${IMAGE}:${TAG}"
