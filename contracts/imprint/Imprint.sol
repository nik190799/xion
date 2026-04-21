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
//    - The Attestor address is rotatable via the two-role timelock lattice
//      (KW-CONTRACTS-001 remediation; see Rotation lattice section below).
//
//  Slashing:
//    - The Attestor can slash a wallet's IMPRINT with a reason tag.
//    - Slashed amounts are permanently burned.
//    - Slash events are indexed for auditability.
//
//  Rotation lattice (KW-CONTRACTS-001):
//    Two separate authorities:
//      - `engagementAttestor` — operational; signs `attest` and `slash`.
//      - `governance` — constitutional; can rotate `engagementAttestor` and
//        can rotate itself.
//    Both rotations are two-phase propose/execute with a minimum delay:
//      - Attestor rotation: 7-day timelock, proposed and cancellable by
//        `governance`.
//      - Governance rotation: 30-day timelock, proposed and cancellable by
//        `governance` itself (which is expected to be a Cold-Root-gated
//        multisig with 3-of-5 Shamir custody per docs/13-OPERATIONS.md).
//    The lattice is documented in docs/04-ARCHITECTURE.md and
//    docs/13-OPERATIONS.md; the constitutional property is "every authority
//    held in this contract rotates on a publicly-visible timelock", not
//    "this specific address can never change", which would be a
//    single-key-loss bricking path.
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
    // Decay parameters: ~5% per year (≈ 42 basis-points per 30 days when
    // compounded 12.17 times/year). Matches docs/16-CURRENCY.md's documented
    // decay rate ("slowly decaying ... e.g., 5% per year, with a floor").
    // Changed from 200 BPS/30d (~21.5%/year) to 42 BPS/30d (~5%/year) as part
    // of KW-CONTRACTS-003 remediation; decay math:
    //   (1 - 0.0042)^12.17 ≈ 0.950  →  ~5% per year
    // -------------------------------------------------------------------------
    uint256 public constant DECAY_BPS_PER_30D = 42; // ~5% per year
    uint256 public constant DECAY_PERIOD = 30 days;

    // -------------------------------------------------------------------------
    // Authorization — rotation lattice (KW-CONTRACTS-001).
    // -------------------------------------------------------------------------
    address public engagementAttestor;
    address public governance;

    // Pending rotations. `eta` is the earliest block.timestamp at which the
    // proposed rotation can be executed. zero `eta` means "no pending rotation".
    address public pendingAttestor;
    uint256 public pendingAttestorEta;
    address public pendingGovernance;
    uint256 public pendingGovernanceEta;

    uint256 public constant ATTESTOR_ROTATION_DELAY = 7 days;
    uint256 public constant GOVERNANCE_ROTATION_DELAY = 30 days;

    // -------------------------------------------------------------------------
    // Events
    // -------------------------------------------------------------------------
    event Attested(address indexed to, uint256 amount, bytes32 indexed reasonTag, uint256 newBalance);
    event Slashed(address indexed from, uint256 amount, bytes32 indexed reasonTag, uint256 newBalance);
    event Locked(address indexed holder); // ERC-5192 spirit — emitted on first mint

    event AttestorRotationProposed(address indexed proposed, uint256 eta);
    event AttestorRotationExecuted(address indexed previous, address indexed current);
    event AttestorRotationCancelled(address indexed cancelled);
    event GovernanceRotationProposed(address indexed proposed, uint256 eta);
    event GovernanceRotationExecuted(address indexed previous, address indexed current);
    event GovernanceRotationCancelled(address indexed cancelled);

    error NotAttestor();
    error NotGovernance();
    error ZeroAddress();
    error InsufficientBalance();
    error AmountOverflow();
    error NoPendingRotation();
    error RotationNotMatured();

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

    modifier onlyGovernance() {
        if (msg.sender != governance) revert NotGovernance();
        _;
    }

    constructor(address _engagementAttestor, address _governance) {
        if (_engagementAttestor == address(0) || _governance == address(0)) revert ZeroAddress();
        engagementAttestor = _engagementAttestor;
        governance = _governance;
    }

    // -------------------------------------------------------------------------
    // Mint — called by the registered engagement attestor after verifying that
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
        // KW-CONTRACTS-004: explicit overflow check on the uint128 narrowing.
        if (newBal > type(uint128).max) revert AmountOverflow();

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
    // Rotation lattice — KW-CONTRACTS-001.
    //
    // Attestor rotation (7-day timelock, gated by `governance`):
    //   1. governance.proposeAttestorRotation(newAttestor)   → sets pending + eta
    //   2. wait ATTESTOR_ROTATION_DELAY
    //   3. anyone.executeAttestorRotation()                  → swaps attestor
    //
    // Governance rotation (30-day timelock, gated by `governance` itself):
    //   1. governance.proposeGovernanceRotation(newGovernance)
    //   2. wait GOVERNANCE_ROTATION_DELAY
    //   3. anyone.executeGovernanceRotation()
    //
    // Cancel paths are available while the rotation is still pending, to
    // handle the "signed the wrong address" case cleanly.
    // -------------------------------------------------------------------------
    function proposeAttestorRotation(address newAttestor) external onlyGovernance {
        if (newAttestor == address(0)) revert ZeroAddress();
        pendingAttestor = newAttestor;
        pendingAttestorEta = block.timestamp + ATTESTOR_ROTATION_DELAY;
        emit AttestorRotationProposed(newAttestor, pendingAttestorEta);
    }

    function cancelAttestorRotation() external onlyGovernance {
        if (pendingAttestor == address(0)) revert NoPendingRotation();
        address cancelled = pendingAttestor;
        pendingAttestor = address(0);
        pendingAttestorEta = 0;
        emit AttestorRotationCancelled(cancelled);
    }

    function executeAttestorRotation() external {
        if (pendingAttestor == address(0)) revert NoPendingRotation();
        if (block.timestamp < pendingAttestorEta) revert RotationNotMatured();
        address previous = engagementAttestor;
        address next = pendingAttestor;
        engagementAttestor = next;
        pendingAttestor = address(0);
        pendingAttestorEta = 0;
        emit AttestorRotationExecuted(previous, next);
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
    // is effectively small for governance purposes, and the rawAmount is
    // preserved untouched until the next mint/slash).
    //
    // KW-CONTRACTS-008 (gas-grenade decay loop): for the MVP we use a
    // straightforward loop; realistic worst case at launch is < 12 iterations.
    // A v2 contract may replace this with a closed-form fixed-point exp.
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
