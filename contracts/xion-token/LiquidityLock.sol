// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

// =============================================================================
//  LiquidityLock — the 10-year liquidity-lock contract for the XION fair-launch
//  bonding-curve LP tokens.
//
//  Purpose:
//    The fair-launch pool (168B XION, 40% of supply) is paired with USDC on a
//    Virtuals-style bonding curve. The LP tokens minted by that pairing are
//    transferred to this contract at deployment and cannot be withdrawn for
//    10 years. This makes rug-pulling the liquidity structurally impossible.
//
//  Properties:
//    - No owner. Constructor sets the beneficiary once; cannot change.
//    - No admin. No pause. No upgrade. No emergency withdraw.
//    - Unlock timestamp is immutable after construction.
//    - The beneficiary address is typically the AO Core treasury-signing
//      multisig, but the address could be a "burn+redeploy" sink; the contract
//      does not assume.
//    - After unlock, only the beneficiary can call `withdraw`. If the
//      beneficiary address is lost, the LP tokens are effectively burned.
//
//  Out of scope:
//    This contract holds LP tokens and has exactly one exit path (`withdraw`
//    after `unlockTimestamp`, callable only by `beneficiary`). It has no
//    fee-claim, no partial-withdraw, no rebalancing, no hook surface. Any
//    forward-looking discussion of LP fee policy lives in
//    `LIQUIDITY_LOCK_NOTES.md`, not in this source file, to keep the
//    contract's surface as small as the property it promises.
//    (KW-CONTRACTS-006 remediation.)
// =============================================================================

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract LiquidityLock {
    IERC20 public immutable lpToken;
    address public immutable beneficiary;
    uint256 public immutable unlockTimestamp;

    event Locked(address indexed lpToken, uint256 amount, uint256 unlockAt);
    event Withdrawn(address indexed to, uint256 amount);

    error NotYetUnlocked(uint256 unlockAt, uint256 current);
    error NotBeneficiary();
    error ZeroAddress();
    error UnlockInPast();

    constructor(address _lpToken, address _beneficiary, uint256 _unlockTimestamp) {
        if (_lpToken == address(0) || _beneficiary == address(0)) revert ZeroAddress();
        if (_unlockTimestamp <= block.timestamp) revert UnlockInPast();
        lpToken = IERC20(_lpToken);
        beneficiary = _beneficiary;
        unlockTimestamp = _unlockTimestamp;
        emit Locked(_lpToken, 0, _unlockTimestamp);
    }

    // -------------------------------------------------------------------------
    // Withdraw — only callable by the beneficiary, only after unlock. No
    // partial withdrawal to specific addresses; the LP tokens are sent to the
    // beneficiary address of record, exactly as declared at deployment.
    // -------------------------------------------------------------------------
    function withdraw() external {
        if (msg.sender != beneficiary) revert NotBeneficiary();
        if (block.timestamp < unlockTimestamp) {
            revert NotYetUnlocked(unlockTimestamp, block.timestamp);
        }
        uint256 bal = lpToken.balanceOf(address(this));
        require(bal > 0, "nothing to withdraw");
        require(lpToken.transfer(beneficiary, bal), "transfer failed");
        emit Withdrawn(beneficiary, bal);
    }

    // -------------------------------------------------------------------------
    // Read-only helpers for public verification.
    // -------------------------------------------------------------------------
    function timeUntilUnlock() external view returns (uint256) {
        if (block.timestamp >= unlockTimestamp) return 0;
        return unlockTimestamp - block.timestamp;
    }

    function heldLpAmount() external view returns (uint256) {
        return lpToken.balanceOf(address(this));
    }
}
