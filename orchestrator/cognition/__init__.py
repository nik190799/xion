"""Cognition layer: stateless workers, sub-agents, retrieval (see docs/24-COGNITION.md)."""

from orchestrator.cognition.memory_adapter import (
    ForgetReceipt,
    ForgetScope,
    InMemoryMemoryBackend,
    MemoryForgetAdapter,
)
from orchestrator.cognition.pool import WorkerPool
from orchestrator.cognition.subagent import EphemeralSubagent, SpecialistAgent
from orchestrator.cognition.user_context import UserContext
from orchestrator.cognition.worker import CognitionWorker

__all__ = [
    "CognitionWorker",
    "EphemeralSubagent",
    "ForgetReceipt",
    "ForgetScope",
    "InMemoryMemoryBackend",
    "MemoryForgetAdapter",
    "SpecialistAgent",
    "UserContext",
    "WorkerPool",
]
