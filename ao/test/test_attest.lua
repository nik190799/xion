-- test_attest.lua

package.path = package.path .. ";../process/?.lua;process/?.lua"
local harness = require("test.harness")

harness.setup()
_G.Owner = "DEPLOYER"
require("xion_core")

local state = require("state")

print("Running test_attest.lua...")

local subject = string.rep("a", 40)
local corr_id = string.rep("b", 64)

-- 1. Success case
harness.dispatch({
    From = "DEPLOYER",
    Action = "attest",
    subject_address = subject,
    event_kind = "chat_turn",
    event_correlation_id = corr_id,
    event_weight = "10",
    event_timestamp = "123456789"
})

harness.assert_equal(1, #_G.ao.outbox)
harness.assert_equal("ATTEST_SUCCESS", _G.ao.outbox[1].Action)
harness.assert_equal(corr_id, _G.ao.outbox[1].CorrelationId)

local att = state.attestations[corr_id]
harness.assert_equal(subject, att.subject)
harness.assert_equal("chat_turn", att.kind)
harness.assert_equal(10, att.weight)
harness.assert_equal(123456789, att.timestamp)

_G.ao.outbox = {}

-- 2. Failure: non_authorised_caller
harness.dispatch({
    From = "ATTACKER",
    Action = "attest",
    subject_address = subject,
    event_kind = "chat_turn",
    event_correlation_id = string.rep("c", 64),
    event_weight = "10",
    event_timestamp = "123456789"
})
harness.assert_equal(1, #_G.ao.outbox)
harness.assert_equal("ATTEST_REJECTION", _G.ao.outbox[1].Action)
harness.assert_equal("non_authorised_caller", _G.ao.outbox[1].Reason)

_G.ao.outbox = {}

-- 3. Failure: invalid_event_kind
harness.dispatch({
    From = "DEPLOYER",
    Action = "attest",
    subject_address = subject,
    event_kind = "invalid_kind",
    event_correlation_id = string.rep("c", 64),
    event_weight = "10",
    event_timestamp = "123456789"
})
harness.assert_equal(1, #_G.ao.outbox)
harness.assert_equal("ATTEST_REJECTION", _G.ao.outbox[1].Action)
harness.assert_equal("invalid_event_kind", _G.ao.outbox[1].Reason)

_G.ao.outbox = {}

-- 4. Failure: weight_exceeds_cap
harness.dispatch({
    From = "DEPLOYER",
    Action = "attest",
    subject_address = subject,
    event_kind = "chat_turn",
    event_correlation_id = string.rep("c", 64),
    event_weight = "1001", -- Max is 1000
    event_timestamp = "123456789"
})
harness.assert_equal(1, #_G.ao.outbox)
harness.assert_equal("ATTEST_REJECTION", _G.ao.outbox[1].Action)
harness.assert_equal("weight_exceeds_cap", _G.ao.outbox[1].Reason)

_G.ao.outbox = {}

-- 5. Failure: duplicate_correlation_id
harness.dispatch({
    From = "DEPLOYER",
    Action = "attest",
    subject_address = subject,
    event_kind = "chat_turn",
    event_correlation_id = corr_id, -- Used in success case
    event_weight = "10",
    event_timestamp = "123456789"
})
harness.assert_equal(1, #_G.ao.outbox)
harness.assert_equal("ATTEST_REJECTION", _G.ao.outbox[1].Action)
harness.assert_equal("duplicate_correlation_id", _G.ao.outbox[1].Reason)

print("All attest tests passed!")
