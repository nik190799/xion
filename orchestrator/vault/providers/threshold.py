"""Threshold-unlock vault provider."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_PRIME = 257
_DEFAULT_THRESHOLD = 3


def _mod_inverse(value: int) -> int:
    return pow(value % _PRIME, -1, _PRIME)


def _interpolate_at_zero(points: list[tuple[int, int]]) -> int:
    total = 0
    for i, (x_i, y_i) in enumerate(points):
        numerator = 1
        denominator = 1
        for j, (x_j, _) in enumerate(points):
            if i == j:
                continue
            numerator = (numerator * (-x_j)) % _PRIME
            denominator = (denominator * (x_i - x_j)) % _PRIME
        total = (total + y_i * numerator * _mod_inverse(denominator)) % _PRIME
    return total


def _decode_share(raw: Any) -> tuple[int, list[int]]:
    if not isinstance(raw, dict) or not isinstance(raw.get("x"), int) or not isinstance(raw.get("y"), list):
        raise ValueError("threshold share must be an object with integer x and y[]")
    x = raw["x"]
    values = raw["y"]
    if x <= 0 or x >= _PRIME:
        raise ValueError("threshold share x coordinate out of range")
    if any(not isinstance(value, int) or value < 0 or value >= _PRIME for value in values):
        raise ValueError("threshold share y coordinate out of range")
    return x, values


def combine_shares(raw_shares: list[Any], threshold: int = _DEFAULT_THRESHOLD) -> str:
    """Reconstruct a UTF-8 secret from Shamir shares over GF(257)."""

    if len(raw_shares) < threshold:
        raise ValueError(f"at least {threshold} shares are required")
    shares = [_decode_share(raw) for raw in raw_shares[:threshold]]
    secret_bytes = bytearray()
    width = len(shares[0][1])
    if any(len(values) != width for _, values in shares):
        raise ValueError("threshold shares have inconsistent lengths")
    xs = [x for x, _ in shares]
    if len(set(xs)) != len(xs):
        raise ValueError("threshold shares must have unique x coordinates")
    for index in range(width):
        value = _interpolate_at_zero([(x, values[index]) for x, values in shares])
        if value > 255:
            raise ValueError("reconstructed secret byte is outside UTF-8 byte range")
        secret_bytes.append(value)
    return secret_bytes.decode("utf-8")


@dataclass(frozen=True, slots=True)
class ThresholdVault:
    """Local Shamir 3-of-5 credential vault provider.

    The provider expects a JSON bundle at `XION_THRESHOLD_VAULT_PATH`.
    Keeping share loading local preserves the gateway boundary while avoiding a
    new vendor dependency for the pre-Genesis ceremony path.
    """

    provider_id: str = "threshold"
    path: Path | None = None

    def unlock(self, name: str) -> str | None:
        bundle = self._load_bundle()
        secrets = bundle.get("secrets", {})
        if not isinstance(secrets, dict) or name not in secrets:
            return None
        threshold = int(bundle.get("threshold", _DEFAULT_THRESHOLD))
        shares = secrets[name]
        if not isinstance(shares, list):
            raise ValueError(f"threshold secret {name} must be a share list")
        return combine_shares(shares, threshold=threshold)

    def is_sealed(self) -> bool:
        path = self._path()
        return path is None or not path.is_file()

    def posture(self) -> str:
        return "threshold-local-shamir" if not self.is_sealed() else "threshold-sealed"

    def _path(self) -> Path | None:
        if self.path is not None:
            return self.path
        raw = os.environ.get("XION_THRESHOLD_VAULT_PATH", "").strip()
        return Path(raw) if raw else None

    def _load_bundle(self) -> dict[str, Any]:
        path = self._path()
        if path is None:
            raise FileNotFoundError("XION_THRESHOLD_VAULT_PATH is not set")
        return json.loads(path.read_text(encoding="utf-8"))


ThresholdVaultStub = ThresholdVault

__all__ = ["ThresholdVault", "ThresholdVaultStub", "combine_shares"]
