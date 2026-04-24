-- state.lua
-- Xion AO Core state container

local state = {
    -- State-tip included
    state_tip_height = 0,
    state_root_sha256 = string.rep("0", 64),
    prev_state_root_sha256 = string.rep("0", 64),

    -- Checkpoint-only
    authorized_relays = {},
    budget_envelopes = {},
    governance_queue = {},
    revocation_registry = {},

    -- Attestations (Phase 6.1)
    attestations = {}
}

-- Initialize with the deployer as the first authorized relay for bootstrap
-- In a real deployment, this would be the founder's hot/warm tier signer
function state.init(deployer_address)
    state.authorized_relays[deployer_address] = true
end

function state.is_authorized_relay(address)
    return state.authorized_relays[address] == true
end

return state
