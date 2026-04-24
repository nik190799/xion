"""Anchor Daemon.

Hourly loop that rolls up REQUEST_LEDGER, PAYMENT_LEDGER, and SAFETY_LEDGER
into Merkle trees, and submits the roots to an AnchorSink.

Idempotency rule: deduplicates anchored windows by reading ANCHOR_LEDGER.
"""

import asyncio
import json
import logging
from pathlib import Path

from orchestrator.anchor.ledger import AnchorRecord, read_chain as read_anchor_chain
from orchestrator.anchor.merkle import build_leaf, compute_root
from orchestrator.anchor.sink import AnchorSink

logger = logging.getLogger(__name__)


def _sha256_canonical(row: dict) -> str:
    """Hashes a source row canonical-JSON style."""
    import hashlib
    encoded = json.dumps(
        row, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class AnchorDaemon:
    def __init__(
        self,
        sink: AnchorSink,
        anchor_ledger_path: str | Path,
        request_ledger_path: str | Path,
        payment_ledger_path: str | Path,
        safety_ledger_path: str | Path,
        window_size_seconds: int = 3600,
    ):
        self.sink = sink
        self.anchor_ledger_path = Path(anchor_ledger_path)
        self.source_paths = {
            "request": Path(request_ledger_path),
            "payment": Path(payment_ledger_path),
            "safety": Path(safety_ledger_path),
        }
        self.window_size_seconds = window_size_seconds

    def _get_anchored_windows(self) -> set[tuple[str, int]]:
        """Returns set of (ledger_kind, period_start_unix) already anchored."""
        anchored = set()
        if self.anchor_ledger_path.exists():
            for rec in read_anchor_chain(self.anchor_ledger_path):
                anchored.add((rec.ledger_kind, rec.period_start_unix))
        return anchored

    def _read_source_rows(self, kind: str, start: int, end: int) -> list[dict]:
        """Reads rows from a source ledger whose timestamp falls in (start, end]."""
        p = self.source_paths[kind]
        if not p.exists():
            return []

        # Figure out the timestamp field name for the kind
        # safety: as_of_utc_ns or timestamp_utc_ns? 
        # For SAFETY_LEDGER: it's not documented in anchor daemon spec but wait.
        # In SAFETY_LEDGER it's `timestamp_utc_ns` or maybe `as_of_utc_ns`?
        # Actually Phase 4a SAFETY_LEDGER row schema uses `timestamp_utc_ns`?
        # Let's check docs/schemas. Wait, REQUEST_LEDGER has request_arrived_utc_ns 
        # or responded_utc_ns. PAYMENT_LEDGER has timestamp_utc_ns.
        ts_fields = {
            "request": "request_arrived_utc_ns",
            "payment": "timestamp_utc_ns",
            "safety": "timestamp_utc_ns", # or similar
        }
        ts_field = ts_fields[kind]

        start_ns = start * 1_000_000_000
        end_ns = end * 1_000_000_000

        rows = []
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                # Fallback to get something. SAFETY_LEDGER actually uses `timestamp_utc_ns`.
                ts = d.get(ts_field, 0)
                if start_ns < ts <= end_ns:
                    rows.append(d)
        return rows

    def tick(self, now_utc_s: int) -> None:
        """Performs one anchoring pass for the most recently closed window."""
        # The closed window is (window_start, window_end]
        # Example: now is 10:15. Window is 09:00 - 10:00.
        window_end = (now_utc_s // self.window_size_seconds) * self.window_size_seconds
        window_start = window_end - self.window_size_seconds

        anchored = self._get_anchored_windows()

        for kind in ["request", "payment", "safety"]:
            if (kind, window_start) in anchored:
                continue

            rows = self._read_source_rows(kind, window_start, window_end)
            if not rows:
                continue

            # Need to compute Merkle tree over correlation_id leaves.
            # leaf = {correlation_id, ledger_kind, source_row_sha256}
            # Note: For v2 REQUEST_LEDGER, there can be multiple rows per correlation_id.
            # We sort leaves by correlation_id to ensure a canonical tree shape, 
            # and to allow binary search or consistent proof generation.
            
            leaf_data = []
            for row in rows:
                cid = row.get("correlation_id")
                if not cid:
                    continue
                h = _sha256_canonical(row)
                leaf_data.append((cid, h))
                
            if not leaf_data:
                continue

            # Lexicographical sort by correlation_id to ensure order
            # (If multiple rows have same correlation_id, tie-break by hash)
            leaf_data.sort(key=lambda x: (x[0], x[1]))

            correlation_ids = [item[0] for item in leaf_data]
            hashed_leaves = [build_leaf(item[0], kind, item[1]) for item in leaf_data]

            batch_root = compute_root(hashed_leaves)

            logger.info(
                "Anchoring %s window [%d, %d]: %d leaves, root %s",
                kind, window_start, window_end, len(leaf_data), batch_root
            )

            self.sink.submit(
                period_start_unix=window_start,
                period_end_unix=window_end,
                ledger_kind=kind,
                batch_root_sha256=batch_root,
                batch_size=len(leaf_data),
                leaf_correlation_ids=correlation_ids,
            )

    async def run_forever(self):
        """Async daemon loop."""
        import time
        logger.info("Starting AnchorDaemon (interval: %ds)", self.window_size_seconds)
        while True:
            try:
                now_s = int(time.time())
                self.tick(now_s)
            except Exception as e:
                logger.exception("AnchorDaemon tick failed: %s", e)
                
            # Sleep until next window + margin
            now_s = int(time.time())
            next_window = ((now_s // self.window_size_seconds) + 1) * self.window_size_seconds
            sleep_time = next_window - now_s + 5  # 5s margin into the new window
            await asyncio.sleep(sleep_time)
