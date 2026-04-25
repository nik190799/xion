#!/usr/bin/env bash
# Patch upstream ao-localnet MU: `getProcess()` can cache (or fetch) process tags
# without a `Scheduler` tag on ArLocal. GraphQL for the same `processId` has full
# tags. `locate()` then throws "No Scheduler tag found on process ...".
#
# Upstream ao-localnet only has services/mu/Dockerfile; MU source is cloned inside
# the image from permaweb/ao. This script:
#   1) Fetches servers/mu/.../schedulerLocations.js from ao (raw GitHub or
#      XION_MU_SCHEDULERLOC_TARGET),
#   2) Inserts ensureProcessHasSchedulerTag() and wraps getProcess returns,
#   3) Writes services/mu/schedulerLocations.xion.js and injects COPY into Dockerfile.
#
# Idempotent. Run from: scripts/ao-localnet-up.sh (after upstream is pinned).
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
MU_SVC="$UPSTREAM/services/mu"
OVERLAY="$MU_SVC/schedulerLocations.xion.js"
DOCKERFILE="$MU_SVC/Dockerfile"
RAW_URL="${XION_MU_SCHEDULERLOC_RAW_URL:-https://raw.githubusercontent.com/permaweb/ao/main/servers/mu/src/domain/clients/schedulerLocations.js}"
MARKER="Xion-ensureProcessHasSchedulerTag"
DF_MARKER="# Xion: schedulerLocations GraphQL fallback"

if [ ! -f "$DOCKERFILE" ]; then
  echo "[patch-ao-localnet-mu-graphql-fallback] no MU Dockerfile at $DOCKERFILE (skip)" >&2
  exit 0
fi

TMP="${TMPDIR:-/tmp}/xion-mu-scheduler-src.$$"
trap 'rm -f "$TMP"' EXIT

if [ -n "${XION_MU_SCHEDULERLOC_TARGET:-}" ] && [ -f "$XION_MU_SCHEDULERLOC_TARGET" ]; then
  cp -- "${XION_MU_SCHEDULERLOC_TARGET}" "$TMP"
elif command -v curl >/dev/null 2>&1; then
  if ! curl -fsSL "$RAW_URL" -o "$TMP"; then
    echo "[patch-ao-localnet-mu-graphql-fallback] curl failed for $RAW_URL (skip)" >&2
    exit 0
  fi
else
  echo "[patch-ao-localnet-mu-graphql-fallback] need curl or XION_MU_SCHEDULERLOC_TARGET (skip)" >&2
  exit 0
fi

command -v python3 >/dev/null 2>&1 || { echo "[patch-ao-localnet-mu-graphql-fallback] python3 not in PATH; skip" >&2; exit 0; }

python3 - "$TMP" "$OVERLAY" "$DOCKERFILE" "$MARKER" "$DF_MARKER" <<'PY'
import pathlib
import sys

src_path, overlay_path, dockerfile_path, marker, df_marker = sys.argv[1:6]
overlay_p = pathlib.Path(overlay_path)
docker_p = pathlib.Path(dockerfile_path)

s = pathlib.Path(src_path).read_text(encoding="utf-8").replace("\r\n", "\n")
if marker in s:
    out = s
else:
    helper = r"""
    // Xion-ensureProcessHasSchedulerTag: ArLocal / gateway can expose process data without a `Scheduler` tag; GQL is canonical.
    async function ensureProcessHasSchedulerTag (process, processId) {
      if (!process || !Array.isArray(process.tags)) return process
      if (process.tags.find((t) => t.name === 'Scheduler')) return process
      if (!GRAPHQL_URL) return process
      for (let attempt = 0; attempt < 50; attempt++) {
        try {
          const gRes = await fetch(GRAPHQL_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              query: 'query ($id: ID!) { transaction(id: $id) { tags { name value } } }',
              variables: { id: processId }
            })
          })
          const gJson = await gRes.json()
          const gqlTags = gJson?.data?.transaction?.tags
          if (Array.isArray(gqlTags) && gqlTags.some((t) => t.name === 'Scheduler')) {
            const fixed = { id: processId, tags: gqlTags }
            await db.run({
              sql: `INSERT OR REPLACE INTO ${PROCESSES_TABLE} (processId, processData) VALUES (?, ?)`,
              parameters: [processId, JSON.stringify(fixed)]
            })
            schedLogger({ log: `Xion: merged GraphQL tags for process ${processId}` })
            return fixed
          }
        } catch (_e) {}
        await new Promise((r) => setTimeout(r, 80 * (attempt + 1)))
      }
      return process
    }

"""
    jpart = """    /**
     * Fetch a process from Arweave and enumerate the HTTP response
     * headers as tags. Results are cached in the processes table.
     *
     * @param {string} processId - the Arweave transaction id of the process
     * @returns {Promise<{ id: string, tags: Array<{ name: string, value: string }> } | undefined>}
     */
    async function getProcess (processId) {"""

    anchor = "    ])\n\n" + jpart
    if anchor not in s:
        print(
            "[patch-ao-localnet-mu-graphql-fallback] getProcess anchor not found; ao/mu layout changed; skip",
            file=sys.stderr,
        )
        sys.exit(0)

    s = s.replace(anchor, "    ])\n" + helper + jpart, 1)

    old_cached = """      if (cached.length) {
        return JSON.parse(cached[0].processData)
      }"""
    new_cached = """      if (cached.length) {
        return await ensureProcessHasSchedulerTag(JSON.parse(cached[0].processData), processId)
      }"""
    if old_cached in s:
        s = s.replace(old_cached, new_cached, 1)
    else:
        print(
            "[patch-ao-localnet-mu-graphql-fallback] warn: cached-return pattern not found; partial patch",
            file=sys.stderr,
        )

    old_final = """      schedLogger({ log: `Fetched and cached process ${processId}` })

      return process
    }"""
    new_final = """      schedLogger({ log: `Fetched and cached process ${processId}` })

      return await ensureProcessHasSchedulerTag(process, processId)
    }"""
    if old_final in s:
        s = s.replace(old_final, new_final, 1)
    else:
        print(
            "[patch-ao-localnet-mu-graphql-fallback] warn: final-return pattern not found; partial patch",
            file=sys.stderr,
        )

    out = s

prev = overlay_p.read_text(encoding="utf-8") if overlay_p.is_file() else None
if prev == out:
    print(f"[patch-ao-localnet-mu-graphql-fallback] already up to date: {overlay_p}")
else:
    overlay_p.parent.mkdir(parents=True, exist_ok=True)
    overlay_p.write_text(out, encoding="utf-8")
    print(f"[patch-ao-localnet-mu-graphql-fallback] patched {overlay_p}")

df = docker_p.read_text(encoding="utf-8").replace("\r\n", "\n")
copy_line = "COPY schedulerLocations.xion.js src/domain/clients/schedulerLocations.js"
if df_marker in df or copy_line in df:
    pass
else:
    lines = df.split("\n")
    out_lines = []
    inserted = False
    for line in lines:
        out_lines.append(line)
        if not inserted and line.strip() == "WORKDIR /usr/app":
            out_lines.append("")
            out_lines.append(f"{df_marker} (ArLocal)")
            out_lines.append(copy_line)
            inserted = True
    if not inserted:
        print(
            "[patch-ao-localnet-mu-graphql-fallback] warn: WORKDIR /usr/app not found; add COPY manually",
            file=sys.stderr,
        )
    else:
        docker_p.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        print(f"[patch-ao-localnet-mu-graphql-fallback] injected Dockerfile overlay in {docker_p}")
PY
