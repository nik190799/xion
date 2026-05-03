"""Chutes operational service.

Upstream ``chutes`` CLI (e.g. 0.6.x) has no ``--yes`` / ``--json`` on ``build`` / ``deploy`` / ``chutes delete``:
it uses ``input()`` for confirmations. For CI and headless shells set ``CI=1`` or
``XION_CHUTES_NONINTERACTIVE=1`` so xion_ops feeds answers on stdin (``y`` for deploy/delete; for remote
``build`` defaults to ``n`` then ``y`` when the CLI asks whether to list all context files, then confirm
upload — override with ``XION_CHUTES_NONINTERACTIVE_BUILD_STDIN`` if your image has few context files).

**Timing vs https://chutes.ai/docs/cli/manage (`build → deploy → warmup`):**

- ``chutes build … --wait`` runs until completion (no documented second cap); subprocess timeout is omitted
  unless ``XION_CHUTES_BUILD_CMD_TIMEOUT_SEC`` caps CI jobs.
- The SDK’s warmup path polls for instances with ``max_wait=600`` seconds; cord polling defaults to the same
  order (**600**) via ``XION_CHUTES_WARMUP_MAX_WAIT_SEC``.
- ``chutes warmup`` subprocess default **660** s (600 + 60 slack) aligns with staying above that SDK ceiling;
  tune with ``XION_CHUTES_PLATFORM_WARMUP_TIMEOUT_SEC``.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from xion_ops.commands import run_command
from xion_ops.services.base import OpsService
from xion_ops.types import BalanceReport, CommandResult, DeploymentResult, ServiceHealth, WalletInfo
from xion_ops.wallets import wallets_for_service

DEFAULT_CHUTE_REF = "xion_relay_chute:chute"
DEFAULT_VERIFY_MODULE_REL = "xion_relay_chute.py"

# Bundled Chutes SDK (e.g. 0.6.x): poll_for_instances(..., max_wait=600.0) in chutes.entrypoint.warmup.
CHUTES_SDK_POLL_INSTANCES_MAX_WAIT_SEC = 600.0
CHUTES_CLI_WARMUP_SUBPROCESS_DEFAULT_SEC = CHUTES_SDK_POLL_INSTANCES_MAX_WAIT_SEC + 60.0


def normalize_chute_ref(ref: str) -> str:
    """Map ``module.py`` to ``module:chute``; pass through ``module:obj`` unchanged."""

    s = ref.strip()
    if not s:
        return DEFAULT_CHUTE_REF
    if ":" in s:
        return s
    name = Path(s).name
    if name.endswith(".py"):
        return f"{name[:-3]}:chute"
    return s


def verify_module_relative_path(chute_ref_or_path: str) -> str:
    """Relative path under the repo for :func:`verify_import` (exec on disk)."""

    s = chute_ref_or_path.strip()
    if not s:
        return DEFAULT_VERIFY_MODULE_REL
    if ":" in s:
        mod, _, _ = s.partition(":")
        mod = mod.strip()
        return mod if mod.endswith(".py") else f"{mod}.py"
    return s


def chutes_cli_noninteractive() -> bool:
    ci = os.environ.get("CI", "").strip().lower()
    if ci in ("1", "true", "yes"):
        return True
    ni = os.environ.get("XION_CHUTES_NONINTERACTIVE", "").strip().lower()
    return ni in ("1", "true", "yes")


def _stdin_for_chutes_subcommand(subcommand: str) -> str | None:
    if not chutes_cli_noninteractive():
        return None
    if subcommand == "deploy":
        return "y\n"
    if subcommand == "build":
        return os.environ.get("XION_CHUTES_NONINTERACTIVE_BUILD_STDIN", "n\ny\n")
    if subcommand == "delete":
        return "y\n"
    return None


def combined_command_output(result: CommandResult) -> str:
    return ((result.stdout or "") + "\n" + (result.stderr or "")).strip()


_UUID_RE = r"[a-fA-F0-9]{8}-(?:[a-fA-F0-9]{4}-){3}[a-fA-F0-9]{12}"


def parse_chutes_deploy_output(text: str) -> dict[str, str | None]:
    """Pull metadata from CLI loguru success lines and any JSON payloads."""

    chute_id = None
    version = None

    mj = re.search(rf"\bchute_id=(?P<id>{_UUID_RE})\b", text)
    if not mj:
        mj = re.search(rf"'chute_id':\s*'(?P<id>{_UUID_RE})'", text)
    if mj:
        chute_id = mj.group("id")

    mv = re.search(r"\bversion=(?P<v>[a-fA-F0-9\-]{8,})", text)
    if not mv:
        mv = re.search(r"'version':\s*'(?P<v>[^']+)'", text)
    if mv:
        version = mv.group("v").strip()

    try:
        payload: Any = json.loads(text.strip())
        if isinstance(payload, dict):
            cid = payload.get("chute_id")
            if isinstance(cid, str) and not chute_id:
                chute_id = cid
            ver = payload.get("version")
            if isinstance(ver, str) and not version:
                version = ver
    except json.JSONDecodeError:
        pass

    return {"chute_id": chute_id, "version": version, "url": _extract_url(text)}


def _chutes_optional_bearer_headers() -> dict[str, str]:
    token = os.environ.get("CHUTES_API_KEY") or os.environ.get("XION_CHUTES_API_KEY")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _optional_positive_int_timeout(env_name: str) -> int | None:
    """Parse a positive subprocess timeout from env (seconds); unset → None (unbounded)."""

    raw = os.environ.get(env_name)
    if raw is None or not str(raw).strip():
        return None
    try:
        val = int(float(str(raw).strip()))
    except ValueError:
        return None
    return val if val > 0 else None


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip())
    except ValueError:
        return default


def _repo_root_wsl_path(repo_root: Path) -> str:
    """Map a Windows repo path to a WSL `/mnt/<drive>/...` path for bash -lc."""

    resolved = repo_root.resolve()
    s = str(resolved)
    if len(s) >= 2 and s[1] == ":" and s[0].isalpha():
        drive = s[0].lower()
        tail = s[2:].replace("\\", "/")
        return f"/mnt/{drive}{tail}"
    return s.replace("\\", "/")


class ChutesService(OpsService):
    name = "chutes"

    def _invoke_chutes_cli(
        self, argv: list[str], *, timeout: int | None = None, stdin: str | None = None
    ) -> CommandResult:
        """Prefer host ``chutes``; on Windows without it, run via WSL (pipx/local install)."""

        stdin_effective = stdin
        if stdin_effective is None and argv:
            stdin_effective = _stdin_for_chutes_subcommand(argv[0])

        if shutil.which("chutes"):
            return run_command(
                ["chutes", *argv], cwd=self.repo_root, check=False, timeout=timeout, stdin=stdin_effective
            )
        if sys.platform == "win32":
            wsl_repo = _repo_root_wsl_path(self.repo_root)
            rendered = " ".join(shlex.quote(part) for part in ["chutes", *argv])
            shell_parts = [
                f"cd {shlex.quote(wsl_repo)}",
                'export PATH="$HOME/.local/bin:$HOME/bin:$PATH"',
            ]
            for key in ("CHUTES_API_KEY", "XION_CHUTES_API_KEY"):
                val = os.environ.get(key)
                if val:
                    shell_parts.append(f"export {key}={shlex.quote(val)}")
            shell_parts.append(rendered)
            shell_line = " && ".join(shell_parts)
            return run_command(
                ["wsl", "bash", "-lc", shell_line],
                cwd=self.repo_root,
                check=False,
                timeout=timeout,
                stdin=stdin_effective,
            )

        return run_command(
            ["chutes", *argv], cwd=self.repo_root, check=False, timeout=timeout, stdin=stdin_effective
        )

    def _invoke_chutes_managed_cli(
        self, argv: list[str], *, timeout: int | None = None, stdin: str | None = None
    ) -> CommandResult:
        """Run ``chutes chutes <command>…`` (list/get/delete miners)."""

        stdin_effective = stdin
        if stdin_effective is None and argv:
            stdin_effective = _stdin_for_chutes_subcommand(argv[0])

        if shutil.which("chutes"):
            return run_command(
                ["chutes", "chutes", *argv],
                cwd=self.repo_root,
                check=False,
                timeout=timeout,
                stdin=stdin_effective,
            )
        if sys.platform == "win32":
            wsl_repo = _repo_root_wsl_path(self.repo_root)
            rendered = " ".join(shlex.quote(part) for part in ["chutes", "chutes", *argv])
            shell_parts = [
                f"cd {shlex.quote(wsl_repo)}",
                'export PATH="$HOME/.local/bin:$HOME/bin:$PATH"',
            ]
            for key in ("CHUTES_API_KEY", "XION_CHUTES_API_KEY"):
                val = os.environ.get(key)
                if val:
                    shell_parts.append(f"export {key}={shlex.quote(val)}")
            shell_parts.append(rendered)
            shell_line = " && ".join(shell_parts)
            return run_command(
                ["wsl", "bash", "-lc", shell_line],
                cwd=self.repo_root,
                check=False,
                timeout=timeout,
                stdin=stdin_effective,
            )

        return run_command(
            ["chutes", "chutes", *argv],
            cwd=self.repo_root,
            check=False,
            timeout=timeout,
            stdin=stdin_effective,
        )

    def addresses(self) -> list[WalletInfo]:
        registry = self.repo_root / "genesis" / "FUNDING_TARGETS.json"
        if not registry.exists():
            return []
        return wallets_for_service(self.name, registry)

    def balances(self) -> list[BalanceReport]:
        reports: list[BalanceReport] = []
        for wallet in self.addresses():
            try:
                balance = self.credit_balance()
                status = "ok" if balance >= wallet.target else ("zero" if balance == 0 else "shortfall")
                reports.append(BalanceReport(wallet=wallet, balance=balance, raw_balance=str(balance), status=status))
            except Exception as exc:
                reports.append(BalanceReport(wallet=wallet, balance=None, status="unknown", message=str(exc)))
        return reports

    def _cord_get_status(self, base: str, path: str, *, timeout_s: float = 20.0) -> tuple[bool, str, int | None]:
        """HTTP GET ``base``+``path``; return (success_2xx, message_or_body_snippet, http_status_or_none)."""
        absolute = base.rstrip("/") + path
        headers = _chutes_optional_bearer_headers()
        req = Request(absolute, headers=headers or {})
        try:
            with urlopen(req, timeout=timeout_s) as response:
                status = int(response.status)
                body = response.read(8192).decode("utf-8", errors="replace")
                ok = 200 <= status < 300
                return ok, body[:2048], status
        except HTTPError as exc:
            return False, getattr(exc, "reason", str(exc)) or str(exc.code), exc.code
        except URLError as exc:
            return False, str(exc.reason if hasattr(exc, "reason") else exc), None
        except Exception as exc:  # pragma: no cover — defensive parity with legacy health()
            return False, str(exc), None

    def health(self, url: str | None = None) -> ServiceHealth:
        target = url or os.environ.get("XION_CHUTES_HEALTH_URL") or self.base_url()
        if not target:
            return ServiceHealth(service=self.name, ok=False, message="no Chutes URL configured")
        ok, snippet, status = self._cord_get_status(target, "/health")
        return ServiceHealth(
            service=self.name,
            ok=ok,
            message="" if ok else (snippet[:512] if snippet else "health_check_failed"),
            details={"url": target, "status": status, "bearer": bool(_chutes_optional_bearer_headers())},
        )

    def credit_balance(self) -> float:
        api_url = os.environ.get("XION_CHUTES_CREDITS_URL")
        token = os.environ.get("CHUTES_API_KEY") or os.environ.get("XION_CHUTES_API_KEY")
        if not api_url:
            return 0.0
        request = Request(api_url, headers={"Authorization": f"Bearer {token}"} if token else {})
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return float(payload.get("balance") or payload.get("credits") or payload.get("balance_usd") or 0)

    def verify_cords(self, url: str | None = None) -> DeploymentResult:
        """Require ``GET /health``, ``GET /quote``, ``GET /self`` — matches public cords in ``xion_relay_chute.py``.

        When the Chutes gateway requires authentication, set ``CHUTES_API_KEY`` or
        ``XION_CHUTES_API_KEY`` so Bearer is attached (see ``docs/runbooks/CHUTES_RELAY_DEPLOY.md``).
        """
        target = url or self.base_url()
        if not target:
            return DeploymentResult(
                service=self.name,
                ok=False,
                url="",
                details={"error": "no Chutes URL configured (pass url arg or XION_CHUTES_BASE_URL)"},
            )
        cord_paths = ("/health", "/quote", "/self")
        per_path: dict[str, dict[str, object]] = {}
        all_ok = True
        used_bearer = bool(_chutes_optional_bearer_headers())
        for cord in cord_paths:
            ok_p, snippet, status = self._cord_get_status(target, cord)
            per_path[cord] = {"ok": ok_p, "status": status, "body_prefix": snippet[:512]}
            if not ok_p:
                all_ok = False
        return DeploymentResult(
            service=self.name,
            ok=all_ok,
            url=target,
            details={
                "cords": per_path,
                "bearer_attached": used_bearer,
                "result": "all cords green" if all_ok else "one or more cords failed",
            },
        )

    def warmup_until_cords_green(
        self,
        url: str | None = None,
        *,
        max_wait_seconds: float | None = None,
        interval_seconds: float | None = None,
        platform_warmup_slug: str | None = None,
    ) -> DeploymentResult:
        """Poll ``verify_cords`` until all paths are 2xx or ``max_wait_seconds`` elapses.

        Optionally run the platform ``chutes warmup <slug>`` subprocess once before
        polling (helps cold GPU miners per Chutes operator runbooks).

        Cord poll deadline defaults align with upstream ``poll_for_instances(..., max_wait=600)``
        (Chutes SDK ``chutes.entrypoint.warmup``). Tune with:

        - ``XION_CHUTES_WARMUP_MAX_WAIT_SEC`` (default **600**, same order as SDK instance poll ceiling),
        - ``XION_CHUTES_WARMUP_INTERVAL_SEC`` (default **15**),
        - ``XION_CHUTES_PLATFORM_WARMUP_TIMEOUT_SEC`` (default **660** seconds for ``chutes warmup``, ≥ SDK 600).

        Mirrors the historical ``MODE=live`` shell verifier semantics: Bearer from
        ``CHUTES_API_KEY`` / ``XION_CHUTES_API_KEY``.
        """

        target = url or self.base_url()
        if not target:
            return DeploymentResult(
                service=self.name,
                ok=False,
                url="",
                details={"error": "no Chutes URL configured (pass url arg or XION_CHUTES_BASE_URL)"},
            )

        max_w = (
            float(max_wait_seconds)
            if max_wait_seconds is not None
            else _float_env("XION_CHUTES_WARMUP_MAX_WAIT_SEC", CHUTES_SDK_POLL_INSTANCES_MAX_WAIT_SEC)
        )
        step = (
            float(interval_seconds)
            if interval_seconds is not None
            else _float_env("XION_CHUTES_WARMUP_INTERVAL_SEC", 15.0)
        )
        step = max(1.0, step)
        max_w = max(0.0, max_w)

        extra_details: dict[str, Any] = {}
        slug = platform_warmup_slug or os.environ.get("XION_CHUTES_WARMUP_SLUG") or ""
        slug = slug.strip()
        if slug:
            plat = self.chutes_cli_platform_warmup(slug)
            extra_details.update(
                {
                    "platform_warmup_slug": slug,
                    "platform_warmup_ok": plat.ok,
                    "platform_warmup": plat.details,
                }
            )

        started = time.monotonic()
        deadline = started + max_w
        attempts = 0
        last_verify: DeploymentResult | None = None

        while True:
            attempts += 1
            last_verify = self.verify_cords(target)
            if last_verify.ok:
                d = dict(last_verify.details)
                d.update(extra_details)
                return DeploymentResult(
                    service=self.name,
                    ok=True,
                    url=target,
                    details={
                        **d,
                        "attempts": attempts,
                        "elapsed_s": round(time.monotonic() - started, 3),
                        "warmup_strategy": "verify_cords_poll",
                    },
                )
            if time.monotonic() >= deadline:
                break
            nap = min(step, max(0.01, deadline - time.monotonic()))
            if nap <= 0:
                break
            time.sleep(nap)

        cords = dict(last_verify.details["cords"]) if last_verify and "cords" in last_verify.details else {}
        err_body: dict[str, Any] = {
            **extra_details,
            "attempts": attempts,
            "elapsed_s": round(time.monotonic() - started, 3),
            "max_wait_seconds": max_w,
            "interval_seconds": step,
            "last_cords": cords,
            "result": "timeout waiting for all cords green",
        }
        if last_verify is not None:
            err_body["bearer_attached"] = last_verify.details.get("bearer_attached")
        return DeploymentResult(service=self.name, ok=False, url=target, details=err_body)

    def verify_import(self, module_path: str = DEFAULT_VERIFY_MODULE_REL) -> DeploymentResult:
        path = self.repo_root / module_path
        old_path = list(sys.path)
        try:
            sys.path.insert(0, str(self.repo_root))
            if not path.exists():
                return DeploymentResult(service=self.name, ok=False, id=module_path, details={"error": "missing module"})
            namespace: dict[str, Any] = {"__file__": str(path), "__name__": "__xion_ops_chute_verify__"}
            exec(path.read_text(encoding="utf-8"), namespace)
            ok = "chute" in namespace or "stub" in namespace
            return DeploymentResult(
                service=self.name,
                ok=ok,
                id=module_path,
                details={"has_chute": "chute" in namespace, "has_stub": "stub" in namespace},
            )
        except Exception as exc:
            return DeploymentResult(service=self.name, ok=False, id=module_path, details={"error": str(exc)})
        finally:
            sys.path[:] = old_path

    def build_chute_image(
        self,
        chute_ref: str = DEFAULT_CHUTE_REF,
        *,
        wait: bool = False,
        public: bool = False,
        debug: bool = False,
        logo: str | None = None,
        include_cwd: bool = False,
        config_path: str | None = None,
    ) -> DeploymentResult:
        ref = normalize_chute_ref(chute_ref)
        cmd: list[str] = ["build", ref]
        if config_path:
            cmd.extend(["--config-path", config_path])
        if logo:
            cmd.extend(["--logo", logo])
        if include_cwd:
            cmd.append("--include-cwd")
        if debug:
            cmd.append("--debug")
        if public:
            cmd.append("--public")
        if wait:
            cmd.append("--wait")
        # Official `build --wait` runs until completion; omit timeout unless CI caps wall-clock.
        build_to = _optional_positive_int_timeout("XION_CHUTES_BUILD_CMD_TIMEOUT_SEC")
        started = time.monotonic()
        result = self._invoke_chutes_cli(cmd, timeout=build_to)
        duration_s = round(time.monotonic() - started, 3)
        quota_hit = False
        low = (result.stderr or "") + "\n" + (result.stdout or "")
        ll = low.lower()
        if "imagehistory" in ll or ("24" in low and ("hour" in ll or "hours" in ll)):
            quota_hit = True

        details: dict[str, Any] = {
            "command": ["chutes"] + cmd,
            "returncode": result.returncode,
            "duration_s": duration_s,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "chute_ref": ref,
            "imagehistory_quota_suspected": quota_hit,
        }
        return DeploymentResult(
            service=self.name,
            ok=result.returncode == 0,
            id=ref,
            details=details,
        )

    def deploy_chute(
        self,
        chute_ref: str = DEFAULT_CHUTE_REF,
        *,
        accept_fee: bool = False,
        public: bool = False,
        debug: bool = False,
        logo: str | None = None,
        config_path: str | None = None,
    ) -> DeploymentResult:
        ref = normalize_chute_ref(chute_ref)
        cmd: list[str] = ["deploy", ref]
        if config_path:
            cmd.extend(["--config-path", config_path])
        if logo:
            cmd.extend(["--logo", logo])
        if debug:
            cmd.append("--debug")
        if public:
            cmd.append("--public")
        if accept_fee:
            cmd.append("--accept-fee")
        deploy_to = _optional_positive_int_timeout("XION_CHUTES_DEPLOY_CMD_TIMEOUT_SEC")
        started = time.monotonic()
        result = self._invoke_chutes_cli(cmd, timeout=deploy_to)
        duration_s = round(time.monotonic() - started, 3)
        combined = combined_command_output(result)
        parsed = parse_chutes_deploy_output(combined)
        chute_id = parsed.get("chute_id")
        url = parsed.get("url")
        version = parsed.get("version")
        fallback_json_id = _extract_field(result.stdout, "id") or _extract_field(result.stdout, "chute_id")
        if not chute_id and fallback_json_id:
            chute_id = fallback_json_id
        if not url:
            url = _extract_url(result.stdout) or _extract_url(result.stderr)

        details: dict[str, Any] = {
            "command": ["chutes"] + cmd,
            "returncode": result.returncode,
            "duration_s": duration_s,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "chute_ref": ref,
            "parsed_chute_id": chute_id,
            "parsed_version": version,
            "parsed_url": url,
        }
        warn: list[str] = []
        if result.returncode == 0 and not chute_id:
            warn.append(
                "deploy exited 0 but chute_id was not parsed from output; inspect CLI logs or "
                "use `python -m xion_ops chutes chutes-get` before rollback"
            )
        if result.returncode == 0 and not url and not (os.environ.get("XION_CHUTES_BASE_URL") or "").strip():
            warn.append(
                "no gateway URL parsed and XION_CHUTES_BASE_URL is unset; cord warmup may need an explicit URL"
            )
        if warn:
            details["deploy_metadata_warnings"] = warn

        return DeploymentResult(
            service=self.name,
            ok=result.returncode == 0,
            id=chute_id or ref,
            url=url,
            details=details,
        )

    def chutes_cli_platform_warmup(self, slug: str, *, timeout_s: float | None = None) -> DeploymentResult:
        """Run ``chutes warmup <slug>`` once (allocates miners for cold deployments).

        Default subprocess timeout (**660** s) exceeds the bundled SDK’s **600** s instance poll so the CLI
        is not SIGKILL’d at the upstream default ceiling during cold GPU scheduling.
        """

        t = (
            float(timeout_s)
            if timeout_s is not None
            else _float_env("XION_CHUTES_PLATFORM_WARMUP_TIMEOUT_SEC", CHUTES_CLI_WARMUP_SUBPROCESS_DEFAULT_SEC)
        )
        t_int = max(60, int(t))
        stripped = slug.strip()
        completed = self._invoke_chutes_cli(["warmup", stripped], timeout=t_int)
        return DeploymentResult(
            service=self.name,
            ok=completed.returncode == 0,
            id=stripped,
            details={
                "returncode": completed.returncode,
                "stdout": completed.stdout[-8192:] if completed.stdout else "",
                "stderr": completed.stderr[-8192:] if completed.stderr else "",
            },
        )

    def chutes_chutes_get(self, name_or_id: str) -> DeploymentResult:
        """Shell out to ``chutes chutes get`` (upstream prints JSON).

        Useful for miner/instance polling per Chutes CLI docs when HTTP cords lag.
        """

        nid = name_or_id.strip()
        completed = self._invoke_chutes_managed_cli(["get", nid])
        return DeploymentResult(
            service=self.name,
            ok=completed.returncode == 0,
            id=nid,
            details={
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
        )

    def chutes_images_list(self, *, limit: int = 25, page: int = 0) -> DeploymentResult:
        """Shell out to ``chutes images list`` (console table/Rich output)."""

        completed = self._invoke_chutes_cli(
            ["images", "list", "--limit", str(limit), "--page", str(page)]
        )
        return DeploymentResult(
            service=self.name,
            ok=completed.returncode == 0,
            details={"stdout": completed.stdout, "stderr": completed.stderr},
        )

    def warmup(self, url: str | None = None) -> DeploymentResult:
        """Warm by polling HTTP cords until green (preferred over a single `/health`)."""

        return self.warmup_until_cords_green(url)

    def rollback_chute(self, chute_id: str) -> DeploymentResult:
        """Invoke ``chutes chutes delete``; upstream accepts chute UUID or logical name."""

        nid = chute_id.strip()
        result = self._invoke_chutes_managed_cli(["delete", nid])
        return DeploymentResult(
            service=self.name,
            ok=result.returncode == 0,
            id=nid,
            details={"stdout": result.stdout, "stderr": result.stderr},
        )

    def base_url(self) -> str:
        return os.environ.get("XION_CHUTES_BASE_URL") or os.environ.get("XION_SECONDARY_HTTPS_BASE", "")


def _extract_url(output: str) -> str | None:
    for token in output.replace("\n", " ").split():
        clean = token.strip().strip(",").strip("`'\"")
        if clean.startswith("https://") or clean.startswith("http://"):
            return clean.rstrip(").,;]")
    return None


def _extract_field(output: str, key: str) -> str | None:
    try:
        payload: Any = json.loads(output)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and isinstance(payload.get(key), str):
        return str(payload[key])
    return None
