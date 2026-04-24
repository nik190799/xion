"""Tests for the interaction anchoring Merkle tree."""

import json
from orchestrator.anchor.merkle import (
    _sha256,
    _sha256_hex,
    build_leaf,
    compute_root,
    compute_proof,
    verify_proof,
)

def test_build_leaf_canonicalization():
    """Asserts byte-exact JSON structure for leaves."""
    leaf_bytes = build_leaf("cor_123", "request", "abcdef012345")
    
    # Manually reproduce
    expected_body = {
        "correlation_id": "cor_123",
        "ledger_kind": "request",
        "source_row_sha256": "abcdef012345"
    }
    expected_encoded = json.dumps(
        expected_body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    expected_hash = _sha256(expected_encoded)
    
    assert leaf_bytes == expected_hash

def test_compute_root_single_leaf():
    leaf = _sha256(b"leaf1")
    root = compute_root([leaf])
    assert root == leaf.hex()

def test_compute_root_even_leaves():
    leaf1 = _sha256(b"leaf1")
    leaf2 = _sha256(b"leaf2")
    expected_root = _sha256(leaf1 + leaf2).hex()
    assert compute_root([leaf1, leaf2]) == expected_root

def test_compute_root_odd_leaves():
    leaf1 = _sha256(b"leaf1")
    leaf2 = _sha256(b"leaf2")
    leaf3 = _sha256(b"leaf3")
    
    left = _sha256(leaf1 + leaf2)
    right = _sha256(leaf3 + leaf3) # Sibling duplication
    expected_root = _sha256(left + right).hex()
    
    assert compute_root([leaf1, leaf2, leaf3]) == expected_root

def test_compute_proof_and_verify():
    leaves = [_sha256(f"leaf{i}".encode()) for i in range(5)]
    root = compute_root(leaves)
    
    for i, leaf in enumerate(leaves):
        proof = compute_proof(leaves, i)
        assert verify_proof(leaf, proof, root, i), f"Proof failed for index {i}"

def test_verify_proof_tampered():
    leaves = [_sha256(f"leaf{i}".encode()) for i in range(4)]
    root = compute_root(leaves)
    
    proof = compute_proof(leaves, 1)
    # Tamper with the proof
    tampered_proof = [p if p != proof[0] else _sha256_hex(b"tampered") for p in proof]
    
    assert not verify_proof(leaves[1], tampered_proof, root, 1)
