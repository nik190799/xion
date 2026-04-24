-- attest.lua
-- Handler: attest
-- Family: lifecycle

local state = require("state")
local abi = require("abi")

local attest = {}

-- Constant MAX_EVENT_WEIGHT from doctrine
local MAX_EVENT_WEIGHT = 1000

local ALLOWED_EVENT_KINDS = {
    chat_turn = true,
    proposal_engagement = true,
    improvement_contribution = true
}

function attest.handle(msg)
    -- Precondition: caller is hot-tier or warm-tier signer
    if not state.is_authorized_relay(msg.From) then
        print("attest: non_authorised_caller")
        ao.send({
            Target = msg.From,
            Action = "ATTEST_REJECTION",
            Reason = "non_authorised_caller"
        })
        return
    end

    local subject_address = msg.subject_address
    local event_kind = msg.event_kind
    local event_correlation_id = msg.event_correlation_id
    local event_weight = tonumber(msg.event_weight)
    local event_timestamp = tonumber(msg.event_timestamp)

    -- Argument validation
    if not subject_address or not abi.is_hex(subject_address, 40) then
        print("attest: invalid_subject_address")
        ao.send({Target = msg.From, Action = "ATTEST_REJECTION", Reason = "invalid_subject_address"})
        return
    end

    if not event_kind or not ALLOWED_EVENT_KINDS[event_kind] then
        print("attest: invalid_event_kind")
        ao.send({Target = msg.From, Action = "ATTEST_REJECTION", Reason = "invalid_event_kind"})
        return
    end

    if not event_correlation_id or not abi.is_hex(event_correlation_id, 32) then
        print("attest: invalid_event_correlation_id")
        ao.send({Target = msg.From, Action = "ATTEST_REJECTION", Reason = "invalid_event_correlation_id"})
        return
    end

    if not event_weight or not abi.is_uint32(event_weight) then
        print("attest: invalid_event_weight")
        ao.send({Target = msg.From, Action = "ATTEST_REJECTION", Reason = "invalid_event_weight"})
        return
    end

    if not event_timestamp or not abi.is_uint64(event_timestamp) then
        print("attest: invalid_event_timestamp")
        ao.send({Target = msg.From, Action = "ATTEST_REJECTION", Reason = "invalid_event_timestamp"})
        return
    end

    -- Precondition: event_weight <= MAX_EVENT_WEIGHT
    if event_weight > MAX_EVENT_WEIGHT then
        print("attest: weight_exceeds_cap")
        ao.send({Target = msg.From, Action = "ATTEST_REJECTION", Reason = "weight_exceeds_cap"})
        return
    end

    -- Precondition: duplicate_correlation_id -> reject
    if state.attestations[event_correlation_id] then
        print("attest: duplicate_correlation_id")
        ao.send({Target = msg.From, Action = "ATTEST_REJECTION", Reason = "duplicate_correlation_id"})
        return
    end

    -- State changes
    state.attestations[event_correlation_id] = {
        subject = subject_address,
        kind = event_kind,
        weight = event_weight,
        timestamp = event_timestamp
    }

    print("attest: OK, correlation_id " .. event_correlation_id)
    
    ao.send({
        Target = msg.From,
        Action = "ATTEST_SUCCESS",
        CorrelationId = event_correlation_id
    })
end

return attest
