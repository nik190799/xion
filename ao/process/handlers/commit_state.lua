-- commit_state.lua
-- Handler: commit-state
-- Family: lifecycle

local state = require("state")
local abi = require("abi")

local commit_state = {}

function commit_state.handle(msg)
    -- Precondition: caller is hot-tier or warm-tier signer (authorized relay)
    if not state.is_authorized_relay(msg.From) then
        print("commit-state: non_authorised_caller")
        ao.send({
            Target = msg.From,
            Action = "STATE_REJECTION",
            Reason = "non_authorised_caller"
        })
        return
    end

    local tip_height = tonumber(msg.tip_height)
    local state_root_sha256 = msg.state_root_sha256

    -- Argument validation
    if not tip_height or not abi.is_uint64(tip_height) then
        print("commit-state: invalid_tip_height")
        ao.send({
            Target = msg.From,
            Action = "STATE_REJECTION",
            Reason = "invalid_tip_height"
        })
        return
    end

    if not state_root_sha256 or not abi.is_hex(state_root_sha256, 64) then
        print("commit-state: invalid_state_root_sha256")
        ao.send({
            Target = msg.From,
            Action = "STATE_REJECTION",
            Reason = "invalid_state_root_sha256"
        })
        return
    end

    -- Precondition: tip_height == current_tip_height + 1
    if tip_height ~= state.state_tip_height + 1 then
        print("commit-state: tip_height_skip")
        ao.send({
            Target = msg.From,
            Action = "STATE_REJECTION",
            Reason = "tip_height_skip",
            Expected = tostring(state.state_tip_height + 1),
            Actual = tostring(tip_height)
        })
        return
    end

    -- Precondition: state_root_sha256 != current_state_root
    if state_root_sha256 == state.state_root_sha256 then
        print("commit-state: duplicate_root")
        -- Failure mode: duplicate_root -> reject (no-op)
        -- The schema says no-op, so we don't emit a STATE_REJECTION row, just return
        return
    end

    -- State changes
    state.prev_state_root_sha256 = state.state_root_sha256
    state.state_root_sha256 = state_root_sha256
    state.state_tip_height = tip_height

    print("commit-state: OK, new height " .. tostring(tip_height))
    
    -- State tip emission
    ao.send({
        Target = msg.From,
        Action = "STATE_TIP_EMISSION",
        Height = tostring(state.state_tip_height),
        StateRoot = state.state_root_sha256,
        PrevStateRoot = state.prev_state_root_sha256
    })
end

return commit_state
