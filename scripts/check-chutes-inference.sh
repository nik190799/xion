#!/usr/bin/env bash
# Read Chutes key from repo-root .env (strip CRLF if Windows), then probe inference endpoint.
set -u
REPO_ENV="$(cd "$(dirname "$0")/.." && pwd)/.env"
CK="$(grep -E '^(CHUTES_API_KEY|XION_CHUTES_API_KEY)=' "$REPO_ENV" | head -1 | cut -d= -f2- | tr -d '\r\n')"
echo "key_len=${#CK} prefix=${CK:0:10}…"
echo "--- GET /v1/models ---"
curl -sS --max-time 30 -o /tmp/chutes_models.json -w "HTTP %{http_code} (%{time_total}s)\n" \
  -H "Authorization: Bearer ${CK}" \
  https://llm.chutes.ai/v1/models
echo "--- response head ---"
head -c 600 /tmp/chutes_models.json
echo
echo "--- POST /v1/chat/completions Kimi-K2.6-TEE one-token ---"
curl -sS --max-time 60 -o /tmp/chutes_chat.json -w "HTTP %{http_code} (%{time_total}s)\n" \
  -X POST https://llm.chutes.ai/v1/chat/completions \
  -H "Authorization: Bearer ${CK}" \
  -H "Content-Type: application/json" \
  -d '{"model":"moonshotai/Kimi-K2.6-TEE","messages":[{"role":"user","content":"Reply with exactly one short word."}],"max_tokens":10}'
echo "--- response head ---"
head -c 600 /tmp/chutes_chat.json
