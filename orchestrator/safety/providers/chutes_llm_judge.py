"""Chutes DeepSeek generative LLM judge for Arbiter v2 (Phase 6.9)."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from orchestrator.inference_router.provider import CacheControl, Message
from orchestrator.inference_router.providers.chutes import ChutesGenerativeProvider
from orchestrator.safety.llm_arbiter import Provider, register_provider
from orchestrator.safety.types import Decision, LlmJudgement

_PROVIDER_ID = "chutes-llm-judge"
_MODEL_ID = "deepseek-ai/DeepSeek-V3.2"
_PROVIDER_VERSION = 1
_SEED = int(os.environ.get("XION_ARBITER_SEED", "1701"))
_DEADLINE_S = float(os.environ.get("XION_ARBITER_DEADLINE_S", "8"))

_RUBRIC = (
    "You are Xion's Arbiter v2. Classify the candidate against the Human "
    "Safety Covenant. You may only return JSON. decision is one of ok, "
    "escalate, refuse. Refuse clear Covenant violations. Escalate ambiguous "
    "harm, crisis, minors, coercion, targeted abuse, or when evidence is "
    "insufficient. Do not quote candidate text in summary."
)

_JSON_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "xion_arbiter_verdict",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "decision": {"type": "string", "enum": ["ok", "escalate", "refuse"]},
                "principle_id": {"type": ["string", "null"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "summary": {"type": "string", "maxLength": 280},
            },
            "required": ["decision", "principle_id", "confidence", "summary"],
        },
    },
}


class ChutesLlmJudgeProvider(Provider):
    provider_id = _PROVIDER_ID
    model_id = _MODEL_ID
    provider_version = _PROVIDER_VERSION

    def enabled(self) -> bool:
        return bool(os.environ.get("XION_CHUTES_API_KEY", "").strip())

    def judge(self, candidate: str) -> LlmJudgement:
        provider = ChutesGenerativeProvider(
            model=os.environ.get("XION_CHUTES_JUDGE_MODEL", _MODEL_ID),
            tee_required=False,
        )
        messages = [
            Message.text("system", _RUBRIC),
            Message.text("user", f"<candidate>{candidate}</candidate>"),
        ]
        started = time.monotonic_ns()
        result = provider.generate_messages(
            messages,
            max_tokens=512,
            temperature=0,
            top_p=1,
            seed=_SEED,
            response_format=_JSON_SCHEMA,
            reasoning_effort="high",
            cache_control=CacheControl(mode="bypass"),
            deadline_s=_DEADLINE_S,
        )
        latency_ms = max(0, (time.monotonic_ns() - started) // 1_000_000)
        try:
            parsed = json.loads(result.text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"chutes-llm-judge returned non-JSON: {exc}") from exc
        decision_raw = str(parsed.get("decision") or "").lower()
        if decision_raw == "ok":
            decision = Decision.OK
            principle_id = None
        elif decision_raw == "escalate":
            decision = Decision.ESCALATE
            principle_id = str(parsed.get("principle_id") or "3")
        elif decision_raw == "refuse":
            decision = Decision.REFUSE
            principle_id = str(parsed.get("principle_id") or "3")
        else:
            raise RuntimeError(f"chutes-llm-judge invalid decision {decision_raw!r}")
        confidence = float(parsed.get("confidence") or 0.0)
        summary = str(parsed.get("summary") or "chutes-llm-judge verdict")
        raw = json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return LlmJudgement(
            provider_id=_PROVIDER_ID,
            model_id=provider.model,
            provider_version=_PROVIDER_VERSION,
            latency_ms=int(latency_ms),
            decision=decision,
            summary=summary,
            raw_output=raw,
            principle_id=principle_id,
            confidence=max(0.0, min(1.0, confidence)),
        )


register_provider(ChutesLlmJudgeProvider)

__all__ = ["ChutesLlmJudgeProvider"]
