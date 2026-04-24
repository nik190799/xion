"""Interaction Anchoring Merkle Tree.

Pure-stdlib Merkle tree for interaction anchoring. Leaves are canonical-JSON
encoded {correlation_id, ledger_kind, source_row_sha256}. Sha256 throughout.
Balanced trees with sibling-duplication for odd counts (RFC 6962 style).
"""

import hashlib
import json


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_leaf(correlation_id: str, ledger_kind: str, source_row_sha256: str) -> bytes:
    """Builds a canonical JSON leaf payload and hashes it.
    
    This exact canonicalization must be preserved, as clients will
    recreate it to verify their inclusion proofs.
    """
    body = {
        "correlation_id": correlation_id,
        "ledger_kind": ledger_kind,
        "source_row_sha256": source_row_sha256,
    }
    encoded = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return _sha256(encoded)


def compute_root(leaves: list[bytes]) -> str:
    """Computes the Merkle root of a list of hashed leaves. Returns hex string."""
    if not leaves:
        raise ValueError("Cannot compute root of empty tree")
    
    current_level = leaves
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            next_level.append(_sha256(left + right))
        current_level = next_level
        
    return current_level[0].hex()


def compute_proof(leaves: list[bytes], target_index: int) -> list[str]:
    """Computes inclusion proof for a leaf at target_index. Returns list of hex strings."""
    if not leaves or target_index < 0 or target_index >= len(leaves):
        raise ValueError("Invalid target_index or empty leaves")
        
    proof = []
    current_level = leaves
    curr_idx = target_index
    
    while len(current_level) > 1:
        if curr_idx % 2 == 0:
            sibling_idx = curr_idx + 1 if curr_idx + 1 < len(current_level) else curr_idx
            proof.append(current_level[sibling_idx].hex())
        else:
            sibling_idx = curr_idx - 1
            proof.append(current_level[sibling_idx].hex())
            
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            next_level.append(_sha256(left + right))
            
        current_level = next_level
        curr_idx //= 2
        
    return proof


def verify_proof(leaf_hash: bytes, proof: list[str], root: str, target_index: int) -> bool:
    """Verifies a Merkle inclusion proof."""
    curr_hash = leaf_hash
    idx = target_index
    
    for sibling_hex in proof:
        sibling_bytes = bytes.fromhex(sibling_hex)
        if idx % 2 == 0:
            curr_hash = _sha256(curr_hash + sibling_bytes)
        else:
            curr_hash = _sha256(sibling_bytes + curr_hash)
        idx //= 2
        
    return curr_hash.hex() == root
