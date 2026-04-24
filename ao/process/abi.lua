-- abi.lua
-- Shared argument validation for Xion AO Core handlers

local abi = {}

function abi.is_hex(str, expected_len)
    if type(str) ~= "string" then return false end
    if expected_len and #str ~= expected_len then return false end
    return str:match("^[0-9a-fA-F]+$") ~= nil
end

function abi.is_uint64(val)
    local n = tonumber(val)
    return n ~= nil and n >= 0 and math.floor(n) == n
end

function abi.is_uint32(val)
    local n = tonumber(val)
    return n ~= nil and n >= 0 and n <= 4294967295 and math.floor(n) == n
end

return abi
