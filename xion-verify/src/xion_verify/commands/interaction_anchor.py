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

def _fetch_gateway_anchor_batch(gateway_url: str, process_id: str, owner_address: str, batch_root_sha256: str) -> bool:
    import json
    import urllib.request
    
    lua_code = 'return require("json").encode(AnchorBatches or {})'
    url = f"{gateway_url.rstrip('/')}/dry-run?process-id={process_id}"
    body_obj = {
        "Id": "1234",
        "Owner": owner_address,
        "Target": process_id,
        "Anchor": "0",
        "Tags": [{"name": "Action", "value": "Eval"}],
        "Data": lua_code,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body_obj).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "xion-verify",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            raw = resp.read()
            outer = json.loads(raw.decode("utf-8"))
            data = outer.get("Output", {}).get("data", {})
            if isinstance(data, dict):
                inner_json = data.get("output", "")
            else:
                inner_json = data
            batches = json.loads(inner_json)
            if isinstance(batches, list):
                for b in batches:
                    if b.get("batch_root_sha256") == batch_root_sha256:
                        return True
    except Exception:
        pass
    return False

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

    receipt_path = repo_root / "genesis" / "AO_DEPLOY_RECEIPT.json"
    owner_address = ""
    ao_pid = ""
    if receipt_path.exists():
        try:
            import json
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            owner_address = receipt.get("signer_address", "")
            ao_pid = receipt.get("process_id", "")
        except Exception:
            pass

    import os
    gateway_url = os.environ.get("XION_AO_GATEWAY_URL", "https://cu.ao-testnet.xyz")
    
    ao_confirmed = 0
        
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

        if rec.ao_message_id is not None and ao_pid and owner_address:
            if _fetch_gateway_anchor_batch(gateway_url, ao_pid, owner_address, rec.batch_root_sha256):
                ao_confirmed += 1
            else:
                print(f"FAIL: ao_message_id is set but batch_root_sha256 not found on AO process {ao_pid}", file=stdout)
                return 1

    if ao_confirmed > 0:
        print(f"OK ({len(anchor_records)} anchors cross-checked, {ao_confirmed} of {len(anchor_records)} also confirmed on AO Core PID={ao_pid})", file=stdout)
    else:
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
