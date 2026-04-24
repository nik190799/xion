"""GET /me/receipts endpoint."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Annotated

from orchestrator.api.admission import admission_dependency
from orchestrator.anchor.ledger import read_chain as read_anchor_chain
from orchestrator.anchor.merkle import compute_proof, build_leaf
import json

router = APIRouter(prefix="/me", tags=["me"])


def _sha256_canonical(row: dict) -> str:
    import hashlib
    encoded = json.dumps(
        row, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@router.get("/receipts", dependencies=[Depends(admission_dependency)])
def get_receipts(
    request: Request,
    since_unix: int = Query(0, alias="since"),
    correlation_id: str | None = Query(None),
    principal_id: Annotated[str, Depends(admission_dependency)] = None,
):
    """Returns Merkle inclusion proofs for anchored interactions.
    
    Filters by period_start_unix >= since_unix and optional correlation_id.
    """
    anchor_ledger_path = request.app.state.anchor_ledger_path
    
    # We also need the source ledgers to rebuild the leaf hash!
    source_paths = {
        "request": request.app.state.request_ledger_path,
        "payment": request.app.state.payment_ledger_path,
        "safety": request.app.state.safety_ledger_path,
    }

    results = []
    
    # Very naive unoptimized search for Phase 6.3 
    if not anchor_ledger_path.exists():
        return results

    for rec in read_anchor_chain(anchor_ledger_path):
        if rec.period_start_unix < since_unix:
            continue
            
        if correlation_id and correlation_id not in rec.leaf_correlation_ids:
            continue
            
        # To compute the proof, we need the full leaf_data for this batch.
        # This means reading the source ledger for that window.
        kind = rec.ledger_kind
        source_path = source_paths.get(kind)
        if not source_path or not source_path.exists():
            continue
            
        start_ns = rec.period_start_unix * 1_000_000_000
        end_ns = rec.period_end_unix * 1_000_000_000
        
        ts_fields = {
            "request": "request_arrived_utc_ns",
            "payment": "timestamp_utc_ns",
            "safety": "timestamp_utc_ns",
        }
        ts_field = ts_fields.get(kind, "timestamp_utc_ns")
        
        rows = []
        with source_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                ts = d.get(ts_field, 0)
                if start_ns < ts <= end_ns:
                    rows.append(d)
                    
        # Match the daemon's leaf generation
        leaf_data = []
        for row in rows:
            cid = row.get("correlation_id")
            if not cid:
                continue
            h = _sha256_canonical(row)
            leaf_data.append((cid, h))
            
        # Tie-break exactly as daemon does
        leaf_data.sort(key=lambda x: (x[0], x[1]))
        
        hashed_leaves = [build_leaf(item[0], kind, item[1]) for item in leaf_data]
        
        # If filtering, only yield the matching correlation_id
        for i, item in enumerate(leaf_data):
            cid = item[0]
            if correlation_id and cid != correlation_id:
                continue
                
            proof = compute_proof(hashed_leaves, i)
            results.append({
                "correlation_id": cid,
                "ledger_kind": kind,
                "anchor_seq": rec.seq,
                "batch_root_sha256": rec.batch_root_sha256,
                "merkle_proof": proof,
                "ao_message_id": rec.ao_message_id,
            })

    return results
