#!/usr/bin/env bash
# Upstream ao-localnet services/cu/Dockerfile uses node:20; current ao/servers/cu (main) needs
# Promise.withResolvers (Node 22+). Without this, CU logs: "Promise.withResolvers is not a function"
# and aos fails with "Could not connect to process".
set -euo pipefail
script_dir() {
  local src="${BASH_SOURCE[0]}"
  while [ -h "$src" ]; do
    local d
    d="$(cd -P "$(dirname "$src")" && pwd)"
    src="$(readlink "$src")"
    [[ "$src" != /* ]] && src="$d/$src"
  done
  cd -P "$(dirname "$src")" && pwd
}
ROOT="$(cd "$(script_dir)/.." && pwd)"
UPSTREAM="${XION_AO_LOCALNET_UPSTREAM_DIR:-$ROOT/infra/ao-localnet/.upstream}"
F="$UPSTREAM/services/cu/Dockerfile"
[ -f "$F" ] || { echo "[patch-cu-node22] missing $F"; exit 0; }
command -v python3 >/dev/null 2>&1 || { echo "[patch-cu-node22] need python3"; exit 0; }
python3 - "$F" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
s = p.read_text(encoding="utf-8", errors="replace")
if "FROM node:20-alpine" not in s:
    print(f"[patch-cu-node22] skip (no node:20): {p}")
    sys.exit(0)
n = s.replace("FROM node:20-alpine", "FROM node:22-alpine")
if not n.lstrip().startswith("# Xion:"):
    n = "# Xion: Node 22+ — ao/servers/cu main uses Promise.withResolvers (see patch-ao-localnet-cu-node22.sh)\n" + n
p.write_text(n, encoding="utf-8")
print(f"[patch-cu-node22] patched {p}")
sys.exit(2)
PY
rc=$?
if [ "$rc" -eq 2 ]; then
  echo "[patch-cu-node22] Rebuild: docker compose -f infra/ao-localnet/docker-compose.yaml build cu && ... up -d cu"
  exit 2
fi
exit 0
