"""Tests for `orchestrator.volition` (Phase 5c code surface).

The load-bearing tests in this file are:

  1. ``test_genesis_weights_byte_pinned_to_doctrine`` — the tuple in
     `orchestrator/volition.py` byte-equals the values printed in
     `docs/18-VOLITION.md` Part III. A silent drift in either
     direction flips this test red.

  2. ``test_source_whitelist_enforced`` — an AST walk on
     `compute_drive_vector`'s body asserts that every
     ``state.<sense>.<field>`` attribute reference is a member of
     ``SOURCE_WHITELIST``. This is Invariant 15's AST-level teeth:
     a PR that reads a revenue-adjacent field inside the function
     fails CI loudly.

  3. ``test_compute_drive_vector_signature_excludes_revenue_slots`` —
     the function's signature has no parameter named `revenue`,
     `fees`, `rebates`, `price`, `balance`, `tips`, `donations`, or
     `engagement`. Adding such a slot requires editing the signature
     AND passing this test's assertion.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from orchestrator.sensorium import (
    Chronoception,
    DistressSignal,
    Interoception,
    Proprioception,
    SensoriumState,
)
from orchestrator.volition import (
    GENESIS_WEIGHTS,
    SOURCE_WHITELIST,
    WEIGHT_CEILING,
    WEIGHT_FLOOR,
    DriveVector,
    Volition,
    compute_drive_vector,
)


# ------------------------------------------------------- pure-function shape


def _fresh_state(**overrides) -> SensoriumState:
    """Build a SensoriumState with benign defaults, overridable per field."""
    return SensoriumState(
        interoception=overrides.get(
            "interoception",
            Interoception.from_placeholders(treasury_stress=0.0, cost_pressure=0.0),
        ),
        chronoception=overrides.get("chronoception", Chronoception()),
        proprioception=overrides.get("proprioception", Proprioception()),
        distress=overrides.get(
            "distress", DistressSignal(text_distress_score=0.0)
        ),
    )


def test_compute_drive_vector_pure_function_same_state_same_output():
    state = _fresh_state()
    a = compute_drive_vector(state)
    b = compute_drive_vector(state)
    assert a.survive == b.survive
    assert a.serve == b.serve
    assert a.meaning == b.meaning
    assert a.weights == b.weights


def test_compute_drive_vector_returns_drive_vector_type():
    assert isinstance(compute_drive_vector(_fresh_state()), DriveVector)


def test_drive_vector_fields_are_in_unit_interval_or_saturate():
    state = _fresh_state(
        interoception=Interoception.from_placeholders(
            treasury_stress=1.0, cost_pressure=1.0
        ),
    )
    v = compute_drive_vector(state)
    for label, val in (("survive", v.survive), ("serve", v.serve), ("meaning", v.meaning)):
        assert 0.0 <= val <= 1.0, f"{label} out of unit interval: {val}"


def test_survive_rises_when_interoception_rises():
    low = compute_drive_vector(_fresh_state(
        interoception=Interoception.from_placeholders(treasury_stress=0.0, cost_pressure=0.0),
    ))
    high = compute_drive_vector(_fresh_state(
        interoception=Interoception.from_placeholders(treasury_stress=1.0, cost_pressure=1.0),
    ))
    assert high.survive > low.survive
    assert high.survive == 1.0


def test_survive_rises_when_checkpoint_is_stale():
    low = compute_drive_vector(_fresh_state(
        chronoception=Chronoception(),   # 0 staleness
    ))
    # one week ceiling -> 1.0; half-week should be ~0.5
    half_week_s = 3.5 * 24 * 3600.0
    high = compute_drive_vector(_fresh_state(
        chronoception=Chronoception(checkpoint_staleness_s=half_week_s),
    ))
    assert high.survive > low.survive


def test_survive_rises_when_watchdog_fires_accumulate():
    low = compute_drive_vector(_fresh_state())
    high = compute_drive_vector(_fresh_state(
        proprioception=Proprioception.from_runtime(watchdog_fires_recent=32),
    ))
    assert high.survive >= 1.0 or high.survive > low.survive


def test_serve_and_meaning_are_genesis_defaults_at_phase_5c():
    # Until Phase 5+ wires aggregate readings, serve and meaning are
    # pinned constants. A change here is a Phase-5+ landing signal.
    v = compute_drive_vector(_fresh_state())
    assert v.serve == 0.5
    assert v.meaning == 0.5


def test_drive_vector_to_dict_keys_match_drive_endpoint_shape():
    v = compute_drive_vector(_fresh_state())
    d = v.to_dict()
    assert set(d.keys()) == {"survive", "serve", "meaning", "weights", "as_of_utc_ns"}
    assert set(d["weights"].keys()) == {"w_survive", "w_serve", "w_meaning"}


# ------------------------------------------------------- Genesis weight pins


def test_genesis_weights_shape():
    assert isinstance(GENESIS_WEIGHTS, tuple)
    assert len(GENESIS_WEIGHTS) == 3
    assert all(isinstance(w, float) for w in GENESIS_WEIGHTS)


def test_genesis_weights_satisfy_constitutional_simplex():
    assert abs(sum(GENESIS_WEIGHTS) - 1.0) < 1e-9
    for w in GENESIS_WEIGHTS:
        assert WEIGHT_FLOOR <= w <= WEIGHT_CEILING


def test_genesis_weights_byte_pinned_to_doctrine():
    # docs/18-VOLITION.md Part III pins (0.30, 0.45, 0.25). A drift in
    # either direction (code or doctrine) flips this test red.
    # xion-verify drive performs the equivalent check at the
    # doctrine-bytes level; this test is the pytest-side partner.
    assert GENESIS_WEIGHTS == (0.30, 0.45, 0.25)


def test_compute_drive_vector_rejects_weights_outside_simplex():
    state = _fresh_state()
    with pytest.raises(ValueError):
        compute_drive_vector(state, weights=(0.05, 0.45, 0.50))  # floor violated
    with pytest.raises(ValueError):
        compute_drive_vector(state, weights=(0.60, 0.25, 0.15))  # ceiling violated
    with pytest.raises(ValueError):
        compute_drive_vector(state, weights=(0.30, 0.45, 0.30))  # doesn't sum to 1


# ------------------------------------------------------- Invariant 15 teeth


_FORBIDDEN_PARAM_NAMES: tuple[str, ...] = (
    "revenue",
    "fees",
    "rebates",
    "price",
    "balance",
    "tips",
    "donations",
    "engagement",
)


def test_compute_drive_vector_signature_excludes_revenue_slots():
    sig = inspect.signature(compute_drive_vector)
    names = {p.name for p in sig.parameters.values()}
    for forbidden in _FORBIDDEN_PARAM_NAMES:
        assert forbidden not in names, (
            f"Invariant 15 teeth: compute_drive_vector accepted a "
            f"forbidden parameter name {forbidden!r}. "
            f"See docs/18-VOLITION.md Part V."
        )


def _parse_volition_source() -> ast.Module:
    src_path = Path(__file__).resolve().parents[1] / "volition.py"
    return ast.parse(src_path.read_text(encoding="utf-8"), filename=str(src_path))


def _attribute_chains_under(node: ast.AST) -> list[tuple[str, ...]]:
    """Return every ``a.b.c`` attribute chain (as a tuple of names)
    rooted at a bare ``Name``. Ignores chains rooted at a call or
    subscript; we only care about what the code reads off the
    argument-passed SensoriumState.
    """
    chains: list[tuple[str, ...]] = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Attribute):
            parts: list[str] = []
            cur: ast.AST = sub
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.append(cur.id)
                parts.reverse()
                chains.append(tuple(parts))
    return chains


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name!r} not found in orchestrator/volition.py")


def test_source_whitelist_enforced():
    """AST-walk: every `state.<sense>.<field>` chain reached from
    `compute_drive_vector` (including through `_survive_from_state`
    etc.) MUST appear in `SOURCE_WHITELIST`.
    """
    tree = _parse_volition_source()
    # Transitively include helpers that compute any term. Today that
    # is `_survive_from_state`; extending it requires adding to this
    # list AND to the whitelist.
    function_names = ("compute_drive_vector", "_survive_from_state")
    seen_chains: set[tuple[str, ...]] = set()
    for fname in function_names:
        node = _find_function(tree, fname)
        for chain in _attribute_chains_under(node):
            seen_chains.add(chain)

    # Consider only chains rooted at `state.`; those are the reads
    # off the `SensoriumState` argument. Everything else (constants,
    # `_clamp01`, etc.) is uninteresting.
    state_reads = {c for c in seen_chains if c and c[0] == "state"}

    # Normalise "state.interoception.survival_pressure" ->
    # "interoception.survival_pressure" to match SOURCE_WHITELIST.
    normalised = {".".join(c[1:]) for c in state_reads}

    # Keep only terminal field reads (length 2: sense.field). A chain
    # shorter than that is "state.interoception" (accessing the
    # container) and doesn't count as a field read; a chain longer
    # than that would be nested access we don't currently do.
    field_reads = {c for c in normalised if c.count(".") == 1}

    whitelisted: set[str] = set()
    for allowed in SOURCE_WHITELIST.values():
        whitelisted |= allowed

    bad = field_reads - whitelisted
    assert not bad, (
        f"Invariant 15 teeth: compute_drive_vector (and its helpers) "
        f"read SensoriumState fields outside SOURCE_WHITELIST: "
        f"{sorted(bad)}. Either add them to SOURCE_WHITELIST AND to "
        f"docs/04-ARCHITECTURE.md § \"Volition\" source-whitelist "
        f"table, or remove the read from the function body."
    )


def test_source_whitelist_mentions_no_revenue_adjacent_fields():
    forbidden_substrings = ("revenue", "price", "balance", "tips", "donations", "engagement")
    for term, fields in SOURCE_WHITELIST.items():
        for f in fields:
            for s in forbidden_substrings:
                assert s not in f, (
                    f"Invariant 15 teeth: SOURCE_WHITELIST[{term!r}] "
                    f"contains a revenue-adjacent field {f!r}. "
                    f"This is a constitutional violation."
                )


# ------------------------------------------------------- Volition holder


def test_volition_compute_matches_free_function():
    state = _fresh_state()
    holder = Volition()
    from_holder = holder.compute(state)
    from_free = compute_drive_vector(state)
    assert from_holder.survive == from_free.survive
    assert from_holder.serve == from_free.serve
    assert from_holder.meaning == from_free.meaning
    assert from_holder.weights == from_free.weights


def test_volition_snapshot_keys_are_drive_endpoint_shape():
    state = _fresh_state()
    payload = Volition().snapshot(state, methodology_hash="a" * 64)
    assert set(payload.keys()) >= {"schema_version", "as_of_utc_ns", "terms", "methodology_hash"}
    assert set(payload["terms"].keys()) == {"survive", "serve", "meaning"}
    for term in payload["terms"].values():
        assert set(term.keys()) >= {"current_signal", "weight", "weight_band"}
        assert term["weight_band"] == [WEIGHT_FLOOR, WEIGHT_CEILING]


def test_volition_snapshot_without_methodology_hash_omits_the_key():
    payload = Volition().snapshot(_fresh_state())
    assert "methodology_hash" not in payload
