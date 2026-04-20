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
    //   2: SECURITY             63B  (15%)
    //   3: TREASURY             42B  (10%)
    //   4: CREATOR_COMMISSIONS  42B  (10%)
    //   5: FOUNDATION_OPS       21B  (5%)
    //   6: GENESIS_HONOR        21B  (5%)
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
    // Governance controls (Tier-2+ decisions). These can SLOW the schedule but
    // cannot accelerate it. See `slowEra`, `pauseMinting`, `retirePool`.
    // -------------------------------------------------------------------------
    address public aoCoreAuthority; // the AO-Core-signed relay that routes mint calls
    bool    public mintingPaused;
    uint256[4] public eraSlowdownBps; // per-era slowdown in basis points (10000 = no slowdown, 5000 = 50% slower)

    event GenesisEmitted(uint256 amount);
    event ScheduledMint(uint8 indexed pool, address indexed to, uint256 amount, uint256 era);
    event EraSlowed(uint8 era, uint256 slowdownBps);
    event MintingPaused(bool paused);
    event PoolRetired(uint8 pool, uint256 remainingBurned);

    error NotAuthority();
    error GenesisAlreadyEmitted();
    error MintingIsPaused();
    error PoolExhausted(uint8 pool);
    error EraCapExceeded(uint8 era);
    error EraNotActive(uint8 era);
    error CannotAccelerate();
    error InvalidPool();

    modifier onlyAuthority() {
        if (msg.sender != aoCoreAuthority) revert NotAuthority();
        _;
    }

    constructor(address _token, address _aoCoreAuthority) {
        token = IXionToken(_token);
        aoCoreAuthority = _aoCoreAuthority;
        GENESIS_TIMESTAMP = block.timestamp;
        // All eraSlowdownBps default to 10000 (no slowdown).
        eraSlowdownBps = [uint256(10000), 10000, 10000, 10000];
    }

    // -------------------------------------------------------------------------
    // Emit the genesis allocation. Called ONCE at C-2 launch, routed through
    // the AO Core authority after C-2 gates have been verified. Distributes
    // across pools according to the predefined genesis distribution (fair-launch
    // pool receives ~40B initial, others receive proportional seeds). The
    // actual per-pool split for the 84B is set by the AO Core and passed here.
    // -------------------------------------------------------------------------
    function emitGenesis(address[7] calldata recipients, uint256[7] calldata amounts)
        external
        onlyAuthority
    {
        if (genesisEmitted) revert GenesisAlreadyEmitted();
        uint256 total;
        for (uint8 i = 0; i < 7; i++) {
            total += amounts[i];
            poolMinted[i] += amounts[i];
            if (poolMinted[i] > poolCap[i]) revert PoolExhausted(i);
            if (amounts[i] > 0) {
                token.mint(recipients[i], amounts[i]);
            }
        }
        require(total == GENESIS_ALLOC, "genesis total must equal 84B");
        genesisEmitted = true;
        emit GenesisEmitted(total);
    }

    // -------------------------------------------------------------------------
    // scheduledMint — the per-event mint path used by Service Earn, Security
    // Pool rewards, Witness bond returns, Creator Commissions, etc. Callable
    // only by the AO Core authority, which has verified the qualifying event
    // (e.g., user paid $X in USDC for a voice call → rebate Y XION from the
    // Service Earn pool).
    // -------------------------------------------------------------------------
    function scheduledMint(uint8 pool, address to, uint256 amount) external onlyAuthority {
        if (mintingPaused) revert MintingIsPaused();
        if (pool >= 7) revert InvalidPool();
        if (!genesisEmitted) revert EraNotActive(0);

        uint256 elapsed = block.timestamp - GENESIS_TIMESTAMP;
        uint8 era = _currentEra(elapsed);
        _enforceEraCap(era, amount);
        _enforceSlowdown(era, amount);

        poolMinted[pool] += amount;
        if (poolMinted[pool] > poolCap[pool]) revert PoolExhausted(pool);

        token.mint(to, amount);
        emit ScheduledMint(pool, to, amount, era);
    }

    // -------------------------------------------------------------------------
    // slowEra — Tier-2 governance action. Applies a slowdown factor to a given
    // era. Slowdown is expressed in basis points, where 10000 = no slowdown and
    // values < 10000 mean the effective per-era cap is reduced. CANNOT exceed
    // 10000; you cannot accelerate.
    // -------------------------------------------------------------------------
    function slowEra(uint8 era, uint256 newSlowdownBps) external onlyAuthority {
        if (era == 0 || era > 4) revert EraNotActive(era);
        if (newSlowdownBps > 10000) revert CannotAccelerate();
        if (newSlowdownBps > eraSlowdownBps[era - 1]) revert CannotAccelerate();
        eraSlowdownBps[era - 1] = newSlowdownBps;
        emit EraSlowed(era, newSlowdownBps);
    }

    // -------------------------------------------------------------------------
    // pauseMinting — Tier-1 emergency action. Freezes all scheduled mints for
    // up to 72 hours. Auto-sunsets; if governance wants to extend, it must
    // re-pause (logged).
    // -------------------------------------------------------------------------
    uint256 public pauseExpiresAt;

    function pauseMinting(uint256 durationSeconds) external onlyAuthority {
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
    function retirePool(uint8 pool) external onlyAuthority {
        if (pool >= 7) revert InvalidPool();
        uint256 remaining = poolCap[pool] - poolMinted[pool];
        poolCap[pool] = poolMinted[pool]; // cap frozen at current minted amount
        emit PoolRetired(pool, remaining);
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

    function _enforceSlowdown(uint8 era, uint256 amount) internal view {
        // Slowdown reduces the effective per-era cap. Here we re-check that
        // mintedInEraN * 10000 / eraSlowdownBps[era-1] <= original era cap,
        // which is algebraically equivalent to mintedInEraN <= eraCap * slowdownBps / 10000.
        uint256 bps = eraSlowdownBps[era - 1];
        uint256 effectiveCap;
        if (era == 1) effectiveCap = (ERA1_CAP * bps) / 10000;
        else if (era == 2) effectiveCap = (ERA2_CAP * bps) / 10000;
        else if (era == 3) effectiveCap = (ERA3_CAP * bps) / 10000;
        else if (era == 4) effectiveCap = (ERA4_CAP * bps) / 10000;
        else revert EraNotActive(era);

        uint256 mintedSoFar;
        if (era == 1) mintedSoFar = mintedInEra1;
        else if (era == 2) mintedSoFar = mintedInEra2;
        else if (era == 3) mintedSoFar = mintedInEra3;
        else mintedSoFar = mintedInEra4;

        require(mintedSoFar <= effectiveCap, "slowdown cap reached");
        amount; // silence unused
    }
}
