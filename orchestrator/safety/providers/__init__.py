"""Real Arbiter v2 provider implementations.

Every submodule here defines a concrete `Provider` subclass and calls
`orchestrator.safety.llm_arbiter.register_provider` at import time so
that setting `XION_LLM_ARBITER_PROVIDER=<provider_id>` selects it.

Doctrine for each provider lives in `docs/04-ARCHITECTURE.md`. That is
the canonical source for identity pins, rubric shape, canonical-raw-output
format, and deprecation procedure. Code in this subpackage MUST NOT drift
from that doctrine without bumping the provider's `provider_version`.

Import contract. The orchestrator's critical path
(`orchestrator.safety.api` → `llm_arbiter.get_active_provider`) imports
this subpackage lazily. That means:

  - The `DeterministicStub` default works with zero provider imports.
  - Only when `get_active_provider()` is actually called does this
    subpackage load, which in turn imports every concrete provider.
  - Each provider's module-level code registers the provider class
    with the registry via `register_provider(...)`.

This keeps any network-touching code out of the bare `import
orchestrator.safety` path while still letting operator env-var
selection work transparently.

To add a new provider:

  1. Create `orchestrator/safety/providers/<your_provider>.py`.
  2. Define a `Provider` subclass (see `chutes_llm_judge.py` for the
     template).
  3. Call `register_provider(YourProvider)` at module scope.
  4. Import the module from this `__init__.py` (one line below) so
     `get_active_provider()` sees it.
  5. Write a doctrine section in `docs/04-ARCHITECTURE.md`. A provider
     without pinned doctrine cannot be audited in 2126 and therefore
     must not ship.
"""

from __future__ import annotations

from orchestrator.safety.providers import chutes_llm_judge  # noqa: F401 — registers on import

__all__: list[str] = []
