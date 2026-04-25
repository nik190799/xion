"""Chutes billing telemetry provider (Phase 6.9)."""

from __future__ import annotations

import http.client
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from orchestrator.billing.provider import Balance, Payment, RunwayDays


class ChutesBillingError(RuntimeError):
    pass


@dataclass
class ChutesBillingProvider:
    provider_id: str = "chutes"
    api_base_url: str = field(default_factory=lambda: os.environ.get(
        "XION_CHUTES_API_BASE_URL", "https://api.chutes.ai",
    ))
    _api_key: str = field(default_factory=lambda: os.environ.get(
        "XION_CHUTES_API_KEY", "",
    ), repr=False)

    def __post_init__(self) -> None:
        if not self._api_key:
            raise ChutesBillingError("ChutesBillingProvider requires XION_CHUTES_API_KEY")
        parsed = urlparse(self.api_base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ChutesBillingError(
                f"XION_CHUTES_API_BASE_URL is not a valid http(s) URL: {self.api_base_url!r}"
            )

    def balance(self) -> Balance:
        payload = self._get_json("/users/me", timeout=5.0)
        balance_usd = _first_float(payload, "balance", "balance_usd", "credits", "credit_balance")
        balance_tao = _first_float(payload, "balance_tao", "tao_balance")
        payment_address = _first_str(payload, "payment_address", "deposit_address")
        return Balance(
            provider_id=self.provider_id,
            balance_usd=balance_usd or 0.0,
            balance_tao=balance_tao,
            payment_address=payment_address,
            as_of_utc_ns=time.time_ns(),
        )

    def recent_payments(self, window_s: int) -> list[Payment]:
        payload = self._get_json("/payments", timeout=5.0)
        rows = payload.get("items") or payload.get("data") or payload
        if not isinstance(rows, list):
            return []
        cutoff_ns = time.time_ns() - int(window_s * 1_000_000_000)
        payments: list[Payment] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            ts_ns = _timestamp_ns(row)
            if ts_ns < cutoff_ns:
                continue
            payments.append(
                Payment(
                    provider_id=self.provider_id,
                    amount_tao=_first_float(row, "amount_tao", "tao") or 0.0,
                    amount_usd=_first_float(row, "amount_usd", "usd"),
                    tx_hash=_first_str(row, "tx_hash", "transaction_hash"),
                    timestamp_utc_ns=ts_ns,
                )
            )
        return payments

    def forecast_runway(self, burn_rate_usd_per_day: float | None) -> RunwayDays:
        if burn_rate_usd_per_day is None or burn_rate_usd_per_day <= 0:
            return RunwayDays(days=None, burn_rate_usd_per_day=burn_rate_usd_per_day)
        bal = self.balance()
        return RunwayDays(
            days=bal.balance_usd / burn_rate_usd_per_day,
            burn_rate_usd_per_day=burn_rate_usd_per_day,
        )

    def tao_payment_summary(self) -> dict[str, Any]:
        return self._get_json("/payments/summary/tao", timeout=5.0)

    def _get_json(self, path_suffix: str, *, timeout: float) -> dict[str, Any]:
        parsed = urlparse(self.api_base_url)
        path = (parsed.path.rstrip("/") or "") + path_suffix
        try:
            conn = self._open_connection(parsed, timeout=timeout)
            try:
                conn.request("GET", path, headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "User-Agent": "xion-os/0.4.0 (+phase-6.9)",
                })
                resp = conn.getresponse()
                raw = resp.read()
                status = resp.status
            finally:
                conn.close()
        except (TimeoutError, OSError, http.client.HTTPException) as exc:
            raise ChutesBillingError(f"chutes billing transport error: {exc}") from None
        if not (200 <= status < 300):
            snippet = raw[:256].decode("utf-8", errors="replace")
            raise ChutesBillingError(f"chutes billing HTTP {status}: {snippet}")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ChutesBillingError(f"chutes billing response not JSON: {exc}") from None
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _open_connection(parsed: Any, *, timeout: float) -> http.client.HTTPConnection:
        if parsed.scheme == "https":
            return http.client.HTTPSConnection(parsed.hostname, port=parsed.port, timeout=timeout)
        return http.client.HTTPConnection(parsed.hostname, port=parsed.port, timeout=timeout)


def _first_float(payload: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _first_str(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _timestamp_ns(row: dict[str, Any]) -> int:
    for key in ("timestamp_utc_ns", "created_at_ns"):
        value = row.get(key)
        if isinstance(value, int):
            return value
    # Unknown timestamp shape: keep row recent rather than silently hiding it.
    return time.time_ns()


__all__ = ["ChutesBillingError", "ChutesBillingProvider"]
