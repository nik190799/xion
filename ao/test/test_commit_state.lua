-- test_commit_state.lua

package.path = package.path .. ";../process/?.lua;process/?.lua"
local harness = require("test.harness")

harness.setup()
_G.Owner = "DEPLOYER"
require("xion_core")

local state = require("state")

print("Running test_commit_state.lua...")

-- 1. Success case
local root1 = string.rep("1", 64)
harness.dispatch({
    From = "DEPLOYER",
    Action = "commit-state",
    tip_height = "1",
    state_root_sha256 = root1
})

harness.assert_equal(1, #_G.ao.outbox, "Should emit 1 message")
harness.assert_equal("STATE_TIP_EMISSION", _G.ao.outbox[1].Action)
harness.assert_equal("1", _G.ao.outbox[1].Height)
harness.assert_equal(root1, _G.ao.outbox[1].StateRoot)
harness.assert_equal(1, state.state_tip_height)
harness.assert_equal(root1, state.state_root_sha256)

_G.ao.outbox = {}

-- 2. Failure: non_authorised_caller
harness.dispatch({
    From = "ATTACKER",
    Action = "commit-state",
    tip_height = "2",
    state_root_sha256 = string.rep("2", 64)
})
harness.assert_equal(1, #_G.ao.outbox)
harness.assert_equal("STATE_REJECTION", _G.ao.outbox[1].Action)
harness.assert_equal("non_authorised_caller", _G.ao.outbox[1].Reason)
harness.assert_equal(1, state.state_tip_height)

_G.ao.outbox = {}

-- 3. Failure: tip_height_skip
harness.dispatch({
    From = "DEPLOYER",
    Action = "commit-state",
    tip_height = "3", -- skip 2
    state_root_sha256 = string.rep("3", 64)
})
harness.assert_equal(1, #_G.ao.outbox)
harness.assert_equal("STATE_REJECTION", _G.ao.outbox[1].Action)
harness.assert_equal("tip_height_skip", _G.ao.outbox[1].Reason)

_G.ao.outbox = {}

-- 4. Failure: duplicate_root
harness.dispatch({
    From = "DEPLOYER",
    Action = "commit-state",
    tip_height = "2",
    state_root_sha256 = root1 -- duplicate
})
harness.assert_equal(0, #_G.ao.outbox, "duplicate_root should be a no-op")

print("All commit_state tests passed!")
