"""Verifier for Phase 6.3 Interaction Anchoring."""

import json
from pathlib import Path
from typing import TextIO

import click
from xion_verify.repo import find_repo_root
from orchestrator.anchor.ledger import verify_chain as verify_anchor_chain
from orchestrator.anchor.merkle import build_leaf, compute_root, compute_proof, verify_proof

def _sha256_canonical(row: dict) -> str:
    import hashlib
    encoded = json.dumps(
        row, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def _get_ts_field(kind: str) -> str:
    return {
        "request": "request_arrived_utc_ns",
        "payment": "timestamp_utc_ns",
        "safety": "timestamp_utc_ns",
    }.get(kind, "timestamp_utc_ns")

def verify_interaction_anchor(
    repo_root: Path,
    stdout: TextIO,
) -> int:
    """Verifies ANCHOR_LEDGER against its source ledgers."""
    
    anchor_path = repo_root / "ledgers" / "ANCHOR_LEDGER.jsonl"
    request_path = repo_root / "REQUEST_LEDGER.jsonl"
    payment_path = repo_root / "PAYMENT_LEDGER.jsonl"
    safety_path = repo_root / "SAFETY_LEDGER.jsonl"
    
    if not anchor_path.exists():
        # It's okay if it doesn't exist yet, but we print a note.
        # Actually, if it doesn't exist, we return OK.
        print("ANCHOR_LEDGER.jsonl not found. OK (empty).", file=stdout)
        return 0
        
    try:
        anchor_records = verify_anchor_chain(anchor_path)
    except Exception as e:
        print(f"FAIL: ANCHOR_LEDGER integrity broken: {e}", file=stdout)
        return 1
        
    # Read source rows lazily
    for rec in anchor_records:
        source_path = {
            "request": request_path,
            "payment": payment_path,
            "safety": safety_path,
        }.get(rec.ledger_kind)
        
        if not source_path or not source_path.exists():
            print(f"FAIL: Source ledger {rec.ledger_kind} not found for anchor seq {rec.seq}", file=stdout)
            return 1
            
        start_ns = rec.period_start_unix * 1_000_000_000
        end_ns = rec.period_end_unix * 1_000_000_000
        ts_field = _get_ts_field(rec.ledger_kind)
        
        rows = []
        with source_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                ts = d.get(ts_field, 0)
                if start_ns < ts <= end_ns:
                    rows.append(d)
                    
        # Check property 4: no source row in window omitted
        # Actually, we need to match correlation_ids
        source_cids = set()
        leaf_data = []
        for row in rows:
            cid = row.get("correlation_id")
            if not cid:
                continue
            source_cids.add(cid)
            h = _sha256_canonical(row)
            leaf_data.append((cid, h))
            
        # Tie-break sort exactly as daemon does
        leaf_data.sort(key=lambda x: (x[0], x[1]))
        
        expected_cids = [x[0] for x in leaf_data]
        
        # Check property 3 & 4: exact match of correlation_ids
        if expected_cids != rec.leaf_correlation_ids:
            print(f"FAIL: leaf_correlation_ids mismatch at anchor seq {rec.seq}", file=stdout)
            return 1
            
        # Check property 2: recompute Merkle root
        hashed_leaves = [build_leaf(item[0], rec.ledger_kind, item[1]) for item in leaf_data]
        if not hashed_leaves:
            print(f"FAIL: anchor seq {rec.seq} has 0 leaves but was written", file=stdout)
            return 1
            
        root = compute_root(hashed_leaves)
        if root != rec.batch_root_sha256:
            print(f"FAIL: batch_root_sha256 mismatch at anchor seq {rec.seq}", file=stdout)
            return 1
            
        # Check property 5: spot-check inclusion proofs
        indices = [0, len(hashed_leaves) // 2, len(hashed_leaves) - 1]
        for idx in set(indices):
            proof = compute_proof(hashed_leaves, idx)
            if not verify_proof(hashed_leaves[idx], proof, root, idx):
                print(f"FAIL: inclusion proof failed for index {idx} at anchor seq {rec.seq}", file=stdout)
                return 1

    print(f"OK ({len(anchor_records)} anchors cross-checked)", file=stdout)
    return 0

@click.command(name="interaction-anchor")
@click.pass_context
def cli(ctx: click.Context):
    """Verify Phase 6.3 ANCHOR_LEDGER against source ledgers."""
    repo_root = find_repo_root(Path.cwd())
    import sys
    stdout = ctx.obj["stdout"] if ctx.obj is not None else sys.stdout
    exit_code = verify_interaction_anchor(repo_root, stdout)
    ctx.exit(exit_code)
