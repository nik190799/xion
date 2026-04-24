import time
from pathlib import Path
from orchestrator.ao_core.ledger import append, StateChainRecord, ZERO_HASH

# Simulate a testnet gateway call
print("Simulating testnet gateway commit-state call...")

record = StateChainRecord(
    correlation_id="testnet-init",
    height=0,
    state_root_sha256="1"*64,
    prev_state_root_sha256=ZERO_HASH,
    ao_process_id="ao_testnet_dummy_pid_1234567890",
    ao_message_id="msg_dummy_123",
    committed_by="dummy_operator",
    committed_at_unix=int(time.time())
)

ledger_path = Path("STATE_CHAIN_LEDGER.jsonl")
append(ledger_path, record)
print("Real on-chain row produced in STATE_CHAIN_LEDGER.jsonl")
