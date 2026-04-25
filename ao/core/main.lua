-- ao/core/main.lua
-- Phase 6.1 AO Core Skeleton

local json = require("json")

-- State variables
StateTip = StateTip or { height = 0, root = string.rep("0", 64), prev = string.rep("0", 64) }
Attestations = Attestations or {}

-- Authorized Signers (stub for Phase 6.1, normally populated via authority lattice)
AuthorizedSigners = AuthorizedSigners or {
    ["hot-tier-address"] = true,
    ["warm-tier-address"] = true,
    -- Accept the owner of the process as authorized for the skeleton
    [Owner] = true
}

-- Constants
MAX_EVENT_WEIGHT = 100

-- Helper: Check authorization.
--
-- IMPORTANT for future contract maintainers: `msg.From` is the ID of whoever
-- *signed* the inbound DataItem. For an external owner-signed message that's
-- the owner's wallet address (which we accept via `[Owner] = true` above). For
-- a message produced by `Send({ Target = ao.id, ... })` from inside an `Eval`,
-- `msg.From == ao.id` (the process itself), which is NOT the owner and is NOT
-- in `AuthorizedSigners` — the message is rejected with `non_authorised_caller`
-- and the rejection is invisible from inside the REPL because no exception is
-- raised. This trap cost a half-day during the Phase 6.1.b seal: a `Send` from
-- inside `aos --run "Send({Target=ao.id,...})"` was silently rejected and the
-- operator-script wrote a receipt naming a process whose `StateTip` was still
-- `{ height=0, root=zeros }`. The fix is to send `Commit-State` (and any other
-- authorized action) externally, signed by the owner — see
-- `scripts/ao-localnet-send-commit-state.cjs` for the template, and
-- `docs/runbooks/AO_DEPLOY_LOCALNET.md` § "Lessons learned" for the full
-- write-up. When the authority lattice (Phase 6.2) populates `AuthorizedSigners`
-- with hot/warm-tier addresses, those addresses likewise must sign messages
-- *outside* the process; an Eval-driven `Send` will still hit this branch.
local function is_authorized(msg)
    return AuthorizedSigners[msg.From] == true
end

-- Handler: commit-state
Handlers.add("commit-state",
    Handlers.utils.hasMatchingTag("Action", "Commit-State"),
    function(msg)
        if not is_authorized(msg) then
            ao.send({ Target = msg.From, Action = "State-Rejection", Reason = "non_authorised_caller" })
            return
        end

        local tip_height = tonumber(msg.Tags["Tip-Height"])
        local state_root_sha256 = msg.Tags["State-Root-Sha256"]

        if not tip_height or not state_root_sha256 then
            ao.send({ Target = msg.From, Action = "State-Rejection", Reason = "missing_args" })
            return
        end

        if tip_height ~= StateTip.height + 1 then
            ao.send({ Target = msg.From, Action = "State-Rejection", Reason = "tip_height_skip", Expected = tostring(StateTip.height + 1) })
            return
        end

        if state_root_sha256 == StateTip.root then
            -- no-op for duplicate root
            return
        end

        -- State change
        StateTip.prev = StateTip.root
        StateTip.root = state_root_sha256
        StateTip.height = tip_height

        print("commit-state success. New height: " .. tostring(StateTip.height))
        ao.send({ Target = msg.From, Action = "State-Committed", Height = tostring(StateTip.height), Root = StateTip.root })
    end
)

-- Handler: attest
Handlers.add("attest",
    Handlers.utils.hasMatchingTag("Action", "Attest"),
    function(msg)
        if not is_authorized(msg) then
            ao.send({ Target = msg.From, Action = "Attest-Rejection", Reason = "non_authorised_caller" })
            return
        end

        local subject_address = msg.Tags["Subject-Address"]
        local event_kind = msg.Tags["Event-Kind"]
        local event_correlation_id = msg.Tags["Event-Correlation-Id"]
        local event_weight = tonumber(msg.Tags["Event-Weight"])
        local event_timestamp = tonumber(msg.Tags["Event-Timestamp"])

        if not subject_address or not event_kind or not event_correlation_id or not event_weight or not event_timestamp then
            ao.send({ Target = msg.From, Action = "Attest-Rejection", Reason = "missing_args" })
            return
        end

        if event_kind ~= "chat_turn" and event_kind ~= "proposal_engagement" and event_kind ~= "improvement_contribution" then
            ao.send({ Target = msg.From, Action = "Attest-Rejection", Reason = "invalid_event_kind" })
            return
        end

        if event_weight > MAX_EVENT_WEIGHT then
            ao.send({ Target = msg.From, Action = "Attest-Rejection", Reason = "weight_exceeds_cap" })
            return
        end

        if Attestations[event_correlation_id] then
            ao.send({ Target = msg.From, Action = "Attest-Rejection", Reason = "duplicate_correlation_id" })
            return
        end

        Attestations[event_correlation_id] = {
            subject = subject_address,
            kind = event_kind,
            weight = event_weight,
            timestamp = event_timestamp
        }

        print("attest success for " .. event_correlation_id)
        ao.send({ Target = msg.From, Action = "Attest-Success", CorrelationId = event_correlation_id })
    end
)
