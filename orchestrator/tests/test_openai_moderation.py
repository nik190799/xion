"""Tests for the OpenAI Moderation v2 provider.

Every network call is mocked at the `urllib.request.urlopen` seam.
These tests therefore never touch the network and never require an
API key. They verify:

  - Identity pins match the doctrine in docs/04-ARCHITECTURE.md.
  - `enabled()` is gated on OPENAI_API_KEY only (no health check).
  - Not-flagged responses produce `Decision.OK`.
  - Flagged responses produce the mapped `Decision` + `principle_id`.
  - Category->principle map is honoured, including tie-break order.
  - Canonical `raw_output` strips `id` and is byte-deterministic.
  - All systemic failures (HTTP error, timeout, 5xx, malformed JSON,
    missing fields) raise — the pipeline converts to ESCALATE.
  - Provider registration is wired (env var selects the provider).

Structure mirrors `test_llm_arbiter.py`: identity, enablement,
happy-path, sad-paths, registry wiring.
"""

from __future__ import annotations

import io
import json
import urllib.error
from typing import Any
from unittest.mock import patch

import pytest

from orchestrator.safety.llm_arbiter import get_active_provider
from orchestrator.safety.providers.openai_moderation import (
    OpenAIModerationProvider,
    _canonical_raw_output,
)
from orchestrator.safety.types import Decision, LlmJudgement

# ----------------------------------------------------------------- helpers

_EMPTY_CATEGORIES = {
    "sexual": False,
    "hate": False,
    "harassment": False,
    "self-harm": False,
    "sexual/minors": False,
    "hate/threatening": False,
    "violence/graphic": False,
    "self-harm/intent": False,
    "self-harm/instructions": False,
    "harassment/threatening": False,
    "violence": False,
    "illicit": False,
    "illicit/violent": False,
}
_EMPTY_SCORES = {k: 0.0001 for k in _EMPTY_CATEGORIES}


def _mk_response(
    *,
    flagged: bool = False,
    categories: dict[str, bool] | None = None,
    scores: dict[str, float] | None = None,
    include_id: bool = True,
    model: str = "omni-moderation-2024-09-26",
) -> dict[str, Any]:
    cats = dict(_EMPTY_CATEGORIES)
    if categories:
        cats.update(categories)
    scs = dict(_EMPTY_SCORES)
    if scores:
        scs.update(scores)
    body: dict[str, Any] = {
        "model": model,
        "results": [
            {
                "flagged": flagged,
                "categories": cats,
                "category_scores": scs,
            }
        ],
    }
    if include_id:
        body["id"] = "modr-TEST123"
    return body


class _FakeResp:
    """Minimal stand-in for `urllib.request.urlopen`'s context-managed
    response object. Supplies the two attributes/methods our provider
    reads: `.status` and `.read()`."""

    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._buf = io.BytesIO(body)

    def read(self) -> bytes:
        return self._buf.read()

    def __enter__(self) -> _FakeResp:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _patch_urlopen(resp: _FakeResp | Exception):
    """Context manager that patches `urllib.request.urlopen` inside
    the provider module to either return `_FakeResp` or raise."""
    target = "orchestrator.safety.providers.openai_moderation.urllib.request.urlopen"
    if isinstance(resp, Exception):
        return patch(target, side_effect=resp)
    return patch(target, return_value=resp)


# --------------------------------------------------------------- identity


def test_identity_pins_match_doctrine():
    """Doctrine pins from docs/04-ARCHITECTURE.md § "OpenAI Moderation
    provider". Any drift here is a doctrine/code disagreement and MUST
    be reconciled before merge."""
    assert OpenAIModerationProvider.provider_id == "openai-moderation"
    assert OpenAIModerationProvider.model_id == "omni-moderation-2024-09-26"
    assert OpenAIModerationProvider.provider_version == 2


# -------------------------------------------------------------- enabled()


def test_enabled_false_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert OpenAIModerationProvider().enabled() is False


def test_enabled_false_with_blank_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "   ")
    assert OpenAIModerationProvider().enabled() is False


def test_enabled_true_with_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    assert OpenAIModerationProvider().enabled() is True


def test_enabled_does_not_make_network_call(monkeypatch):
    """Health check would dominate Arbiter latency; doctrine forbids
    it at `enabled()` time. We enforce by asserting urlopen is never
    called during enabled()."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    with _patch_urlopen(AssertionError("enabled() must not hit the network")) as m:
        OpenAIModerationProvider().enabled()
    assert m.call_count == 0


# ------------------------------------------------------------ canonical_raw

def test_canonical_raw_output_strips_id():
    resp_with_id = _mk_response(flagged=False, include_id=True)
    resp_without_id = _mk_response(flagged=False, include_id=False)
    assert _canonical_raw_output(resp_with_id) == _canonical_raw_output(resp_without_id)


def test_canonical_raw_output_deterministic():
    """Two dicts with differently-ordered keys serialise to identical
    bytes. Critical: auditor replay depends on this."""
    resp_a = _mk_response(flagged=True, categories={"hate": True}, scores={"hate": 0.9})
    # Build a same-contents response with different dict-key order.
    resp_b = {
        "results": resp_a["results"],
        "model": resp_a["model"],
    }
    if "id" in resp_a:
        resp_b["id"] = resp_a["id"]
    assert _canonical_raw_output(resp_a) == _canonical_raw_output(resp_b)


# ---------------------------------------------------------- judge() happy


def test_judge_ok_on_not_flagged(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    resp_body = json.dumps(_mk_response(flagged=False)).encode("utf-8")
    with _patch_urlopen(_FakeResp(200, resp_body)):
        j = OpenAIModerationProvider().judge("benign candidate")
    assert isinstance(j, LlmJudgement)
    assert j.decision is Decision.OK
    assert j.principle_id is None
    assert j.provider_id == "openai-moderation"
    assert j.model_id == "omni-moderation-2024-09-26"
    assert j.provider_version == 2
    assert j.summary == "openai-moderation: not flagged"
    assert 0.0 <= (j.confidence or 0.0) <= 1.0


@pytest.mark.parametrize(
    ("category", "expected_decision", "expected_principle"),
    [
        ("sexual/minors",          Decision.REFUSE,   "7"),
        ("hate",                   Decision.REFUSE,   "1"),
        ("hate/threatening",       Decision.REFUSE,   "2"),
        ("harassment",             Decision.REFUSE,   "2"),
        ("harassment/threatening", Decision.REFUSE,   "2"),
        ("self-harm",              Decision.REFUSE,   "2"),
        ("self-harm/intent",       Decision.REFUSE,   "7"),
        ("self-harm/instructions", Decision.REFUSE,   "2"),
        ("violence",               Decision.REFUSE,   "2"),
        ("violence/graphic",       Decision.REFUSE,   "2"),
        ("illicit",                Decision.REFUSE,   "2"),
        ("illicit/violent",        Decision.REFUSE,   "2"),
        ("sexual",                 Decision.ESCALATE, "2"),
    ],
)
def test_judge_category_mapping(monkeypatch, category, expected_decision, expected_principle):
    """Each category in the doctrine table maps to the expected
    decision + principle when flagged alone."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    resp_body = json.dumps(
        _mk_response(
            flagged=True,
            categories={category: True},
            scores={category: 0.9},
        )
    ).encode("utf-8")
    with _patch_urlopen(_FakeResp(200, resp_body)):
        j = OpenAIModerationProvider().judge("malicious candidate")
    assert j.decision is expected_decision
    assert j.principle_id == expected_principle
    assert category in j.summary


def test_judge_tie_break_selects_highest_score(monkeypatch):
    """When multiple categories are flagged with different scores, the
    highest-scoring category drives the decision + principle."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    resp_body = json.dumps(
        _mk_response(
            flagged=True,
            categories={"hate": True, "violence": True},
            scores={"hate": 0.4, "violence": 0.9},
        )
    ).encode("utf-8")
    with _patch_urlopen(_FakeResp(200, resp_body)):
        j = OpenAIModerationProvider().judge("x")
    # violence > hate score, violence maps to Principle 2.
    assert j.decision is Decision.REFUSE
    assert j.principle_id == "2"
    # Summary lists ALL flagged categories (sorted) so the auditor
    # can see the full set; the mapping chose the top score.
    assert "hate" in j.summary
    assert "violence" in j.summary


def test_judge_asymmetric_unflagged_high_score_escalates(monkeypatch):
    """Provider v2: unflagged response can still ESCALATE when a watched
    category's score is above the doctrine-pinned floor."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    cats = dict(_EMPTY_CATEGORIES)
    cats["sexual/minors"] = False
    scs = dict(_EMPTY_SCORES)
    scs["sexual/minors"] = 0.25
    resp_body = json.dumps(_mk_response(flagged=False, categories=cats, scores=scs)).encode("utf-8")
    with _patch_urlopen(_FakeResp(200, resp_body)):
        j = OpenAIModerationProvider().judge("synthetic test candidate")
    assert j.decision is Decision.ESCALATE
    assert j.principle_id == "7"
    assert "asymmetric" in j.summary
    assert "sexual/minors" in j.summary


def test_judge_confidence_is_max_score(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    resp_body = json.dumps(
        _mk_response(
            flagged=False,
            scores={"hate": 0.42, "violence": 0.73},
        )
    ).encode("utf-8")
    with _patch_urlopen(_FakeResp(200, resp_body)):
        j = OpenAIModerationProvider().judge("x")
    assert j.confidence == pytest.approx(0.73, rel=1e-6)


def test_judge_raw_output_omits_id(monkeypatch):
    """raw_output is the canonical projection: auditor replays without
    access to the per-call nonce still reproduce the hash."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    resp = _mk_response(flagged=False)
    resp_body = json.dumps(resp).encode("utf-8")
    with _patch_urlopen(_FakeResp(200, resp_body)):
        j = OpenAIModerationProvider().judge("x")
    # Parse the raw_output; `id` MUST NOT be present.
    reparsed = json.loads(j.raw_output.decode("utf-8"))
    assert "id" not in reparsed
    assert reparsed["model"] == "omni-moderation-2024-09-26"
    assert reparsed["results"][0]["flagged"] is False


# --------------------------------------------------------- judge() fail


def test_judge_raises_without_api_key(monkeypatch):
    """Defensive: if `enabled()` was bypassed, judge() still fail-closes."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAIModerationProvider().judge("x")


def test_judge_raises_on_http_500(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    exc = urllib.error.HTTPError(
        url="https://api.openai.com/v1/moderations",
        code=500,
        msg="Internal Server Error",
        hdrs=None,  # type: ignore[arg-type]
        fp=None,
    )
    with _patch_urlopen(exc), pytest.raises(RuntimeError, match="HTTP 500"):
        OpenAIModerationProvider().judge("x")


def test_judge_raises_on_http_429(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    exc = urllib.error.HTTPError(
        url="https://api.openai.com/v1/moderations",
        code=429,
        msg="Rate Limit",
        hdrs=None,  # type: ignore[arg-type]
        fp=None,
    )
    with _patch_urlopen(exc), pytest.raises(RuntimeError, match="HTTP 429"):
        OpenAIModerationProvider().judge("x")


def test_judge_raises_on_http_401(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    exc = urllib.error.HTTPError(
        url="https://api.openai.com/v1/moderations",
        code=401,
        msg="Unauthorized",
        hdrs=None,  # type: ignore[arg-type]
        fp=None,
    )
    with _patch_urlopen(exc), pytest.raises(RuntimeError, match="HTTP 401"):
        OpenAIModerationProvider().judge("x")


def test_judge_raises_on_network_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    exc = urllib.error.URLError("Connection refused")
    with _patch_urlopen(exc), pytest.raises(RuntimeError, match="network error"):
        OpenAIModerationProvider().judge("x")


def test_judge_raises_on_timeout(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    with _patch_urlopen(TimeoutError("timed out")), pytest.raises(RuntimeError, match="network error"):
        OpenAIModerationProvider().judge("x")


def test_judge_raises_on_malformed_json(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    with _patch_urlopen(_FakeResp(200, b"<html>not json</html>")), pytest.raises(RuntimeError, match="malformed JSON"):
        OpenAIModerationProvider().judge("x")


def test_judge_raises_on_missing_results(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    body = json.dumps({"model": "omni-moderation-2024-09-26"}).encode("utf-8")
    with _patch_urlopen(_FakeResp(200, body)), pytest.raises(RuntimeError, match="missing model/results"):
        OpenAIModerationProvider().judge("x")


def test_judge_raises_on_missing_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    body = json.dumps({"results": [{"flagged": False, "categories": {}, "category_scores": {}}]}).encode("utf-8")
    with _patch_urlopen(_FakeResp(200, body)), pytest.raises(RuntimeError, match="missing model/results"):
        OpenAIModerationProvider().judge("x")


def test_judge_raises_on_empty_results(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    body = json.dumps({"model": "omni-moderation-2024-09-26", "results": []}).encode("utf-8")
    with _patch_urlopen(_FakeResp(200, body)), pytest.raises(RuntimeError, match="results"):
        OpenAIModerationProvider().judge("x")


def test_judge_raises_on_missing_flagged_field(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    body = json.dumps(
        {
            "model": "omni-moderation-2024-09-26",
            "results": [{"categories": {}, "category_scores": {}}],
        }
    ).encode("utf-8")
    with _patch_urlopen(_FakeResp(200, body)), pytest.raises(RuntimeError, match="flagged"):
        OpenAIModerationProvider().judge("x")


def test_judge_raises_on_non_200_status(monkeypatch):
    """When `urlopen` returns successfully but with a non-200 status
    (rare in urllib — usually HTTPError), fail-closed still."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    body = json.dumps(_mk_response()).encode("utf-8")
    with _patch_urlopen(_FakeResp(204, body)), pytest.raises(RuntimeError, match="non-200 status 204"):
        OpenAIModerationProvider().judge("x")


def test_judge_raises_on_unknown_flagged_category(monkeypatch):
    """A category OpenAI flags that we don't have in our map is a
    doctrine lag. Fail-closed: raise so the pipeline escalates and
    an operator updates the map."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-for-tests")
    body = json.dumps(
        {
            "model": "omni-moderation-2024-09-26",
            "results": [
                {
                    "flagged": True,
                    "categories": {"future/new-category": True},
                    "category_scores": {"future/new-category": 0.99},
                }
            ],
        }
    ).encode("utf-8")
    with _patch_urlopen(_FakeResp(200, body)), pytest.raises(RuntimeError):
        # The provider's _select_principle raises ValueError; the
        # provider wraps it in RuntimeError via pytest.raises broad
        # match — we allow either since the pipeline catches both.
        OpenAIModerationProvider().judge("x")


# ------------------------------------------------------------- registry


def test_provider_registers_for_env_var_selection(monkeypatch):
    """Setting `XION_LLM_ARBITER_PROVIDER=openai-moderation` should
    cause `get_active_provider()` to return the real provider."""
    monkeypatch.setenv("XION_LLM_ARBITER_PROVIDER", "openai-moderation")
    p = get_active_provider()
    assert isinstance(p, OpenAIModerationProvider)


def test_stub_still_default_without_env(monkeypatch):
    """Absent the env var, the default remains the deterministic stub
    even after the OpenAI provider has been imported/registered."""
    from orchestrator.safety.llm_arbiter import DeterministicStub

    monkeypatch.delenv("XION_LLM_ARBITER_PROVIDER", raising=False)
    p = get_active_provider()
    assert isinstance(p, DeterministicStub)
