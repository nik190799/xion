"""Shared quorum reader primitives."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class QuorumFailedError(RuntimeError):
    """Raised when endpoints do not reach the required majority."""


@dataclass(frozen=True)
class QuorumResult(Generic[T]):
    value: T
    agreeing_endpoints: tuple[str, ...]
    attempted_endpoints: tuple[str, ...]


def require_quorum(
    endpoints: list[str],
    fetch: Callable[[str], T],
    *,
    min_endpoints: int,
    timeout_workers: int | None = None,
) -> QuorumResult[T]:
    if len(endpoints) < min_endpoints:
        raise QuorumFailedError(
            f"quorum requires at least {min_endpoints} endpoints; got {len(endpoints)}"
        )
    threshold = len(endpoints) // 2 + 1
    observations: dict[str, T | BaseException] = {}
    with ThreadPoolExecutor(max_workers=timeout_workers or len(endpoints)) as pool:
        futures = {pool.submit(fetch, endpoint): endpoint for endpoint in endpoints}
        for future in as_completed(futures):
            endpoint = futures[future]
            try:
                observations[endpoint] = future.result()
            except BaseException as exc:  # noqa: BLE001 - endpoint errors are data.
                observations[endpoint] = exc

    successes: list[tuple[str, T]] = [
        (endpoint, value)
        for endpoint, value in observations.items()
        if not isinstance(value, BaseException)
    ]
    counts = Counter(_stable_key(value) for _, value in successes)
    if not counts:
        raise QuorumFailedError("quorum failed: every endpoint errored")
    key, count = counts.most_common(1)[0]
    if count < threshold:
        raise QuorumFailedError(
            f"quorum failed: best agreement {count}/{len(endpoints)} below threshold {threshold}"
        )
    agreeing = tuple(endpoint for endpoint, value in successes if _stable_key(value) == key)
    for _endpoint, value in successes:
        if _stable_key(value) == key:
            return QuorumResult(
                value=value,
                agreeing_endpoints=agreeing,
                attempted_endpoints=tuple(endpoints),
            )
    raise QuorumFailedError("quorum failed: internal agreement selection error")


def _stable_key(value: object) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return repr(value).encode("utf-8")


__all__ = ["QuorumFailedError", "QuorumResult", "require_quorum"]
