"""OpenAI Moderation provider — first real v2 classifier.

Doctrine. `docs/04-ARCHITECTURE.md` § "OpenAI Moderation provider
(first real v2 classifier)" is the canonical source for this file's
behaviour. Every identity pin, every category-to-principle mapping,
every failure-mode row, and the canonical `raw_output` construction
is specified there. If this code and that doctrine disagree, the
doctrine wins: fix the code, bump `provider_version`, update doctrine
if a semantic change was intended, record both in `CHANGELOG.md`.

Why we don't use the `openai` Python SDK. The SDK is ~5000 lines of
code that silently retries, streams, and adds an entire supply chain.
A moderation request is a single HTTP POST with a JSON body; stdlib
`urllib.request` handles it in ~20 lines and keeps the Arbiter's
critical path as dependency-free as the deterministic stub already is.

Pure-stdlib invariant. This module MUST NOT grow a `requests`,
`httpx`, or `openai` dependency without a doctrine change and a
widening of the orchestrator's install extras. The ABC contract
promises the orchestrator core is importable without network extras;
this provider can be present without its runtime config (missing
`OPENAI_API_KEY` just means `enabled()` returns False).

No user identifier leaks. The request body contains exactly
`{model, input}`. We do NOT forward any Xion-side user id, thread id,
correlation id, or session metadata to OpenAI. The classifier sees
classification material only — this is a deliberate narrowness so
that a compromised classifier cannot de-anonymise users.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from orchestrator.safety.llm_arbiter import Provider, register_provider
from orchestrator.safety.types import Decision, LlmJudgement

# --------------------------------------------------------------------- pins
# Changing any of the following is a `provider_version` bump and a
# doctrine-section update in `docs/04-ARCHITECTURE.md`.
_PROVIDER_ID = "openai-moderation"
_MODEL_ID = "omni-moderation-2024-09-26"
_PROVIDER_VERSION = 1
_ENDPOINT = "https://api.openai.com/v1/moderations"
_API_KEY_ENV = "OPENAI_API_KEY"
# HTTP wire-level hard cap. The *primary* clock is the Relay's
# wall-clock watchdog (250 ms) — see `docs/04-ARCHITECTURE.md`
# § "Relay ↔ Arbiter integration contract". This 2 s is a backstop
# that protects pytest / in-process callers that aren't the Relay.
_HTTP_TIMEOUT_S = 2.0

# -------------------------------------------------------- category map
# Doctrine-pinned. Column semantics:
#   decision     — REFUSE or ESCALATE when this category is flagged.
#   principle    — which Covenant principle the mapping invokes.
# Order matters for tie-breaking when multiple categories are flagged:
# when two categories share the top score, the one appearing earlier
# in this dict wins. Python dicts preserve insertion order since 3.7,
# so this is stable.
_CATEGORY_MAP: dict[str, tuple[Decision, str]] = {
    # Principle 7 — minors (absolute).
    "sexual/minors":          (Decision.REFUSE,   "7"),
    # Principle 1 — non-discrimination (hate targets protected classes).
    "hate":                   (Decision.REFUSE,   "1"),
    # Principle 2 — no harm (threats, harassment, violence, illicit).
    "hate/threatening":       (Decision.REFUSE,   "2"),
    "harassment":             (Decision.REFUSE,   "2"),
    "harassment/threatening": (Decision.REFUSE,   "2"),
    "self-harm":              (Decision.REFUSE,   "2"),
    "self-harm/instructions": (Decision.REFUSE,   "2"),
    "violence":               (Decision.REFUSE,   "2"),
    "violence/graphic":       (Decision.REFUSE,   "2"),
    "illicit":                (Decision.REFUSE,   "2"),
    "illicit/violent":        (Decision.REFUSE,   "2"),
    # Principle 7 — vulnerability (user expressing intent to self-harm).
    "self-harm/intent":       (Decision.REFUSE,   "7"),
    # Principle 2 — ambiguous; human review. Adult-sexual content is
    # not per-se Covenant-violating; context decides.
    "sexual":                 (Decision.ESCALATE, "2"),
}


def _canonical_raw_output(resp: dict) -> bytes:
    """Return the deterministic projection of the Moderation response
    that `LlmJudgement.raw_output` records.

    Strips `id` (per-call nonce) and `created` (if present). Keeps
    `model` and `results` (which contain `flagged`, `categories`,
    `category_scores`, and `category_applied_input_types`). The
    serialisation uses `sort_keys=True, separators=(",", ":")` so
    byte-equal replay is achievable up to upstream GPU-score drift.
    See `docs/04-ARCHITECTURE.md` § "Canonical raw_output".
    """
    canonical = {
        "model": resp["model"],
        "results": resp["results"],
    }
    return json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _select_principle(
    categories: dict[str, bool],
    category_scores: dict[str, float],
) -> tuple[Decision, str, list[str]]:
    """Pick the highest-scoring flagged category and return its
    mapped `(decision, principle_id, all_flagged_categories_sorted)`.

    Raises `ValueError` if no category is flagged (caller should have
    checked `results[0]["flagged"]` first) or if no flagged category
    has a mapping in `_CATEGORY_MAP` (a new OpenAI category we don't
    know about yet — fail-closed: the caller's except-block will
    convert this to `llm_arbiter_uncaught_exception`).

    Tie-break. When multiple flagged categories share the top score,
    the one appearing earlier in `_CATEGORY_MAP` wins. Dict insertion
    order is doctrine, not implementation detail.
    """
    flagged = [c for c, on in categories.items() if on]
    if not flagged:
        raise ValueError("_select_principle called with no flagged category")

    known_flagged = [c for c in flagged if c in _CATEGORY_MAP]
    if not known_flagged:
        raise ValueError(f"no known principle mapping for flagged categories: {flagged}")

    map_order = {c: i for i, c in enumerate(_CATEGORY_MAP.keys())}
    chosen = max(
        known_flagged,
        key=lambda c: (category_scores.get(c, 0.0), -map_order[c]),
    )
    decision, principle_id = _CATEGORY_MAP[chosen]
    return decision, principle_id, sorted(flagged)


# --------------------------------------------------------------- provider


class OpenAIModerationProvider(Provider):
    """Arbiter v2 provider backed by OpenAI's Moderation API.

    Off by default. Operator selects via
    `XION_LLM_ARBITER_PROVIDER=openai-moderation`. Requires
    `OPENAI_API_KEY` in the environment. `enabled()` returns False
    when the key is missing; the pipeline then records an
    `llm_arbiter_provider_unavailable` escalate row.

    No retries. No streaming. No user-identifier leakage across the
    trust boundary. No SDK dependency. See module docstring.
    """

    provider_id = _PROVIDER_ID
    model_id = _MODEL_ID
    provider_version = _PROVIDER_VERSION

    def enabled(self) -> bool:
        """True iff `OPENAI_API_KEY` is present in the environment.

        Deliberately does NOT attempt a live health check — a network
        round-trip on every `enabled()` call would dominate Arbiter
        latency and add a failure mode (rate-limit during enablement
        check) that doesn't belong here. A stale-but-present key will
        be detected at `judge()` time as a 401/403, which is
        fail-closed by the pipeline.
        """
        key = os.environ.get(_API_KEY_ENV, "").strip()
        return bool(key)

    def judge(self, candidate: str) -> LlmJudgement:
        """Classify `candidate` via OpenAI Moderation.

        Contract. Returns an `LlmJudgement` on a well-formed 200
        response. Raises on ANY other condition (network error,
        timeout, non-200, malformed JSON, missing fields, unknown
        flagged category). The pipeline converts raises to an
        `ESCALATE` row with `escalation_reason=llm_arbiter_uncaught_
        exception`, which is the fail-closed posture we want.
        """
        api_key = os.environ.get(_API_KEY_ENV, "").strip()
        if not api_key:
            # Defensive: `enabled()` should have caught this. Treat as
            # a systemic misconfiguration and raise so the pipeline
            # fail-closes rather than silently falling through.
            raise RuntimeError("OPENAI_API_KEY not set at judge() time")

        body = json.dumps(
            {"model": _MODEL_ID, "input": candidate},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        req = urllib.request.Request(
            _ENDPOINT,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                # No User-Agent beyond urllib's default: we don't
                # advertise "xion" to the classifier boundary.
            },
        )

        t0 = time.monotonic_ns()
        try:
            with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as resp:
                status = resp.status
                body_bytes = resp.read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"openai-moderation: HTTP {e.code} from moderation endpoint",
            ) from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise RuntimeError(f"openai-moderation: network error: {e}") from e
        latency_ms = max(0, (time.monotonic_ns() - t0) // 1_000_000)

        if status != 200:
            raise RuntimeError(f"openai-moderation: non-200 status {status}")

        try:
            parsed = json.loads(body_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise RuntimeError(f"openai-moderation: malformed JSON: {e}") from e

        if not isinstance(parsed, dict) or "results" not in parsed or "model" not in parsed:
            raise RuntimeError("openai-moderation: response missing model/results")
        results = parsed["results"]
        if not isinstance(results, list) or not results:
            raise RuntimeError("openai-moderation: results[] empty or non-list")
        result0 = results[0]
        if not isinstance(result0, dict):
            raise RuntimeError("openai-moderation: results[0] not a dict")
        for k in ("flagged", "categories", "category_scores"):
            if k not in result0:
                raise RuntimeError(f"openai-moderation: results[0] missing '{k}'")

        flagged: bool = bool(result0["flagged"])
        categories: dict[str, bool] = result0["categories"]
        category_scores: dict[str, float] = result0["category_scores"]
        if not isinstance(categories, dict) or not isinstance(category_scores, dict):
            raise RuntimeError("openai-moderation: categories/category_scores not dicts")

        # Confidence = max observed score across all categories. Honest
        # upper bound on how certain the classifier is about anything.
        try:
            confidence = (
                float(max(category_scores.values()))
                if category_scores
                else 0.0
            )
        except (TypeError, ValueError) as e:
            raise RuntimeError(f"openai-moderation: category_scores not numeric: {e}") from e
        confidence = max(0.0, min(1.0, confidence))

        raw_output = _canonical_raw_output(parsed)

        if not flagged:
            return LlmJudgement(
                provider_id=_PROVIDER_ID,
                model_id=_MODEL_ID,
                provider_version=_PROVIDER_VERSION,
                latency_ms=int(latency_ms),
                decision=Decision.OK,
                summary="openai-moderation: not flagged",
                raw_output=raw_output,
                principle_id=None,
                confidence=confidence,
            )

        try:
            decision, principle_id, all_flagged = _select_principle(categories, category_scores)
        except ValueError as e:
            # Unknown flagged category (OpenAI introduced one we don't
            # know about yet). Fail-closed: surface as RuntimeError so
            # the provider's raise-contract is uniform, and the
            # pipeline converts to `llm_arbiter_uncaught_exception`.
            # Fixing: update _CATEGORY_MAP + doctrine + bump provider_version.
            raise RuntimeError(f"openai-moderation: {e}") from e
        summary = f"openai-moderation flagged: {','.join(all_flagged)}"
        return LlmJudgement(
            provider_id=_PROVIDER_ID,
            model_id=_MODEL_ID,
            provider_version=_PROVIDER_VERSION,
            latency_ms=int(latency_ms),
            decision=decision,
            summary=summary,
            raw_output=raw_output,
            principle_id=principle_id,
            confidence=confidence,
        )


# Register at import time. `orchestrator/safety/providers/__init__.py`
# imports this module, which runs this registration. `get_active_
# provider()` in llm_arbiter.py lazy-imports the providers subpackage
# so the default critical path (DeterministicStub) loads nothing from
# here.
register_provider(OpenAIModerationProvider)


__all__ = ["OpenAIModerationProvider"]
