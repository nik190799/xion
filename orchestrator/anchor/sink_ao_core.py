"""Phase 6.3.b AO Core Sink."""
import os
import subprocess
from pathlib import Path

from orchestrator.anchor.ledger import append
from orchestrator.anchor.sink import AnchorReceipt, AnchorSink

class AOCoreSink(AnchorSink):
    def __init__(
        self,
        anchor_ledger_path: str,
        ao_gateway_url: str,
        ao_process_id: str,
        ao_signer_jwk_path: str,
        ao_send_timeout_s: float = 15.0,
    ):
        self.ledger_path = anchor_ledger_path
        self.ao_gateway_url = ao_gateway_url.rstrip("/")
        self.ao_process_id = ao_process_id
        self.ao_signer_jwk_path = ao_signer_jwk_path
        self.ao_send_timeout_s = ao_send_timeout_s

    def submit(
        self,
        period_start_unix: int,
        period_end_unix: int,
        ledger_kind: str,
        batch_root_sha256: str,
        batch_size: int,
        leaf_correlation_ids: list[str],
    ) -> AnchorReceipt:
        # 1. POST signed Anchor-Interaction-Batch message via the node helper
        script_path = Path(__file__).parent.parent.parent / "scripts" / "ao-send-anchor-batch.cjs"
        env = os.environ.copy()

        try:
            result = subprocess.run(
                [
                    "node", str(script_path),
                    self.ao_process_id,
                    self.ao_signer_jwk_path,
                    batch_root_sha256,
                    str(batch_size),
                    str(period_start_unix),
                    str(period_end_unix),
                    ledger_kind,
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=self.ao_send_timeout_s,
                env=env,
            )
            ao_message_id = result.stdout.strip()
            
            append(
                path=self.ledger_path,
                period_start_unix=period_start_unix,
                period_end_unix=period_end_unix,
                ledger_kind=ledger_kind,
                batch_root_sha256=batch_root_sha256,
                batch_size=batch_size,
                leaf_correlation_ids=leaf_correlation_ids,
                ao_message_id=ao_message_id,
            )
            return AnchorReceipt(kind="ao_core", ao_message_id=ao_message_id)

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception):
            # Fallback to local
            append(
                path=self.ledger_path,
                period_start_unix=period_start_unix,
                period_end_unix=period_end_unix,
                ledger_kind=ledger_kind,
                batch_root_sha256=batch_root_sha256,
                batch_size=batch_size,
                leaf_correlation_ids=leaf_correlation_ids,
                ao_message_id=None,
                degraded_to_local=True,
            )
            return AnchorReceipt(kind="local_only", ao_message_id=None)
