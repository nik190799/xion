-- xion_core.lua
-- Xion AO Core entry point

local state = require("state")
local commit_state = require("handlers.commit_state")
local attest = require("handlers.attest")

-- Initialize state with the deployer as the first authorized relay
if not _G.XION_INITIALIZED then
    -- In AOS, the process owner is available as Owner
    -- We assume the deployer is the Owner
    state.init(Owner or "DEPLOYER")
    _G.XION_INITIALIZED = true
end

-- Register handlers
Handlers.add(
    "commit-state",
    Handlers.utils.hasMatchingTag("Action", "commit-state"),
    function(msg)
        commit_state.handle(msg)
    end
)

Handlers.add(
    "attest",
    Handlers.utils.hasMatchingTag("Action", "attest"),
    function(msg)
        attest.handle(msg)
    end
)

print("Xion AO Core initialized.")
