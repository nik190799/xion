"""Phase 6.4: Consent Store.

Append-only JSONL store for user consent preferences.
Keyed by principal_id. Last write wins.
"""
import json
import time
from pathlib import Path

def write_consent(path: Path | str, principal_id: str, consent: dict) -> None:
    """Append a consent record to the store.
    
    Last write for a given principal_id is the canonical state.
    """
    record = {
        "principal_id": principal_id,
        "consent": consent,
        "as_of_utc_ns": time.time_ns(),
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

def read_consent(path: Path | str, principal_id: str) -> dict | None:
    """Read the latest consent record for a given principal_id.
    
    Returns None if no record exists.
    """
    p = Path(path)
    if not p.is_file():
        return None
        
    latest = None
    # We read the whole file and take the last match.
    # In a real database this would be an indexed query. For a local JSONL,
    # and given the scale of settings changes per user, reading the file is OK.
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if record.get("principal_id") == principal_id:
                    latest = record.get("consent")
            except json.JSONDecodeError:
                pass
                
    return latest
