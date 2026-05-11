"""Generate infra/akash/relay-deployment.live.yaml from the canonical SDL plus
the Chutes inference env vars sourced from repo-root .env.

Property promised: the canonical SDL in git stays secret-free; the .live.yaml
(gitignored) is the one passed to provider-services tx deployment create and
carries the inlined Chutes API key. The same key lands on-chain (Akash SDLs
are public on-chain), so operators should mint a scoped/capped Chutes key for
this deployment rather than using a high-limit production key.

This script is intentionally minimal: read canonical, find the
`XION_INFERENCE_POLICY=hosted_api_first` env line, inject five Chutes env
entries right after it, write to .live.yaml. No yaml parsing — keeps line-
order and comments byte-stable so the diff is reviewable.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_SDL = REPO_ROOT / "infra" / "akash" / "relay-deployment.yaml"
LIVE_SDL = REPO_ROOT / "infra" / "akash" / "relay-deployment.live.yaml"
ENV_FILE = REPO_ROOT / ".env"

CHUTES_BASE_URL_DEFAULT = "https://llm.chutes.ai/v1"
CHUTES_API_BASE_URL_DEFAULT = "https://api.chutes.ai"
CHUTES_MODEL_DEFAULT = "moonshotai/Kimi-K2.6-TEE"


def read_env_value(name: str) -> str | None:
    if not ENV_FILE.is_file():
        return None
    pattern = re.compile(rf"^{re.escape(name)}=(.*)$")
    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip().lstrip("﻿")
        if not line or line.startswith("#"):
            continue
        match = pattern.match(line)
        if not match:
            continue
        value = match.group(1).strip().strip("\r")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        return value
    return None


def main() -> int:
    chutes_key = read_env_value("XION_CHUTES_API_KEY") or read_env_value("CHUTES_API_KEY")
    if not chutes_key:
        print("generate-live-sdl: no XION_CHUTES_API_KEY / CHUTES_API_KEY in .env", file=sys.stderr)
        return 1
    chutes_base_url = read_env_value("XION_CHUTES_BASE_URL") or CHUTES_BASE_URL_DEFAULT
    chutes_api_base = read_env_value("XION_CHUTES_API_BASE_URL") or CHUTES_API_BASE_URL_DEFAULT
    chutes_model = read_env_value("XION_CHUTES_HOSTED_MODEL") or CHUTES_MODEL_DEFAULT

    text = CANONICAL_SDL.read_text(encoding="utf-8")
    marker = "      - XION_INFERENCE_POLICY=hosted_api_first"
    if marker not in text:
        print(f"generate-live-sdl: marker not found in {CANONICAL_SDL}", file=sys.stderr)
        return 2

    chutes_block = (
        f"\n      # Chutes/SN64 hosted inference — primary path under "
        f"hosted_api_first.\n"
        f"      # Inlined here for runtime registration of "
        f"ChutesGenerativeProvider.\n"
        f"      # On-chain visible: use a scoped/capped key, rotate after lease.\n"
        f"      - XION_CHUTES_API_KEY={chutes_key}\n"
        f"      - XION_CHUTES_BASE_URL={chutes_base_url}\n"
        f"      - XION_CHUTES_API_BASE_URL={chutes_api_base}\n"
        f"      - XION_CHUTES_HOSTED_MODEL={chutes_model}\n"
        f"      - XION_CHUTES_TEE_REQUIRED=true"
    )

    new_text = text.replace(marker, marker + chutes_block, 1)
    LIVE_SDL.write_text(new_text, encoding="utf-8", newline="\n")
    print(f"generate-live-sdl: wrote {LIVE_SDL.relative_to(REPO_ROOT)}")
    print(f"  Chutes key length: {len(chutes_key)} (prefix: {chutes_key[:8]}…)")
    print(f"  Chutes model:      {chutes_model}")
    print(f"  Chutes base URL:   {chutes_base_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
