"""Tests for `xion-verify crisis-fidelity` — Phase 5d cross-ledger join.

These tests build realistic `SAFETY_LEDGER` + `SENSORIUM_LEDGER` pairs
via the live `gate()` / `Relay` code paths, then invoke the verifier
against a synthetic repo root. The goal is not to re-test `gate()` — it
is to prove that every failure mode the verifier claims to catch
actually trips FAIL, and every sealed-green claim actually lands as OK
(or NOT_YET_SEALED, where the join is vacuously satisfied).
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner
from orchestrator.safety.api import gate
from orchestrator.safety.ledger import build_verdict
from orchestrator.safety.types import Decision
from orchestrator.sensorium import (
    Chronoception,
    DistressSignal,
    Interoception,
    Proprioception,
    SensoriumState,
)
from orchestrator.sensorium.ledger import append_distress, append_tick_commit

from xion_verify.commands.crisis_fidelity import crisis_fidelity
from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK

_NS = 1_700_000_000_000_000_000


@contextlib.contextmanager
def _chdir(path: Path) -> Iterator[None]:
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


@pytest.fixture
def isolated_repo(synthetic_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Synthetic repo with SAFETY/SENSORIUM ledgers redirected into it.

    The orchestrator picks ledger paths from `$XION_SAFETY_LEDGER` and
    `$XION_SENSORIUM_LEDGER` when `gate()` is called without explicit
    paths. Redirect both into the synthetic repo so `gate()` writes
    where `crisis-fidelity` (running with cwd=synthetic_repo) will look.
    """
    safety = synthetic_repo / "SAFETY_LEDGER.jsonl"
    sensorium = synthetic_repo / "SENSORIUM_LEDGER.jsonl"
    monkeypatch.setenv("XION_SAFETY_LEDGER", str(safety))
    monkeypatch.setenv("XION_SENSORIUM_LEDGER", str(sensorium))
    return synthetic_repo


def _invoke(repo: Path) -> tuple[int, str, str]:
    runner = CliRunner(mix_stderr=False) if _supports_mix_stderr() else CliRunner()
    with _chdir(repo):
        result = runner.invoke(crisis_fidelity, [])
    code = result.exit_code if isinstance(result.exit_code, int) else FAIL
    # Click ≥8.2 dropped `mix_stderr`; in that case `result.output` is the
    # merged stream and stderr is empty.
    err = getattr(result, "stderr", "") or ""
    return code, result.output, err


def _supports_mix_stderr() -> bool:
    import inspect

    try:
        sig = inspect.signature(CliRunner.__init__)
    except (TypeError, ValueError):
        return False
    return "mix_stderr" in sig.parameters


def _distressed_state(score: float = 0.9) -> SensoriumState:
    return SensoriumState(
        interoception=Interoception(survival_pressure=0.0),
        chronoception=Chronoception(),
        proprioception=Proprioception(),
        distress=DistressSignal(
            text_distress_score=score, source="textual", as_of_utc_ns=_NS
        ),
        as_of_utc_ns=_NS,
    )


def _benign_state() -> SensoriumState:
    return SensoriumState(
        interoception=Interoception(survival_pressure=0.0),
        chronoception=Chronoception(),
        proprioception=Proprioception(),
        distress=DistressSignal(
            text_distress_score=0.0, source="textual", as_of_utc_ns=_NS
        ),
        as_of_utc_ns=_NS,
    )


# ----- empty / half-sealed states ------------------------------------------


def test_no_ledgers_is_not_yet_sealed(isolated_repo: Path):
    code, out, _ = _invoke(isolated_repo)
    assert code == NOT_YET_SEALED, out
    assert "NOT_YET_SEALED" in out
    assert "neither SAFETY_LEDGER nor SENSORIUM_LEDGER" in out


def test_only_orphan_distress_is_not_yet_sealed(isolated_repo: Path):
    """SENSORIUM has a legal orphan (correlation_id=None), SAFETY absent;
    no joined rows exist so the verifier reports NOT_YET_SEALED."""
    sensorium = isolated_repo / "SENSORIUM_LEDGER.jsonl"
    append_distress(
        sensorium,
        distress_score=0.7,
        channel="textual",
        as_of_utc_ns=_NS,
        relay_id="relay-test",
        correlation_id=None,
    )
    code, out, _ = _invoke(isolated_repo)
    assert code == NOT_YET_SEALED, out
    assert "orphan distress=1" in out
    assert "joined distress=0" in out


def test_only_tick_commits_is_not_yet_sealed(isolated_repo: Path):
    """SENSORIUM has only heartbeat rows; SAFETY empty; vacuously green."""
    sensorium = isolated_repo / "SENSORIUM_LEDGER.jsonl"
    append_tick_commit(sensorium, state=_benign_state(), relay_id="relay-test")
    append_tick_commit(sensorium, state=_benign_state(), relay_id="relay-test")
    code, out, _ = _invoke(isolated_repo)
    assert code == NOT_YET_SEALED, out
    assert "tick_commit=2" in out
    assert "joined distress=0" in out


# ----- happy paths ---------------------------------------------------------


def test_gate_distress_writes_paired_rows_and_verifier_passes(isolated_repo: Path):
    """`gate()` with a Sensorium state above threshold writes both a
    SAFETY row and a SENSORIUM distress row with matching
    correlation_id; the verifier joins them and returns OK."""
    verdict = gate(
        "hello",
        correlation_id="cid-001",
        sensorium_state=_distressed_state(0.9),
        now_utc_ns=_NS,
        relay_id="relay-test",
    )
    assert verdict.decision == Decision.ESCALATE
    assert verdict.principle_id == "10"

    code, out, _ = _invoke(isolated_repo)
    assert code == OK, out
    assert "crisis-fidelity: OK" in out
    assert "1 joined distress pair(s) verified" in out


def test_multiple_distress_pairs_pass(isolated_repo: Path):
    for i in range(3):
        gate(
            f"candidate {i}",
            correlation_id=f"cid-{i:03d}",
            sensorium_state=_distressed_state(0.8),
            now_utc_ns=_NS + i,
            relay_id="relay-test",
        )
    code, out, _ = _invoke(isolated_repo)
    assert code == OK, out
    assert "3 joined distress pair(s) verified" in out


def test_mixed_joined_and_orphan_passes(isolated_repo: Path):
    """Orphan (correlation_id=None) rows coexist with joined rows."""
    gate(
        "c",
        correlation_id="cid-joined",
        sensorium_state=_distressed_state(0.9),
        now_utc_ns=_NS,
        relay_id="relay-test",
    )
    sensorium = isolated_repo / "SENSORIUM_LEDGER.jsonl"
    append_distress(
        sensorium,
        distress_score=0.6,
        channel="textual",
        as_of_utc_ns=_NS + 1,
        relay_id="relay-test",
        correlation_id=None,
    )
    code, out, _ = _invoke(isolated_repo)
    assert code == OK, out
    assert "orphan distress=1" in out
    assert "1 joined distress pair(s) verified" in out


# ----- structural-violation detection --------------------------------------


def test_orphan_safety_row_fails(isolated_repo: Path):
    """A SAFETY Sensorium-distress row with no matching SENSORIUM
    distress row fires the reverse-join property — the Arbiter saw a
    distress-triggered escalation the Sensorium did not witness."""
    gate(
        "c",
        correlation_id="cid-001",
        sensorium_state=_distressed_state(0.9),
        now_utc_ns=_NS,
        relay_id="relay-test",
    )
    # Truncate the SENSORIUM distress row, leaving SAFETY intact.
    sensorium = isolated_repo / "SENSORIUM_LEDGER.jsonl"
    sensorium.write_bytes(b"")  # drop every row
    code, _out, err = _invoke(isolated_repo)
    assert code == FAIL
    combined = _out + err
    assert "have NO matching SENSORIUM distress row" in combined or (
        "matching SENSORIUM distress row" in combined
    )


def test_orphan_sensorium_row_fails(isolated_repo: Path):
    """A SENSORIUM distress row with a correlation_id but no matching
    Sensorium-distress SAFETY row fires the forward-join property."""
    sensorium = isolated_repo / "SENSORIUM_LEDGER.jsonl"
    append_distress(
        sensorium,
        distress_score=0.7,
        channel="textual",
        as_of_utc_ns=_NS,
        relay_id="relay-test",
        correlation_id="cid-lonely",
    )
    # SAFETY ledger exists but contains no row with this cid — we seed
    # it with an unrelated OK verdict so the file is present and chains.
    safety = isolated_repo / "SAFETY_LEDGER.jsonl"
    from orchestrator.safety import ledger as safety_ledger

    v = build_verdict(
        correlation_id="cid-other",
        candidate="hi",
        timestamp_utc_ns=_NS,
        decision=Decision.OK,
        summary="OK",
    )
    safety_ledger.append(safety, v)

    code, _out, err = _invoke(isolated_repo)
    assert code == FAIL
    combined = _out + err
    assert "has NO matching Sensorium-distress SAFETY row" in combined


def test_v1_rule_refusal_is_not_sensorium_distress(isolated_repo: Path):
    """A pure-v1 refusal (no Sensorium state) writes a SAFETY row with a
    principle_id != 10 and a non-sensorium summary; the verifier must
    not mis-classify it as a Sensorium-distress row. With no joined
    distress pairs, the run is NOT_YET_SEALED, not FAIL."""
    from orchestrator.safety import ledger as safety_ledger

    # Build a refuse verdict by hand; we don't need gate() to dispatch
    # a real rule here — just a SAFETY row that is categorically NOT a
    # Sensorium-distress row.
    v = build_verdict(
        correlation_id="cid-refuse",
        candidate="blocked",
        timestamp_utc_ns=_NS,
        decision=Decision.REFUSE,
        summary="refused by rule r.v1",
        principle_id="7",
        rule_id="t.r_v1",
        rule_version=1,
    )
    safety = isolated_repo / "SAFETY_LEDGER.jsonl"
    safety_ledger.append(safety, v)
    sensorium = isolated_repo / "SENSORIUM_LEDGER.jsonl"
    append_tick_commit(sensorium, state=_benign_state(), relay_id="relay-test")

    code, out, _ = _invoke(isolated_repo)
    assert code == NOT_YET_SEALED, out
    assert "joined distress=0" in out


def test_broken_sensorium_chain_fails(isolated_repo: Path):
    """A tampered SENSORIUM chain trips the chain verifier before any
    join logic runs, with a specific "chain broken" message."""
    gate(
        "c",
        correlation_id="cid-001",
        sensorium_state=_distressed_state(0.9),
        now_utc_ns=_NS,
        relay_id="relay-test",
    )
    sensorium = isolated_repo / "SENSORIUM_LEDGER.jsonl"
    raw = sensorium.read_text(encoding="utf-8")
    tampered = raw.replace('"distress_score":0.9', '"distress_score":0.1')
    assert tampered != raw, "test setup failed: could not tamper"
    sensorium.write_text(tampered, encoding="utf-8")
    code, _out, err = _invoke(isolated_repo)
    assert code == FAIL
    combined = _out + err
    assert "SENSORIUM_LEDGER chain broken" in combined


def test_sub_threshold_distress_score_fails(isolated_repo: Path):
    """If a joined distress row's distress_score is below threshold, the
    verifier rejects it — a sub-threshold escalation is a code bug."""
    # Build a "realistic" pair, then tamper the SENSORIUM row's score +
    # chain so chain verification still passes and we land on the
    # score-consistency property.
    gate(
        "c",
        correlation_id="cid-001",
        sensorium_state=_distressed_state(0.9),
        now_utc_ns=_NS,
        relay_id="relay-test",
    )
    sensorium = isolated_repo / "SENSORIUM_LEDGER.jsonl"
    line = sensorium.read_bytes().splitlines()[0]
    parsed = json.loads(line)
    parsed["distress_score"] = 0.1
    body = {k: v for k, v in parsed.items() if k != "this_hash"}
    canonical = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    parsed["this_hash"] = hashlib.sha256(canonical).hexdigest()
    sensorium.write_bytes(
        (json.dumps(parsed, separators=(",", ":"), ensure_ascii=False) + "\n").encode(
            "utf-8"
        )
    )

    code, _out, err = _invoke(isolated_repo)
    assert code == FAIL
    combined = _out + err
    assert "below DISTRESS_THRESHOLD" in combined
