"""Phase 6+ Velocity Hardening: Hermes depth enforcement wrapper.

Doctrine anchor: docs/HERMES_SPIKE_RESULT.md § 3.
Enforces a global delegation depth limit to prevent infinite sub-agent spawning.
"""
class MaxDepthExceededError(Exception):
    """Raised when an agent attempts to spawn beyond the allowed depth."""

class DepthEnforcer:
    def __init__(self, max_depth: int = 1):
        self.max_depth = max_depth

    def check_depth(self, current_depth: int) -> None:
        if current_depth > self.max_depth:
            raise MaxDepthExceededError(f"Delegation depth {current_depth} exceeds limit {self.max_depth}")
