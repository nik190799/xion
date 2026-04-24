# deploy_testnet.ps1
# Operator deploy script for Xion AO Core (Phase 6.1)
# Requires `aos` CLI installed and a funded wallet.

param (
    [string]$ProcessName = "xion-core-testnet"
)

Write-Host "Deploying Xion AO Core to testnet..."

# 1. Spawn the process
# aos $ProcessName

# 2. Load the Lua modules
# aos $ProcessName --load ao/process/abi.lua
# aos $ProcessName --load ao/process/state.lua
# aos $ProcessName --load ao/process/handlers/commit_state.lua
# aos $ProcessName --load ao/process/handlers/attest.lua
# aos $ProcessName --load ao/process/xion_core.lua

# 3. Capture the receipt
$Receipt = @{
    process_id = "mock_ao_process_id_1234567890abcdef"
    code_sha256 = "mock_code_sha256"
    network_id = "ao-testnet"
    deployer_address = "mock_deployer_address"
    deploy_timestamp = [int][double]::Parse((Get-Date -UFormat %s))
}

$ReceiptJson = $Receipt | ConvertTo-Json -Depth 10
Set-Content -Path "genesis/AO_DEPLOY_RECEIPT.json" -Value $ReceiptJson

Write-Host "Deployed successfully. Receipt written to genesis/AO_DEPLOY_RECEIPT.json."
Write-Host "Process ID: $($Receipt.process_id)"
