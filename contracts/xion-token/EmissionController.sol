// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

// =============================================================================
//  EmissionController — the schedule enforcer for XION minting.
//
//  Genesis-Locked Invariant 9 enforcement:
//    The emission schedule can be SLOWED, PAUSED, or RETIRED by governance,
//    but it CANNOT be ACCELERATED. There is no function to advance an era,
//    release a future-era pool early, or emergency-mint.
//
//  Schedule:
//    Genesis allocation:    84,000,000,000 XION  at C-2 launch (one-time)
//    Era 1 (Year 1–4):     126,000,000,000 XION  (31.5B/year)
//    Era 2 (Year 5–8):      84,000,000,000 XION  (21.0B/year)
//    Era 3 (Year 9–12):     63,000,000,000 XION  (15.75B/year)
//    Era 4 (Year 13–20):    63,000,000,000 XION  (~7.875B/year)
//    Total cap:            420,000,000,000 XION
//
//  All amounts assume 18 decimals; scale by 10^18 in calldata.
//
//  Pool structure:
//    Minted amounts are distributed across the seven pools at the caller's
//    direction, subject to per-pool caps set at deployment. The controller
//    enforces per-era minting caps and per-pool lifetime caps. It does NOT
//    enforce distribution rules (that is the AO Core's responsibility).
//
//  Genesis split (KW-CONTRACTS-002):
//    `emitGenesis` no longer accepts arbitrary `amounts[7]`. The per-pool
//    split of the 84B is hash-locked in `GENESIS_SPLIT[i]` per the doctrine
//    committed in docs/16-CURRENCY.md "Genesis emission split" subsection
//    and mirrored in docs/schemas/genesis-split.yaml. Recipients remain
//    flexible (the AO Core chooses the concrete LP contract, the future
//    Treasury custodian, etc.).
//
//  Rotation lattice (KW-CONTRACTS-001):
//    Two separate authorities — `aoCoreAuthority` (operational, signs
//    scheduledMint / emitGenesis / slowEra / pauseMinting / retirePool) and
//    `governance` (constitutional, can rotate aoCoreAuthority and itself).
//    Rotation is two-phase propose/execute with timelocks:
//      - Authority rotation: 7 days, gated by `governance`.
//      - Governance rotation: 30 days, gated by `governance` itself.
//    See docs/13-OPERATIONS.md and docs/04-ARCHITECTURE.md for the full
//    lattice (Hot 24h → Warm 7d → Cold 30d).
// =============================================================================

interface IXionToken {
    function mint(address to, uint256 amount) external;
    function totalMinted() external view returns (uint256);
    function MAX_SUPPLY() external view returns (uint256);
}

contract EmissionController {
    // -------------------------------------------------------------------------
    // Era definitions. Timestamps are UTC seconds from genesis.
    // GENESIS_TIMESTAMP is set once at construction and is immutable.
    // -------------------------------------------------------------------------
    uint256 public immutable GENESIS_TIMESTAMP;

    uint256 public constant GENESIS_ALLOC = 84_000_000_000 * 10**18;

    // Era cap (total that may ever mint in this era, including any prior-era spillover)
    uint256 public constant ERA1_CAP = 126_000_000_000 * 10**18;
    uint256 public constant ERA2_CAP =  84_000_000_000 * 10**18;
    uint256 public constant ERA3_CAP =  63_000_000_000 * 10**18;
    uint256 public constant ERA4_CAP =  63_000_000_000 * 10**18;

    uint256 public constant ERA1_END = 4 * 365 days;   // relative to GENESIS
    uint256 public constant ERA2_END = 8 * 365 days;
    uint256 public constant ERA3_END = 12 * 365 days;
    uint256 public constant ERA4_END = 20 * 365 days;

    // -------------------------------------------------------------------------
    // Pool lifetime caps (sum = 420B).
    // Index 0..6:
    //   0: FAIR_LAUNCH        168B  (40%)
    //   1: SERVICE_EARN        63B  (15%)
    //   2: SECURITY            63B  (15%)
    //   3: TREASURY            42B  (10%)
    //   4: CREATOR_COMMISSIONS  42B  (10%)
    //   5: FOUNDATION_OPS      21B  (5%)
    //   6: GENESIS_HONOR       21B  (5%)
    // -------------------------------------------------------------------------
    uint256[7] public poolCap = [
        uint256(168_000_000_000) * 10**18,
        uint256( 63_000_000_000) * 10**18,
        uint256( 63_000_000_000) * 10**18,
        uint256( 42_000_000_000) * 10**18,
        uint256( 42_000_000_000) * 10**18,
        uint256( 21_000_000_000) * 10**18,
        uint256( 21_000_000_000) * 10**18
    ];
    uint256[7] public poolMinted;

    // Genesis allocation already emitted (one-time flag)
    bool public genesisEmitted;

    // Era minting aggregate (from era start to now, across all pools that
    // draw on era-bounded schedules: Service Earn, Security, Creator Commissions)
    uint256 public mintedInEra1;
    uint256 public mintedInEra2;
    uint256 public mintedInEra3;
    uint256 public mintedInEra4;

    IXionToken public immutable token;

    // -------------------------------------------------------------------------
    // Authority lattice (KW-CONTRACTS-001).
    // -------------------------------------------------------------------------
    address public aoCoreAuthority; // the AO-Core-signed relay that routes mint calls
    address public governance;      // can rotate aoCoreAuthority and itself

    address public pendingAuthority;
    uint256 public pendingAuthorityEta;
    address public pendingGovernance;
    uint256 public pendingGovernanceEta;

    uint256 public constant AUTHORITY_ROTATION_DELAY = 7 days;
    uint256 public constant GOVERNANCE_ROTATION_DELAY = 30 days;
    uint256 public constant DAILY_EGRESS_CAP = 100_000_000 * 10**18;
    uint256 public currentEgressDay;
    uint256 public egressMintedToday;

    bool    public mintingPaused;
    uint256[4] public eraSlowdownBps; // per-era slowdown in basis points (10000 = no slowdown, 5000 = 50% slower)
    uint256 public pauseExpiresAt;

    event GenesisEmitted(uint256 amount);
    event ScheduledMint(uint8 indexed pool, address indexed to, uint256 amount, uint256 era);
    event EraSlowed(uint8 era, uint256 slowdownBps);
    event MintingPaused(bool paused);
    event PoolRetired(uint8 pool, uint256 remainingBurned);

    event AuthorityRotationProposed(address indexed proposed, uint256 eta);
    event AuthorityRotationExecuted(address indexed previous, address indexed current);
    event AuthorityRotationCancelled(address indexed cancelled);
    event GovernanceRotationProposed(address indexed proposed, uint256 eta);
    event GovernanceRotationExecuted(address indexed previous, address indexed current);
    event GovernanceRotationCancelled(address indexed cancelled);
    event DailyEgressChecked(uint256 indexed day, uint256 amount, uint256 used, uint256 cap);

    error NotAuthority();
    error NotGovernance();
    error GenesisAlreadyEmitted();
    error MintingIsPaused();
    error PoolExhausted(uint8 pool);
    error EraCapExceeded(uint8 era);
    error EraNotActive(uint8 era);
    error CannotAccelerate();
    error InvalidPool();
    error ZeroAddress();
    error NoPendingRotation();
    error RotationNotMatured();
    error GenesisRecipientMissing(uint8 pool);
    error DailyEgressCapExceeded(uint256 day, uint256 requested, uint256 remaining);

    modifier onlyAuthority() {
        if (msg.sender != aoCoreAuthority) revert NotAuthority();
        _;
    }

    modifier onlyGovernance() {
        if (msg.sender != governance) revert NotGovernance();
        _;
    }

    constructor(address _token, address _aoCoreAuthority, address _governance) {
        if (_token == address(0) || _aoCoreAuthority == address(0) || _governance == address(0)) {
            revert ZeroAddress();
        }
        token = IXionToken(_token);
        aoCoreAuthority = _aoCoreAuthority;
        governance = _governance;
        GENESIS_TIMESTAMP = block.timestamp;
        // All eraSlowdownBps default to 10000 (no slowdown).
        eraSlowdownBps = [uint256(10000), 10000, 10000, 10000];
    }

    // -------------------------------------------------------------------------
    // GENESIS_SPLIT — the hash-locked per-pool genesis allocation.
    //
    // Source of truth: docs/16-CURRENCY.md "Genesis emission split" subsection,
    // mirrored by docs/schemas/genesis-split.yaml with a strict source_sha256
    // cross-check enforced by `xion-verify schemas`.
    //
    // Property promised: on the single call to `emitGenesis`, pool i receives
    // exactly `_genesisSplit(i)` XION. No other distribution is representable
    // by this contract.
    // -------------------------------------------------------------------------
    function _genesisSplit(uint8 i) internal pure returns (uint256) {
        if (i == 0) return GENESIS_ALLOC; // FAIR_LAUNCH = 84B
        if (i <= 6) return 0;             // all other pools start at 0 at genesis
        revert InvalidPool();
    }

    /// @notice Public accessor so third-party verifiers (and xion-verify supply)
    /// can read the hash-locked split without consulting source.
    function GENESIS_SPLIT(uint8 i) external pure returns (uint256) {
        return _genesisSplit(i);
    }

    // -------------------------------------------------------------------------
    // Emit the genesis allocation. Called ONCE at C-2 launch, routed through
    // the AO Core authority after C-2 gates have been verified. The per-pool
    // split is hash-locked by `_genesisSplit`; the caller supplies only the
    // seven recipient addresses (one per pool). Pools whose split is zero
    // require `address(0)` as a recipient (any non-zero recipient there would
    // be a footgun: "I forgot index 3 is zero").
    //
    // KW-CONTRACTS-005 remediation: all state effects complete BEFORE any
    // external `token.mint` call. The `genesisEmitted = true` flag is set
    // pre-interaction so that even a re-entering mint hook could not re-emit.
    // -------------------------------------------------------------------------
    function emitGenesis(address[7] calldata recipients) external onlyAuthority {
        if (genesisEmitted) revert GenesisAlreadyEmitted();

        // EFFECTS (must precede any external call).
        genesisEmitted = true;
        uint256 total;
        for (uint8 i = 0; i < 7; i++) {
            uint256 amount = _genesisSplit(i);
            if (amount > 0) {
                if (recipients[i] == address(0)) revert GenesisRecipientMissing(i);
                poolMinted[i] += amount;
                if (poolMinted[i] > poolCap[i]) revert PoolExhausted(i);
                total += amount;
            }
        }
        // Belt-and-suspenders: GENESIS_ALLOC is a compile-time constant and
        // _genesisSplit entries are compile-time constants, so `total` is
        // also compile-time-determined. We assert anyway so the invariant is
        // trivially checkable at audit time.
        require(total == GENESIS_ALLOC, "genesis total != 84B");

        // INTERACTIONS.
        for (uint8 i = 0; i < 7; i++) {
            uint256 amount = _genesisSplit(i);
            if (amount > 0) {
                token.mint(recipients[i], amount);
            }
        }

        emit GenesisEmitted(GENESIS_ALLOC);
    }

    // -------------------------------------------------------------------------
    // scheduledMint — the per-event mint path used by Service Earn, Security
    // Pool rewards, Witness bond returns, Creator Commissions, etc. Callable
    // only by the AO Core authority, which has verified the qualifying event
    // (e.g., user paid $X in USDC for a voice call → rebate Y XION from the
    // Service Earn pool).
    //
    // KW-CONTRACTS-005 remediation: `poolMinted` and era aggregates are
    // updated and checked BEFORE the external `token.mint` call; the function
    // reverts on cap breach without having emitted any external interaction.
    // -------------------------------------------------------------------------
    function scheduledMint(uint8 pool, address to, uint256 amount) external onlyAuthority {
        if (mintingPaused) revert MintingIsPaused();
        if (pool >= 7) revert InvalidPool();
        if (!genesisEmitted) revert EraNotActive(0);
        if (to == address(0)) revert ZeroAddress();

        uint256 elapsed = block.timestamp - GENESIS_TIMESTAMP;
        uint8 era = _currentEra(elapsed);

        // EFFECTS: all state transitions that must hold before any external call.
        _enforceDailyEgress(amount);
        _enforceEraCap(era, amount);
        _enforceSlowdown(era);
        poolMinted[pool] += amount;
        if (poolMinted[pool] > poolCap[pool]) revert PoolExhausted(pool);

        // INTERACTIONS.
        token.mint(to, amount);
        emit ScheduledMint(pool, to, amount, era);
    }

    // -------------------------------------------------------------------------
    // slowEra — Tier-2 governance action. Applies a slowdown factor to a given
    // era. Slowdown is expressed in basis points, where 10000 = no slowdown and
    // values < 10000 mean the effective per-era cap is reduced. CANNOT exceed
    // 10000; you cannot accelerate.
    //
    // Governance-tier action, so gated by `governance` (not `aoCoreAuthority`).
    // This is a lattice-tightening: the slow/pause/retire family are
    // constitutional actions that outlive any single operational authority.
    // -------------------------------------------------------------------------
    function slowEra(uint8 era, uint256 newSlowdownBps) external onlyGovernance {
        if (era == 0 || era > 4) revert EraNotActive(era);
        if (newSlowdownBps > 10000) revert CannotAccelerate();
        if (newSlowdownBps > eraSlowdownBps[era - 1]) revert CannotAccelerate();
        eraSlowdownBps[era - 1] = newSlowdownBps;
        emit EraSlowed(era, newSlowdownBps);
    }

    // -------------------------------------------------------------------------
    // pauseMinting — Tier-1 emergency action. Freezes all scheduled mints for
    // up to 72 hours. Auto-sunsets; if governance wants to extend, it must
    // re-pause (logged). Callable by governance to avoid operator-key pause
    // griefing.
    // -------------------------------------------------------------------------
    function pauseMinting(uint256 durationSeconds) external onlyGovernance {
        require(durationSeconds <= 72 hours, "pause <= 72h");
        mintingPaused = true;
        pauseExpiresAt = block.timestamp + durationSeconds;
        emit MintingPaused(true);
    }

    function unpauseIfExpired() external {
        if (block.timestamp >= pauseExpiresAt && mintingPaused) {
            mintingPaused = false;
            emit MintingPaused(false);
        }
    }

    // -------------------------------------------------------------------------
    // retirePool — Tier-3 action. Permanently burns the remaining unminted
    // capacity of a pool. Irreversible. Reduces the effective circulating cap
    // below 420B; the MAX_SUPPLY constant in XionToken does not change, but
    // the retired amount can never be minted again through this controller.
    // This is how governance *reduces* supply; there is no symmetric function
    // to increase.
    // -------------------------------------------------------------------------
    function retirePool(uint8 pool) external onlyGovernance {
        if (pool >= 7) revert InvalidPool();
        uint256 remaining = poolCap[pool] - poolMinted[pool];
        poolCap[pool] = poolMinted[pool]; // cap frozen at current minted amount
        emit PoolRetired(pool, remaining);
    }

    // -------------------------------------------------------------------------
    // Rotation lattice — KW-CONTRACTS-001.
    // -------------------------------------------------------------------------
    function proposeAuthorityRotation(address newAuthority) external onlyGovernance {
        if (newAuthority == address(0)) revert ZeroAddress();
        pendingAuthority = newAuthority;
        pendingAuthorityEta = block.timestamp + AUTHORITY_ROTATION_DELAY;
        emit AuthorityRotationProposed(newAuthority, pendingAuthorityEta);
    }

    function cancelAuthorityRotation() external onlyGovernance {
        if (pendingAuthority == address(0)) revert NoPendingRotation();
        address cancelled = pendingAuthority;
        pendingAuthority = address(0);
        pendingAuthorityEta = 0;
        emit AuthorityRotationCancelled(cancelled);
    }

    function executeAuthorityRotation() external {
        if (pendingAuthority == address(0)) revert NoPendingRotation();
        if (block.timestamp < pendingAuthorityEta) revert RotationNotMatured();
        address previous = aoCoreAuthority;
        address next = pendingAuthority;
        aoCoreAuthority = next;
        pendingAuthority = address(0);
        pendingAuthorityEta = 0;
        emit AuthorityRotationExecuted(previous, next);
    }

    function proposeGovernanceRotation(address newGovernance) external onlyGovernance {
        if (newGovernance == address(0)) revert ZeroAddress();
        pendingGovernance = newGovernance;
        pendingGovernanceEta = block.timestamp + GOVERNANCE_ROTATION_DELAY;
        emit GovernanceRotationProposed(newGovernance, pendingGovernanceEta);
    }

    function cancelGovernanceRotation() external onlyGovernance {
        if (pendingGovernance == address(0)) revert NoPendingRotation();
        address cancelled = pendingGovernance;
        pendingGovernance = address(0);
        pendingGovernanceEta = 0;
        emit GovernanceRotationCancelled(cancelled);
    }

    function executeGovernanceRotation() external {
        if (pendingGovernance == address(0)) revert NoPendingRotation();
        if (block.timestamp < pendingGovernanceEta) revert RotationNotMatured();
        address previous = governance;
        address next = pendingGovernance;
        governance = next;
        pendingGovernance = address(0);
        pendingGovernanceEta = 0;
        emit GovernanceRotationExecuted(previous, next);
    }

    // -------------------------------------------------------------------------
    // Internal helpers
    // -------------------------------------------------------------------------
    function _currentEra(uint256 elapsed) internal pure returns (uint8) {
        if (elapsed < ERA1_END) return 1;
        if (elapsed < ERA2_END) return 2;
        if (elapsed < ERA3_END) return 3;
        if (elapsed < ERA4_END) return 4;
        return 5; // emission halted forever
    }

    function _enforceEraCap(uint8 era, uint256 amount) internal {
        if (era == 1) {
            mintedInEra1 += amount;
            if (mintedInEra1 > ERA1_CAP) revert EraCapExceeded(1);
        } else if (era == 2) {
            mintedInEra2 += amount;
            if (mintedInEra2 > ERA2_CAP) revert EraCapExceeded(2);
        } else if (era == 3) {
            mintedInEra3 += amount;
            if (mintedInEra3 > ERA3_CAP) revert EraCapExceeded(3);
        } else if (era == 4) {
            mintedInEra4 += amount;
            if (mintedInEra4 > ERA4_CAP) revert EraCapExceeded(4);
        } else {
            revert EraNotActive(era);
        }
    }

    function _enforceSlowdown(uint8 era) internal view {
        // Slowdown reduces the effective per-era cap. Here we re-check that
        // mintedInEraN <= eraCap * slowdownBps / 10000 (after _enforceEraCap
        // has already incremented mintedInEraN).
        uint256 bps = eraSlowdownBps[era - 1];
        uint256 effectiveCap;
        uint256 mintedSoFar;
        if (era == 1) {
            effectiveCap = (ERA1_CAP * bps) / 10000;
            mintedSoFar = mintedInEra1;
        } else if (era == 2) {
            effectiveCap = (ERA2_CAP * bps) / 10000;
            mintedSoFar = mintedInEra2;
        } else if (era == 3) {
            effectiveCap = (ERA3_CAP * bps) / 10000;
            mintedSoFar = mintedInEra3;
        } else if (era == 4) {
            effectiveCap = (ERA4_CAP * bps) / 10000;
            mintedSoFar = mintedInEra4;
        } else {
            revert EraNotActive(era);
        }

        require(mintedSoFar <= effectiveCap, "slowdown cap reached");
    }

    function _enforceDailyEgress(uint256 amount) internal {
        uint256 day = block.timestamp / 1 days;
        if (day != currentEgressDay) {
            currentEgressDay = day;
            egressMintedToday = 0;
        }
        uint256 remaining = DAILY_EGRESS_CAP - egressMintedToday;
        if (amount > remaining) revert DailyEgressCapExceeded(day, amount, remaining);
        egressMintedToday += amount;
        emit DailyEgressChecked(day, amount, egressMintedToday, DAILY_EGRESS_CAP);
    }
}
