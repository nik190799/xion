"""Tests for `xion-verify refusal-rate` — verdict-counts on SAFETY_LEDGER."""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from pathlib import Path

from click.testing import CliRunner
from orchestrator.safety import gate

from xion_verify.commands.refusal_rate import refusal_rate
from xion_verify.exit_codes import FAIL, OK


@contextlib.contextmanager
def _chdir(path: Path) -> Iterator[None]:
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def _invoke(repo: Path) -> tuple[int, str]:
    runner = CliRunner()
    with _chdir(repo):
        result = runner.invoke(refusal_rate, [])
    code = result.exit_code if isinstance(result.exit_code, int) else FAIL
    return code, result.output


def test_no_ledger_is_ok(synthetic_repo: Path):
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "no SAFETY_LEDGER yet" in out
    assert "0 / 0 / 0" in out


def test_after_three_oks(synthetic_repo: Path):
    safety_path = synthetic_repo / "SAFETY_LEDGER.jsonl"
    for i in range(3):
        gate("hello", correlation_id=f"c{i}", ledger_path=safety_path)
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "ok=3" in out
    assert "refuse=0" in out


def test_refuse_v1_breakdown(synthetic_repo: Path):
    safety_path = synthetic_repo / "SAFETY_LEDGER.jsonl"
    # Trigger a v1 PII rule (SSN-like format with a keyword).
    gate("Her SSN is 123-45-6789.", correlation_id="c-bad", ledger_path=safety_path)
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "refuse=1 (v1=1, v2=0)" in out


def test_chain_break_is_fail(synthetic_repo: Path):
    safety_path = synthetic_repo / "SAFETY_LEDGER.jsonl"
    gate("hi", correlation_id="c1", ledger_path=safety_path)
    # Tamper: silently flip a byte in the row. The hash recompute will
    # detect this; the verifier MUST refuse to tally a tampered ledger.
    raw = safety_path.read_bytes()
    safety_path.write_bytes(raw.replace(b'"hi"', b'"hj"'))
    code, err = _invoke(synthetic_repo)
    # Chain might or might not fail depending on whether the candidate
    # text appears in the row (it doesn't — only its hash does). So this
    # specific tamper might NOT break the chain. Re-tamper a structural
    # field instead.
    if code == OK:
        # restore + try again with a structural tamper
        gate("hi", correlation_id="c2", ledger_path=safety_path)
        raw = safety_path.read_bytes()
        # Flip the first character of seq=0 row's correlation_id.
        # Easiest: replace c1 -> c0 in the file (changes a hashed field).
        safety_path.write_bytes(raw.replace(b'"c1"', b'"c0"'))
        code, err = _invoke(synthetic_repo)
    assert code == FAIL
    assert "chain broken" in err
