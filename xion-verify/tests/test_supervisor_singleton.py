"""Tests for `xion-verify supervisor-singleton` — Phase 5g+ landing.

Each branch of the verifier maps to one property declared in the
module docstring. The tests build synthetic ``SENSORIUM_LEDGER.jsonl``
files via the live ``append_tick_commit`` code path (not by writing
JSON by hand) so that the seq/prev_hash/this_hash chain is always
well-formed and the tests cannot pass against a broken writer.
"""

from __future__ import annotations

import contextlib
import inspect
import os
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from orchestrator.sensorium import (
    Chronoception,
    DistressSignal,
    Interoception,
    Proprioception,
    SensoriumState,
)
from orchestrator.sensorium.ledger import append_distress, append_tick_commit
from xion_verify.commands.supervisor_singleton import supervisor_singleton
from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK


@contextlib.contextmanager
def _chdir(path: Path) -> Iterator[None]:
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def _supports_mix_stderr() -> bool:
    try:
        sig = inspect.signature(CliRunner.__init__)
    except (TypeError, ValueError):
        return False
    return "mix_stderr" in sig.parameters


def _invoke(
    repo: Path,
    *extra_args: str,
) -> tuple[int, str, str]:
    runner = CliRunner(mix_stderr=False) if _supports_mix_stderr() else CliRunner()
    with _chdir(repo):
        result = runner.invoke(supervisor_singleton, list(extra_args))
    code = result.exit_code if isinstance(result.exit_code, int) else FAIL
    err = getattr(result, "stderr", "") or ""
    return code, result.output, err


def _state_at(as_of_ns: int) -> SensoriumState:
    return SensoriumState(
        interoception=Interoception(survival_pressure=0.0),
        chronoception=Chronoception(),
        proprioception=Proprioception(),
        distress=DistressSignal(
            text_distress_score=0.0,
            source="textual",
            as_of_utc_ns=as_of_ns,
        ),
        as_of_utc_ns=as_of_ns,
    )


def _tick(path: Path, *, as_of_ns: int, relay_id: str) -> None:
    append_tick_commit(path, state=_state_at(as_of_ns), relay_id=relay_id)


@pytest.fixture
def ledger_path(synthetic_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    p = synthetic_repo / "SENSORIUM_LEDGER.jsonl"
    monkeypatch.setenv("XION_SENSORIUM_LEDGER", str(p))
    return p


# ----- NOT_YET_SEALED branches ---------------------------------------------


def test_no_ledger_is_not_yet_sealed(synthetic_repo: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        "XION_SENSORIUM_LEDGER",
        str(synthetic_repo / "SENSORIUM_LEDGER.jsonl"),
    )
    code, out, _err = _invoke(synthetic_repo)
    assert code == NOT_YET_SEALED, out
    assert "NOT_YET_SEALED" in out
    assert "no SENSORIUM_LEDGER" in out


def test_empty_window_is_not_yet_sealed(
    synthetic_repo: Path, ledger_path: Path
):
    # All ticks far in the past — outside the default 24h window.
    long_ago = time.time_ns() - 365 * 24 * 3600 * 1_000_000_000
    for i in range(3):
        _tick(ledger_path, as_of_ns=long_ago + i, relay_id="relay-a")

    code, out, _err = _invoke(synthetic_repo)
    assert code == NOT_YET_SEALED, out
    assert "no tick_commit rows" in out


def test_non_tick_rows_alone_is_not_yet_sealed(
    synthetic_repo: Path, ledger_path: Path
):
    # Distress rows are not tick_commits — the verifier ignores them.
    append_distress(
        ledger_path,
        distress_score=0.9,
        channel="textual",
        as_of_utc_ns=time.time_ns(),
        relay_id="relay-alpha",
        correlation_id="a" * 32,
    )
    code, out, _err = _invoke(synthetic_repo)
    assert code == NOT_YET_SEALED, out


# ----- OK branches ----------------------------------------------------------


def test_single_leader_clean_window_is_ok(
    synthetic_repo: Path, ledger_path: Path
):
    now = time.time_ns()
    # Ten monotonically-increasing ticks, all from one leader.
    for i in range(10):
        _tick(
            ledger_path,
            as_of_ns=now - (10 - i) * 1_000_000_000,
            relay_id="relay-alpha",
        )
    code, out, _err = _invoke(synthetic_repo)
    assert code == OK, out
    assert "OK" in out
    assert "unique_relay_ids=['relay-alpha']" in out
    assert "failovers=0/1" in out


def test_single_graceful_failover_is_ok(
    synthetic_repo: Path, ledger_path: Path
):
    now = time.time_ns()
    # Leader alpha for five ticks, then a clean handoff to beta.
    for i in range(5):
        _tick(
            ledger_path,
            as_of_ns=now - (10 - i) * 1_000_000_000,
            relay_id="relay-alpha",
        )
    for i in range(5):
        _tick(
            ledger_path,
            as_of_ns=now - (5 - i) * 1_000_000_000,
            relay_id="relay-beta",
        )
    code, out, _err = _invoke(synthetic_repo)
    assert code == OK, out
    assert "failovers=1/1" in out


def test_two_graceful_failovers_under_raised_budget_is_ok(
    synthetic_repo: Path, ledger_path: Path
):
    now = time.time_ns()
    rids = ("relay-a", "relay-b", "relay-c")
    for epoch_idx, rid in enumerate(rids):
        for i in range(3):
            _tick(
                ledger_path,
                as_of_ns=now - (12 - epoch_idx * 3 - i) * 1_000_000_000,
                relay_id=rid,
            )
    # Default budget (1) would FAIL (2 transitions). Raising to 2 is OK.
    code, out, _err = _invoke(synthetic_repo, "--max-failovers", "2")
    assert code == OK, out
    assert "failovers=2/2" in out


# ----- FAIL branches (Property A) ------------------------------------------


def test_unbounded_churn_fails_property_a(
    synthetic_repo: Path, ledger_path: Path
):
    now = time.time_ns()
    # Five transitions, default budget = 1.
    for i in range(6):
        _tick(
            ledger_path,
            as_of_ns=now - (6 - i) * 1_000_000_000,
            relay_id=f"relay-{i}",
        )
    code, _out, err = _invoke(synthetic_repo)
    assert code == FAIL, err
    assert "Property A violated" in err
    assert "transitions" in err


# ----- FAIL branches (Property B: within-epoch monotonicity) ---------------


def test_within_epoch_clock_regression_fails_property_b(
    synthetic_repo: Path, ledger_path: Path
):
    now = time.time_ns()
    # Two ticks from the same leader where the second goes backwards.
    _tick(ledger_path, as_of_ns=now - 2_000_000_000, relay_id="relay-alpha")
    _tick(ledger_path, as_of_ns=now - 3_000_000_000, relay_id="relay-alpha")
    code, _out, err = _invoke(synthetic_repo)
    assert code == FAIL, err
    assert "Property B violated" in err
    assert "within leader epoch" in err


def test_identical_tick_ns_in_same_epoch_fails_property_b(
    synthetic_repo: Path, ledger_path: Path
):
    now = time.time_ns()
    ts = now - 5_000_000_000
    _tick(ledger_path, as_of_ns=ts, relay_id="relay-alpha")
    _tick(ledger_path, as_of_ns=ts, relay_id="relay-alpha")
    code, _out, err = _invoke(synthetic_repo)
    assert code == FAIL, err
    assert "Property B violated" in err


# ----- FAIL branches (Property C: concurrent-leader overlap) --------------


def test_concurrent_leaders_overlap_fails_property_c(
    synthetic_repo: Path, ledger_path: Path
):
    """The KW-API-002 corruption signature: two relay_ids interleaved.

    relay-alpha ticks at t=-8s and t=-6s; relay-beta ticks at t=-7s.
    The two time ranges [-8s, -6s] and [-7s, -7s] strictly overlap —
    Property C must fire. Set ``--max-failovers`` high enough to get
    past Property A (there are 2 sort-order transitions after
    interleaving).
    """
    now = time.time_ns()
    _tick(ledger_path, as_of_ns=now - 8_000_000_000, relay_id="relay-alpha")
    _tick(ledger_path, as_of_ns=now - 7_000_000_000, relay_id="relay-beta")
    _tick(ledger_path, as_of_ns=now - 6_000_000_000, relay_id="relay-alpha")
    code, _out, err = _invoke(synthetic_repo, "--max-failovers", "5")
    assert code == FAIL, err
    assert "Property C violated" in err
    assert "concurrent-leader overlap" in err


def test_non_overlapping_ranges_clean_failover_is_ok(
    synthetic_repo: Path, ledger_path: Path
):
    """Property-C regression: contiguous leader epochs must not trip it.

    relay-alpha ticks at t=-10s..-6s; relay-beta ticks at t=-5s..-1s.
    The ranges do not overlap (strictly increasing). Verifier OK.
    """
    now = time.time_ns()
    for i in range(3):
        _tick(
            ledger_path,
            as_of_ns=now - (10 - 2 * i) * 1_000_000_000,
            relay_id="relay-alpha",
        )
    for i in range(3):
        _tick(
            ledger_path,
            as_of_ns=now - (5 - 2 * i) * 1_000_000_000,
            relay_id="relay-beta",
        )
    code, out, _err = _invoke(synthetic_repo)
    assert code == OK, out


# ----- --path override ------------------------------------------------------


def test_path_override_reads_alternate_file(
    synthetic_repo: Path, tmp_path: Path
):
    alt = tmp_path / "alt_ledger.jsonl"
    now = time.time_ns()
    _tick(alt, as_of_ns=now - 1_000_000_000, relay_id="relay-alt")
    code, out, _err = _invoke(synthetic_repo, "--path", str(alt))
    assert code == OK, out
    assert "unique_relay_ids=['relay-alt']" in out


def test_window_hours_narrow_excludes_prior_ticks(
    synthetic_repo: Path, ledger_path: Path
):
    now = time.time_ns()
    # Older tick from a different leader — OUTSIDE a 0.001h (3.6s) window.
    _tick(
        ledger_path,
        as_of_ns=now - 60 * 1_000_000_000,
        relay_id="relay-old",
    )
    # Recent tick from the "current" leader — INSIDE the window.
    _tick(
        ledger_path,
        as_of_ns=now - 1_000_000_000,
        relay_id="relay-new",
    )
    code, out, _err = _invoke(
        synthetic_repo, "--window-hours", "0.001"
    )
    assert code == OK, out
    assert "unique_relay_ids=['relay-new']" in out
