// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

// =============================================================================
//  Imprint — Xion's soulbound reputation token.
//
//  Genesis-Locked Invariant 10:
//    Imprint is non-transferable forever.
//    This contract has NO transfer, transferFrom, approve, permit, delegate,
//    wrap, lend, or inherit function. Non-transferability is enforced by
//    *omission* of these functions, not by a boolean that could ever be
//    flipped. There is no governance path to add a transfer function.
//
//  Shape:
//    - Balance-based (fungible-style) for quantitative reputation.
//    - ERC-5192-spirit (not strict): we emit a contract-wide soulbound signal
//      via the `Locked(address)` event at first mint, but do not implement the
//      NFT-shaped tokenId surface because reputation is quantitative here.
//    - Decay is computed lazily on read; mints and reads update the decay
//      checkpoint.
//
//  Minting:
//    - Only the registered `engagementAttestor` can mint.
//    - The `mintReason` tag is required on every mint for audit.
//    - The Attestor address is set once at construction and cannot be changed
//      after the owner renounces. After renounce, minting authority is fixed
//      until the AO Core itself rotates its relay-auth key (handled upstream,
//      not at this layer).
//
//  Slashing:
//    - The Attestor can slash a wallet's IMPRINT with a reason tag.
//    - Slashed amounts are permanently burned.
//    - Slash events are indexed for auditability.
// =============================================================================

contract Imprint {
    string public constant name = "Imprint";
    string public constant symbol = "IMPRINT";
    uint8  public constant decimals = 18;

    // -------------------------------------------------------------------------
    // Balance checkpoint: amount + last-touched timestamp, used for decay math.
    // -------------------------------------------------------------------------
    struct Balance {
        uint128 rawAmount;   // amount at lastTouched, pre-decay-since-then
        uint64  lastTouched; // unix seconds
    }

    mapping(address => Balance) internal _balances;

    // Ever-minted total (not decreased by decay; decreased by slash/burn).
    uint256 public totalMinted;
    uint256 public totalSlashed;

    // -------------------------------------------------------------------------
    // Decay parameters: ~2% per 30 days, compounded continuously, applied on
    // read. Rate expressed in "basis-points per 30 days" = 200. A wallet that
    // was last touched more than ~10 years ago tends toward a residual floor
    // (we stop at a minimum of 1 wei per decimal to avoid dust math issues).
    // -------------------------------------------------------------------------
    uint256 public constant DECAY_BPS_PER_30D = 200; // 2%
    uint256 public constant DECAY_PERIOD = 30 days;

    // -------------------------------------------------------------------------
    // Authorization
    // -------------------------------------------------------------------------
    address public immutable engagementAttestor;

    // -------------------------------------------------------------------------
    // Events — intentionally NOT the ERC-20 Transfer/Approval set, to reduce
    // the risk of dapps mistakenly wiring IMPRINT into transfer pipelines.
    // -------------------------------------------------------------------------
    event Attested(address indexed to, uint256 amount, bytes32 indexed reasonTag, uint256 newBalance);
    event Slashed(address indexed from, uint256 amount, bytes32 indexed reasonTag, uint256 newBalance);
    event Locked(address indexed holder); // ERC-5192 spirit — emitted on first mint

    error NotAttestor();
    error ZeroAddress();
    error InsufficientBalance();

    // -------------------------------------------------------------------------
    // There is no `transfer`, `transferFrom`, `approve`, `permit`, `delegate`,
    // `increaseAllowance`, or `decreaseAllowance` function. Their ABSENCE is
    // the enforcement mechanism for Invariant 10.
    //
    // A hypothetical `upgrade` function is also absent. This contract is
    // non-upgradeable.
    // -------------------------------------------------------------------------

    modifier onlyAttestor() {
        if (msg.sender != engagementAttestor) revert NotAttestor();
        _;
    }

    constructor(address _engagementAttestor) {
        if (_engagementAttestor == address(0)) revert ZeroAddress();
        engagementAttestor = _engagementAttestor;
    }

    // -------------------------------------------------------------------------
    // Mint — called by the AO Core's engagement attestor after verifying that
    // a qualifying engagement event occurred (sustained thread, accepted
    // contribution, correct Witness report).
    //
    // `reasonTag` is a 32-byte identifier namespacing the earning class, e.g.,
    // keccak256("relationship_thread_month") or keccak256("accepted_skill_v3").
    // -------------------------------------------------------------------------
    function attest(address to, uint256 amount, bytes32 reasonTag) external onlyAttestor {
        if (to == address(0)) revert ZeroAddress();

        uint256 current = _decayedBalance(to);
        bool firstMint = (current == 0 && _balances[to].lastTouched == 0);
        uint256 newBal = current + amount;

        _balances[to] = Balance({
            rawAmount: uint128(newBal),
            lastTouched: uint64(block.timestamp)
        });
        totalMinted += amount;

        if (firstMint) {
            emit Locked(to);
        }
        emit Attested(to, amount, reasonTag, newBal);
    }

    // -------------------------------------------------------------------------
    // Slash — the Attestor can remove IMPRINT from a wallet when the Core's
    // anomaly detector has confirmed Sybil or similar abuse. Slashed amounts
    // are burned (not redistributed).
    // -------------------------------------------------------------------------
    function slash(address from, uint256 amount, bytes32 reasonTag) external onlyAttestor {
        uint256 current = _decayedBalance(from);
        if (amount > current) {
            amount = current; // clamp to balance
        }
        uint256 newBal = current - amount;
        _balances[from] = Balance({
            rawAmount: uint128(newBal),
            lastTouched: uint64(block.timestamp)
        });
        totalSlashed += amount;
        emit Slashed(from, amount, reasonTag, newBal);
    }

    // -------------------------------------------------------------------------
    // Public read — returns the decayed balance as of now.
    // -------------------------------------------------------------------------
    function balanceOf(address holder) external view returns (uint256) {
        return _decayedBalance(holder);
    }

    // -------------------------------------------------------------------------
    // ERC-5192 spirit: a single-arg `locked(address)` query indicating that
    // this holder's IMPRINT is soulbound. Always returns true for any address
    // holding any IMPRINT.
    // -------------------------------------------------------------------------
    function locked(address holder) external view returns (bool) {
        return _decayedBalance(holder) > 0;
    }

    // -------------------------------------------------------------------------
    // Internal: compute the decayed balance lazily. We apply DECAY_BPS_PER_30D
    // over each full 30-day period since lastTouched.
    //
    // Formula (approximate, discrete compounding):
    //   periods = (now - lastTouched) / DECAY_PERIOD
    //   decayed = raw * ((10000 - DECAY_BPS_PER_30D) / 10000) ^ periods
    //
    // We avoid on-chain exponentiation over arbitrary periods by capping at a
    // reasonable `periods` bound (240 periods ≈ 20 years; beyond that, balance
    // is effectively zero for governance purposes, and the rawAmount is
    // preserved untouched until the next mint/slash).
    //
    // For the MVP we use a straightforward loop; production optimization would
    // precompute a lookup table or use log-time exponentiation.
    // -------------------------------------------------------------------------
    function _decayedBalance(address holder) internal view returns (uint256) {
        Balance memory b = _balances[holder];
        if (b.rawAmount == 0) return 0;
        if (b.lastTouched == 0) return 0;

        uint256 elapsed = block.timestamp - b.lastTouched;
        if (elapsed < DECAY_PERIOD) return b.rawAmount;

        uint256 periods = elapsed / DECAY_PERIOD;
        if (periods > 240) periods = 240;

        uint256 amount = b.rawAmount;
        for (uint256 i = 0; i < periods; i++) {
            amount = (amount * (10000 - DECAY_BPS_PER_30D)) / 10000;
            if (amount == 0) break;
        }
        return amount;
    }

    // -------------------------------------------------------------------------
    // Explicit non-conformance markers. These functions revert if called, to
    // prevent dapps from silently assuming ERC-20 compatibility. The revert
    // messages are informational.
    // -------------------------------------------------------------------------
    function transfer(address, uint256) external pure returns (bool) {
        revert("IMPRINT: soulbound; no transfers (Invariant 10)");
    }

    function transferFrom(address, address, uint256) external pure returns (bool) {
        revert("IMPRINT: soulbound; no transfers (Invariant 10)");
    }

    function approve(address, uint256) external pure returns (bool) {
        revert("IMPRINT: soulbound; no approvals (Invariant 10)");
    }

    function allowance(address, address) external pure returns (uint256) {
        return 0;
    }

    // totalSupply reflects the net minted minus slashed, NOT the sum of
    // decayed balances. For the sum-of-decayed view, an off-chain indexer
    // aggregates balanceOf across all known holders. We return the "on-paper"
    // total for auditability.
    function totalSupply() external view returns (uint256) {
        return totalMinted - totalSlashed;
    }
}
