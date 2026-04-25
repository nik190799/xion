#!/usr/bin/env bash
# @permaweb/aoconnect dist/index.js does:  var AO_URL = process.env.AO_URL = void 0;
# That clears the string sentinel `AO_URL=undefined` that @permaweb/aos uses to stay on
# legacy `readResult` (local CU). After import, aos sees AO_URL missing and flips to
# mainnet readResult → "Could not connect to process" on localnet.
#
# This patch only stops clobbering process.env; the local `var AO_URL = void 0` is kept.
# Idempotent. Run: bash scripts/patch-npm-aoconnect-preserve-ao-url.sh
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
MARKER="Xion-patched-preserve-ao-url"

F=""
if F_JS="$(node -e "
const fs = require('fs');
const p = require('path');
const roots = [];
try { roots.push(require('child_process').execSync('npm root -g', { encoding: 'utf8' }).trim()); } catch (e) {}
if (process.env.NVM_DIR) {
  const nv = p.join(process.env.NVM_DIR, 'versions', 'node');
  try {
    for (const v of fs.readdirSync(nv)) {
      roots.push(p.join(nv, v, 'lib', 'node_modules'));
    }
  } catch (e) {}
}
const cands = [];
for (const r of roots) {
  cands.push(p.join(r, '@permaweb', 'aos', 'node_modules', '@permaweb', 'aoconnect', 'dist', 'index.js'));
  cands.push(p.join(r, '@permaweb', 'aoconnect', 'dist', 'index.js'));
}
for (const c of cands) {
  if (fs.existsSync(c)) { console.log(c); process.exit(0); }
}
process.exit(1);
" 2>/dev/null)"; then
  F="$F_JS"
fi

if [ -z "$F" ] || [ ! -f "$F" ]; then
  echo "[patch-npm-aoconnect] could not find @permaweb/aoconnect dist/index.js (npm i -g @permaweb/aos?)" >&2
  exit 0
fi

if grep -qF "$MARKER" "$F" 2>/dev/null; then
  echo "[patch-npm-aoconnect] already applied: $F"
  exit 0
fi

command -v python3 >/dev/null 2>&1 || { echo "[patch-npm-aoconnect] need python3" >&2; exit 0; }

python3 - "$F" "$MARKER" <<'PY'
import pathlib, sys, time
path, marker = sys.argv[1:3]
p = pathlib.Path(path)
s = p.read_text(encoding="utf-8", errors="replace")
if marker in s:
    print("already applied:", path)
    sys.exit(0)
old = "var AO_URL = process.env.AO_URL = void 0;"
new = f"var AO_URL = void 0; // {marker}"
if old not in s:
    if "var AO_URL = void 0" in s and "process.env.AO_URL = void 0" not in s:
        print("OK (upstream already does not clobber process.env.AO_URL):", path)
        sys.exit(0)
    print("pattern_missing (unexpected aoconnect layout):", path, file=sys.stderr)
    sys.exit(0)
bak = p.with_name(p.name + f".bak.{time.time_ns()}.xion")
bak.write_text(s, encoding="utf-8")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("patched:", path)
PY
