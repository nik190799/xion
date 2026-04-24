-- harness.lua
-- Mock Handlers and ao globals for Lua tests

local harness = {}

function harness.setup()
    _G.ao = {
        send = function(msg)
            table.insert(_G.ao.outbox, msg)
        end,
        outbox = {}
    }

    _G.Handlers = {
        list = {},
        add = function(name, pattern, handle)
            table.insert(_G.Handlers.list, {name = name, pattern = pattern, handle = handle})
        end,
        utils = {
            hasMatchingTag = function(key, value)
                return function(msg)
                    return msg[key] == value
                end
            end
        }
    }

    -- Reset state
    package.loaded["state"] = nil
    local state = require("state")
    state.state_tip_height = 0
    state.state_root_sha256 = string.rep("0", 64)
    state.prev_state_root_sha256 = string.rep("0", 64)
    state.authorized_relays = {["DEPLOYER"] = true}
    state.attestations = {}
end

function harness.dispatch(msg)
    for _, handler in ipairs(_G.Handlers.list) do
        if handler.pattern(msg) then
            handler.handle(msg)
            return
        end
    end
    print("No handler found for message")
end

function harness.assert_equal(expected, actual, msg)
    if expected ~= actual then
        error(string.format("Assertion failed: %s (expected %s, got %s)", msg or "", tostring(expected), tostring(actual)))
    end
end

return harness
