-- ao/core/main.lua
-- Phase 6.1 AO Core Skeleton

local json = require("json")

-- State variables
StateTip = StateTip or { height = 0, root = string.rep("0", 64), prev = string.rep("0", 64) }
Attestations = Attestations or {}
AnchorBatches = AnchorBatches or {}
AuthorityRotations = AuthorityRotations or {}
AbdicationEvents = AbdicationEvents or {}
TreasurySpends = TreasurySpends or {}
RegistryUpdates = RegistryUpdates or {}
OutboundSpends = OutboundSpends or {}
ImprintSlashes = ImprintSlashes or {}
ProvisioningEvents = ProvisioningEvents or {}
SliceRoutes = SliceRoutes or {}
ImprovementSpends = ImprovementSpends or {}
ReserveDraws = ReserveDraws or {}
FoundationDonations = FoundationDonations or {}
HibernationEvents = HibernationEvents or {}
HibernationState = HibernationState or { active = false, reason = nil, entered_at = nil }

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

local function tag(msg, name)
    return msg.Tags[name]
end

local function is_hex(value, length)
    return type(value) == "string" and string.len(value) == length and string.match(value, "^[0-9a-f]+$") ~= nil
end

local function positive_number(value)
    local n = tonumber(value)
    if not n or n <= 0 then
        return nil
    end
    return n
end

local function non_negative_number(value)
    local n = tonumber(value)
    if not n or n < 0 then
        return nil
    end
    return n
end

local function require_tags(msg, names)
    for _, name in ipairs(names) do
        if not tag(msg, name) or tag(msg, name) == "" then
            return false
        end
    end
    return true
end

local function reject(msg, action, reason)
    ao.send({ Target = msg.From, Action = action, Reason = reason })
end

local function record_once(table_ref, key, value)
    if table_ref[key] ~= nil then
        return false
    end
    table_ref[key] = value
    return true
end

local function has_allowed_value(value, allowed)
    for _, candidate in ipairs(allowed) do
        if value == candidate then
            return true
        end
    end
    return false
end

-- Handler: rotate-authority
Handlers.add("rotate-authority",
    Handlers.utils.hasMatchingTag("Action", "Rotate-Authority"),
    function(msg)
        if not is_authorized(msg) then
            reject(msg, "Authority-Rejection", "non_authorised_caller")
            return
        end

        if not require_tags(msg, { "Tier", "Old-Address", "New-Address", "Rotation-Nonce", "Effective-Unix" }) then
            reject(msg, "Authority-Rejection", "missing_args")
            return
        end

        local tier = tag(msg, "Tier")
        local old_address = tag(msg, "Old-Address")
        local new_address = tag(msg, "New-Address")
        local rotation_nonce = tag(msg, "Rotation-Nonce")
        local effective_unix = tonumber(tag(msg, "Effective-Unix"))

        if not has_allowed_value(tier, { "hot", "warm", "cold", "witness" }) or not effective_unix then
            reject(msg, "Authority-Rejection", "invalid_args")
            return
        end

        if old_address == new_address then
            reject(msg, "Authority-Rejection", "no_rotation")
            return
        end

        if AuthorizedSigners[old_address] ~= true then
            reject(msg, "Authority-Rejection", "old_authority_unknown")
            return
        end

        if AuthorityRotations[rotation_nonce] ~= nil then
            reject(msg, "Authority-Rejection", "duplicate_rotation_nonce")
            return
        end

        AuthorizedSigners[old_address] = nil
        AuthorizedSigners[new_address] = true
        AuthorityRotations[rotation_nonce] = {
            tier = tier,
            old_address = old_address,
            new_address = new_address,
            effective_unix = effective_unix,
            rotated_by = msg.From
        }

        print("rotate-authority success for " .. tier .. " nonce " .. rotation_nonce)
        ao.send({
            Target = msg.From,
            Action = "Authority-Rotated",
            Tier = tier,
            ["Old-Address"] = old_address,
            ["New-Address"] = new_address,
            ["Rotation-Nonce"] = rotation_nonce
        })
    end
)

-- Handler: abdicate-tier
Handlers.add("abdicate-tier",
    Handlers.utils.hasMatchingTag("Action", "Abdicate-Tier"),
    function(msg)
        if not is_authorized(msg) then
            reject(msg, "Authority-Rejection", "non_authorised_caller")
            return
        end

        if not require_tags(msg, { "Tier", "Successor-Mechanism", "Milestone", "Abdication-Nonce", "Effective-Unix" }) then
            reject(msg, "Authority-Rejection", "missing_args")
            return
        end

        local tier = tag(msg, "Tier")
        local successor_mechanism = tag(msg, "Successor-Mechanism")
        local milestone = tag(msg, "Milestone")
        local abdication_nonce = tag(msg, "Abdication-Nonce")
        local effective_unix = tonumber(tag(msg, "Effective-Unix"))

        if not has_allowed_value(tier, { "hot", "warm", "cold", "operator", "witness" }) or not effective_unix then
            reject(msg, "Authority-Rejection", "invalid_args")
            return
        end

        if AbdicationEvents[abdication_nonce] ~= nil then
            reject(msg, "Authority-Rejection", "duplicate_abdication_nonce")
            return
        end

        AbdicationEvents[abdication_nonce] = {
            tier = tier,
            successor_mechanism = successor_mechanism,
            milestone = milestone,
            effective_unix = effective_unix,
            abdicated_by = msg.From
        }

        print("abdicate-tier success for " .. tier .. " nonce " .. abdication_nonce)
        ao.send({
            Target = msg.From,
            Action = "Tier-Abdicated",
            Tier = tier,
            ["Successor-Mechanism"] = successor_mechanism,
            Milestone = milestone,
            ["Abdication-Nonce"] = abdication_nonce
        })
    end
)

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

-- Handler: anchor-interaction-batch
Handlers.add("anchor-interaction-batch",
    Handlers.utils.hasMatchingTag("Action", "Anchor-Interaction-Batch"),
    function(msg)
        if not is_authorized(msg) then
            ao.send({ Target = msg.From, Action = "Anchor-Rejection", Reason = "non_authorised_caller" })
            return
        end

        local batch_root_sha256 = msg.Tags["Batch-Root-Sha256"]
        local batch_size = tonumber(msg.Tags["Batch-Size"])
        local period_start_unix = tonumber(msg.Tags["Period-Start-Unix"])
        local period_end_unix = tonumber(msg.Tags["Period-End-Unix"])
        local ledger_kind = msg.Tags["Ledger-Kind"]

        if not batch_root_sha256 or not batch_size or not period_start_unix or not period_end_unix or not ledger_kind then
            ao.send({ Target = msg.From, Action = "Anchor-Rejection", Reason = "missing_args" })
            return
        end

        if type(batch_root_sha256) ~= "string" or string.len(batch_root_sha256) ~= 64 or not string.match(batch_root_sha256, "^[0-9a-f]+$") then
            ao.send({ Target = msg.From, Action = "Anchor-Rejection", Reason = "invalid_args" })
            return
        end

        if batch_size <= 0 or period_end_unix <= period_start_unix then
            ao.send({ Target = msg.From, Action = "Anchor-Rejection", Reason = "invalid_args" })
            return
        end

        if ledger_kind ~= "request" and ledger_kind ~= "payment" and ledger_kind ~= "safety" then
            ao.send({ Target = msg.From, Action = "Anchor-Rejection", Reason = "invalid_args" })
            return
        end

        table.insert(AnchorBatches, {
            batch_root_sha256 = batch_root_sha256,
            batch_size = batch_size,
            period_start_unix = period_start_unix,
            period_end_unix = period_end_unix,
            ledger_kind = ledger_kind
        })

        print("anchor-interaction-batch success for " .. batch_root_sha256)
        ao.send({ Target = msg.From, Action = "Anchor-Recorded", ["Batch-Root-Sha256"] = batch_root_sha256 })
    end
)

-- Handler: route-slices
Handlers.add("route-slices",
    Handlers.utils.hasMatchingTag("Action", "Route-Slices"),
    function(msg)
        if not is_authorized(msg) then
            reject(msg, "Sustainability-Rejection", "non_authorised_caller")
            return
        end

        if not require_tags(msg, {
            "Payment-Id",
            "Gross-Amount",
            "Operations-Bps",
            "Improvement-Bps",
            "Reserve-Bps",
            "Foundation-Bps",
            "Rewards-Bps"
        }) then
            reject(msg, "Sustainability-Rejection", "missing_args")
            return
        end

        local payment_id = tag(msg, "Payment-Id")
        local gross_amount = positive_number(tag(msg, "Gross-Amount"))
        local operations_bps = non_negative_number(tag(msg, "Operations-Bps"))
        local improvement_bps = non_negative_number(tag(msg, "Improvement-Bps"))
        local reserve_bps = non_negative_number(tag(msg, "Reserve-Bps"))
        local foundation_bps = non_negative_number(tag(msg, "Foundation-Bps"))
        local rewards_bps = non_negative_number(tag(msg, "Rewards-Bps"))

        if not gross_amount or not operations_bps or not improvement_bps or not reserve_bps or not foundation_bps or not rewards_bps then
            reject(msg, "Sustainability-Rejection", "invalid_args")
            return
        end

        local total_bps = operations_bps + improvement_bps + reserve_bps + foundation_bps + rewards_bps
        if total_bps ~= 10000 then
            reject(msg, "Sustainability-Rejection", "slice_total_mismatch")
            return
        end

        if SliceRoutes[payment_id] ~= nil then
            reject(msg, "Sustainability-Rejection", "duplicate_payment_id")
            return
        end

        SliceRoutes[payment_id] = {
            gross_amount = gross_amount,
            operations_bps = operations_bps,
            improvement_bps = improvement_bps,
            reserve_bps = reserve_bps,
            foundation_bps = foundation_bps,
            rewards_bps = rewards_bps,
            routed_by = msg.From
        }

        print("route-slices success for " .. payment_id)
        ao.send({ Target = msg.From, Action = "Slices-Routed", ["Payment-Id"] = payment_id })
    end
)

-- Handler: improvement-spend
Handlers.add("improvement-spend",
    Handlers.utils.hasMatchingTag("Action", "Improvement-Spend"),
    function(msg)
        if not is_authorized(msg) then
            reject(msg, "Sustainability-Rejection", "non_authorised_caller")
            return
        end

        if not require_tags(msg, { "Proposal-Id", "Amount", "Recipient", "Purpose-Sha256" }) then
            reject(msg, "Sustainability-Rejection", "missing_args")
            return
        end

        local proposal_id = tag(msg, "Proposal-Id")
        local amount = positive_number(tag(msg, "Amount"))
        local recipient = tag(msg, "Recipient")
        local purpose_sha256 = tag(msg, "Purpose-Sha256")

        if not amount or not is_hex(purpose_sha256, 64) then
            reject(msg, "Sustainability-Rejection", "invalid_args")
            return
        end

        if ImprovementSpends[proposal_id] ~= nil then
            reject(msg, "Sustainability-Rejection", "duplicate_proposal_id")
            return
        end

        ImprovementSpends[proposal_id] = {
            amount = amount,
            recipient = recipient,
            purpose_sha256 = purpose_sha256,
            approved_by = msg.From
        }

        print("improvement-spend success for " .. proposal_id)
        ao.send({ Target = msg.From, Action = "Improvement-Spend-Approved", ["Proposal-Id"] = proposal_id })
    end
)

-- Handler: reserve-draw
Handlers.add("reserve-draw",
    Handlers.utils.hasMatchingTag("Action", "Reserve-Draw"),
    function(msg)
        if not is_authorized(msg) then
            reject(msg, "Sustainability-Rejection", "non_authorised_caller")
            return
        end

        if not require_tags(msg, { "Draw-Id", "Amount", "Runway-Days", "Purpose-Sha256" }) then
            reject(msg, "Sustainability-Rejection", "missing_args")
            return
        end

        local draw_id = tag(msg, "Draw-Id")
        local amount = positive_number(tag(msg, "Amount"))
        local runway_days = non_negative_number(tag(msg, "Runway-Days"))
        local purpose_sha256 = tag(msg, "Purpose-Sha256")

        if not amount or not runway_days or not is_hex(purpose_sha256, 64) then
            reject(msg, "Sustainability-Rejection", "invalid_args")
            return
        end

        if ReserveDraws[draw_id] ~= nil then
            reject(msg, "Sustainability-Rejection", "duplicate_draw_id")
            return
        end

        ReserveDraws[draw_id] = {
            amount = amount,
            runway_days = runway_days,
            purpose_sha256 = purpose_sha256,
            approved_by = msg.From
        }

        print("reserve-draw success for " .. draw_id)
        ao.send({ Target = msg.From, Action = "Reserve-Draw-Approved", ["Draw-Id"] = draw_id })
    end
)

-- Handler: accept-donation
Handlers.add("accept-donation",
    Handlers.utils.hasMatchingTag("Action", "Accept-Donation"),
    function(msg)
        if not is_authorized(msg) then
            reject(msg, "Sustainability-Rejection", "non_authorised_caller")
            return
        end

        if not require_tags(msg, { "Donation-Id", "Donor", "Amount-Usd", "Asset" }) then
            reject(msg, "Sustainability-Rejection", "missing_args")
            return
        end

        local donation_id = tag(msg, "Donation-Id")
        local donor = tag(msg, "Donor")
        local amount_usd = positive_number(tag(msg, "Amount-Usd"))
        local asset = tag(msg, "Asset")
        local imprint_credit = non_negative_number(tag(msg, "Imprint-Credit") or "0")

        if not amount_usd or not imprint_credit then
            reject(msg, "Sustainability-Rejection", "invalid_args")
            return
        end

        if FoundationDonations[donation_id] ~= nil then
            reject(msg, "Sustainability-Rejection", "duplicate_donation_id")
            return
        end

        FoundationDonations[donation_id] = {
            donor = donor,
            amount_usd = amount_usd,
            asset = asset,
            imprint_credit = imprint_credit,
            accepted_by = msg.From
        }

        print("accept-donation success for " .. donation_id)
        ao.send({ Target = msg.From, Action = "Donation-Accepted", ["Donation-Id"] = donation_id })
    end
)

-- Handler: enter-hibernation
Handlers.add("enter-hibernation",
    Handlers.utils.hasMatchingTag("Action", "Enter-Hibernation"),
    function(msg)
        if not is_authorized(msg) then
            reject(msg, "Sustainability-Rejection", "non_authorised_caller")
            return
        end

        if not require_tags(msg, { "Hibernation-Id", "Reason", "Entered-At-Unix" }) then
            reject(msg, "Sustainability-Rejection", "missing_args")
            return
        end

        local hibernation_id = tag(msg, "Hibernation-Id")
        local entered_at_unix = tonumber(tag(msg, "Entered-At-Unix"))

        if not entered_at_unix then
            reject(msg, "Sustainability-Rejection", "invalid_args")
            return
        end

        if HibernationState.active then
            reject(msg, "Sustainability-Rejection", "already_hibernating")
            return
        end

        HibernationState = { active = true, reason = tag(msg, "Reason"), entered_at = entered_at_unix }
        HibernationEvents[hibernation_id] = {
            action = "enter",
            reason = tag(msg, "Reason"),
            at_unix = entered_at_unix,
            submitted_by = msg.From
        }

        print("enter-hibernation success for " .. hibernation_id)
        ao.send({ Target = msg.From, Action = "Hibernation-Entered", ["Hibernation-Id"] = hibernation_id })
    end
)

-- Handler: exit-hibernation
Handlers.add("exit-hibernation",
    Handlers.utils.hasMatchingTag("Action", "Exit-Hibernation"),
    function(msg)
        if not is_authorized(msg) then
            reject(msg, "Sustainability-Rejection", "non_authorised_caller")
            return
        end

        if not require_tags(msg, { "Hibernation-Id", "Exit-Reason", "Exited-At-Unix" }) then
            reject(msg, "Sustainability-Rejection", "missing_args")
            return
        end

        local hibernation_id = tag(msg, "Hibernation-Id")
        local exited_at_unix = tonumber(tag(msg, "Exited-At-Unix"))

        if not exited_at_unix then
            reject(msg, "Sustainability-Rejection", "invalid_args")
            return
        end

        if not HibernationState.active then
            reject(msg, "Sustainability-Rejection", "not_hibernating")
            return
        end

        HibernationState = { active = false, reason = nil, entered_at = nil }
        HibernationEvents[hibernation_id] = {
            action = "exit",
            reason = tag(msg, "Exit-Reason"),
            at_unix = exited_at_unix,
            submitted_by = msg.From
        }

        print("exit-hibernation success for " .. hibernation_id)
        ao.send({ Target = msg.From, Action = "Hibernation-Exited", ["Hibernation-Id"] = hibernation_id })
    end
)

local function provision(msg, kind, required_tags)
    if not is_authorized(msg) then
        reject(msg, "Provisioning-Rejection", "non_authorised_caller")
        return
    end

    if not require_tags(msg, required_tags) then
        reject(msg, "Provisioning-Rejection", "missing_args")
        return
    end

    local provision_id = tag(msg, "Provision-Id")
    local budget_cap = positive_number(tag(msg, "Budget-Cap"))
    local target = tag(msg, "Target")
    local manifest_sha256 = tag(msg, "Manifest-Sha256")

    if not budget_cap or not is_hex(manifest_sha256, 64) then
        reject(msg, "Provisioning-Rejection", "invalid_args")
        return
    end

    if ProvisioningEvents[provision_id] ~= nil then
        reject(msg, "Provisioning-Rejection", "duplicate_provision_id")
        return
    end

    ProvisioningEvents[provision_id] = {
        kind = kind,
        target = target,
        budget_cap = budget_cap,
        manifest_sha256 = manifest_sha256,
        submitted_by = msg.From
    }

    print("provision-" .. kind .. " success for " .. provision_id)
    ao.send({
        Target = msg.From,
        Action = "Provisioning-Recorded",
        Kind = kind,
        ["Provision-Id"] = provision_id
    })
end

-- Handler: provision-relay
Handlers.add("provision-relay",
    Handlers.utils.hasMatchingTag("Action", "Provision-Relay"),
    function(msg)
        provision(msg, "relay", { "Provision-Id", "Target", "Budget-Cap", "Manifest-Sha256" })
    end
)

-- Handler: provision-inference
Handlers.add("provision-inference",
    Handlers.utils.hasMatchingTag("Action", "Provision-Inference"),
    function(msg)
        provision(msg, "inference", { "Provision-Id", "Target", "Budget-Cap", "Manifest-Sha256" })
    end
)

-- Handler: provision-storage
Handlers.add("provision-storage",
    Handlers.utils.hasMatchingTag("Action", "Provision-Storage"),
    function(msg)
        provision(msg, "storage", { "Provision-Id", "Target", "Budget-Cap", "Manifest-Sha256" })
    end
)

-- Handler: provision-bandwidth
Handlers.add("provision-bandwidth",
    Handlers.utils.hasMatchingTag("Action", "Provision-Bandwidth"),
    function(msg)
        provision(msg, "bandwidth", { "Provision-Id", "Target", "Budget-Cap", "Manifest-Sha256" })
    end
)

-- Handler: provision-witness
Handlers.add("provision-witness",
    Handlers.utils.hasMatchingTag("Action", "Provision-Witness"),
    function(msg)
        provision(msg, "witness", { "Provision-Id", "Target", "Budget-Cap", "Manifest-Sha256" })
    end
)

-- Handler: treasury-spend
Handlers.add("treasury-spend",
    Handlers.utils.hasMatchingTag("Action", "Treasury-Spend"),
    function(msg)
        if not is_authorized(msg) then
            reject(msg, "Treasury-Rejection", "non_authorised_caller")
            return
        end

        if not require_tags(msg, { "Spend-Id", "Amount", "Asset", "Recipient", "Purpose-Sha256" }) then
            reject(msg, "Treasury-Rejection", "missing_args")
            return
        end

        local spend_id = tag(msg, "Spend-Id")
        local amount = positive_number(tag(msg, "Amount"))
        local purpose_sha256 = tag(msg, "Purpose-Sha256")

        if not amount or not is_hex(purpose_sha256, 64) then
            reject(msg, "Treasury-Rejection", "invalid_args")
            return
        end

        if TreasurySpends[spend_id] ~= nil then
            reject(msg, "Treasury-Rejection", "duplicate_spend_id")
            return
        end

        TreasurySpends[spend_id] = {
            amount = amount,
            asset = tag(msg, "Asset"),
            recipient = tag(msg, "Recipient"),
            purpose_sha256 = purpose_sha256,
            approved_by = msg.From
        }

        print("treasury-spend success for " .. spend_id)
        ao.send({ Target = msg.From, Action = "Treasury-Spend-Approved", ["Spend-Id"] = spend_id })
    end
)

-- Handler: registry-update
Handlers.add("registry-update",
    Handlers.utils.hasMatchingTag("Action", "Registry-Update"),
    function(msg)
        if not is_authorized(msg) then
            reject(msg, "Registry-Rejection", "non_authorised_caller")
            return
        end

        if not require_tags(msg, { "Registry", "Entry-Id", "Entry-Sha256", "Update-Nonce" }) then
            reject(msg, "Registry-Rejection", "missing_args")
            return
        end

        local registry = tag(msg, "Registry")
        local entry_id = tag(msg, "Entry-Id")
        local entry_sha256 = tag(msg, "Entry-Sha256")
        local update_nonce = tag(msg, "Update-Nonce")

        if not has_allowed_value(registry, { "relay", "inference", "storage", "witness", "authority" }) or not is_hex(entry_sha256, 64) then
            reject(msg, "Registry-Rejection", "invalid_args")
            return
        end

        if RegistryUpdates[update_nonce] ~= nil then
            reject(msg, "Registry-Rejection", "duplicate_update_nonce")
            return
        end

        RegistryUpdates[update_nonce] = {
            registry = registry,
            entry_id = entry_id,
            entry_sha256 = entry_sha256,
            updated_by = msg.From
        }

        print("registry-update success for " .. registry .. " entry " .. entry_id)
        ao.send({ Target = msg.From, Action = "Registry-Updated", Registry = registry, ["Entry-Id"] = entry_id })
    end
)

-- Handler: spend
Handlers.add("spend",
    Handlers.utils.hasMatchingTag("Action", "Spend"),
    function(msg)
        if not is_authorized(msg) then
            reject(msg, "Spend-Rejection", "non_authorised_caller")
            return
        end

        if not require_tags(msg, { "Spend-Id", "Amount", "Asset", "Recipient", "Daily-Cap" }) then
            reject(msg, "Spend-Rejection", "missing_args")
            return
        end

        local spend_id = tag(msg, "Spend-Id")
        local amount = positive_number(tag(msg, "Amount"))
        local daily_cap = positive_number(tag(msg, "Daily-Cap"))

        if not amount or not daily_cap then
            reject(msg, "Spend-Rejection", "invalid_args")
            return
        end

        if amount > daily_cap then
            reject(msg, "Spend-Rejection", "daily_cap_exceeded")
            return
        end

        if OutboundSpends[spend_id] ~= nil then
            reject(msg, "Spend-Rejection", "duplicate_spend_id")
            return
        end

        OutboundSpends[spend_id] = {
            amount = amount,
            asset = tag(msg, "Asset"),
            recipient = tag(msg, "Recipient"),
            daily_cap = daily_cap,
            approved_by = msg.From
        }

        print("spend success for " .. spend_id)
        ao.send({ Target = msg.From, Action = "Spend-Approved", ["Spend-Id"] = spend_id })
    end
)

-- Handler: slash-imprint
Handlers.add("slash-imprint",
    Handlers.utils.hasMatchingTag("Action", "Slash-Imprint"),
    function(msg)
        if not is_authorized(msg) then
            reject(msg, "Imprint-Rejection", "non_authorised_caller")
            return
        end

        if not require_tags(msg, { "Slash-Id", "Subject-Address", "Amount", "Evidence-Sha256" }) then
            reject(msg, "Imprint-Rejection", "missing_args")
            return
        end

        local slash_id = tag(msg, "Slash-Id")
        local amount = positive_number(tag(msg, "Amount"))
        local evidence_sha256 = tag(msg, "Evidence-Sha256")

        if not amount or not is_hex(evidence_sha256, 64) then
            reject(msg, "Imprint-Rejection", "invalid_args")
            return
        end

        if ImprintSlashes[slash_id] ~= nil then
            reject(msg, "Imprint-Rejection", "duplicate_slash_id")
            return
        end

        ImprintSlashes[slash_id] = {
            subject_address = tag(msg, "Subject-Address"),
            amount = amount,
            evidence_sha256 = evidence_sha256,
            approved_by = msg.From
        }

        print("slash-imprint success for " .. slash_id)
        ao.send({ Target = msg.From, Action = "Imprint-Slashed", ["Slash-Id"] = slash_id })
    end
)
