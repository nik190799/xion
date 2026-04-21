// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {LiquidityLock} from "../xion-token/LiquidityLock.sol";

/// Minimal ERC-20 stand-in for LP-token tests. Matches the IERC20 shape that
/// LiquidityLock consumes (transfer + balanceOf).
contract MockLP {
    mapping(address => uint256) public balanceOf;

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "MockLP: insufficient");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}

/// Mock LP that returns false from transfer (non-reverting bad-token pattern),
/// used to confirm LiquidityLock surfaces the failure.
contract FailingLP {
    mapping(address => uint256) public balanceOf;

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
    }

    function transfer(address, uint256) external pure returns (bool) {
        return false;
    }
}

// =============================================================================
// LiquidityLock.t.sol
//
// Covers:
//   - Constructor: zero-address guards, past-unlock guard, state set.
//   - withdraw before unlock reverts NotYetUnlocked.
//   - withdraw by non-beneficiary reverts NotBeneficiary.
//   - withdraw after unlock happy path; heldLpAmount -> 0 after.
//   - withdraw with zero balance reverts "nothing to withdraw".
//   - timeUntilUnlock monotonically decreases; 0 after unlock.
// =============================================================================
contract LiquidityLockTest is Test {
    MockLP internal lp;
    LiquidityLock internal lock;

    address internal constant BENEFICIARY = address(0xBABE);
    uint256 internal unlockAt;

    function setUp() public {
        lp = new MockLP();
        unlockAt = block.timestamp + 10 * 365 days;
        lock = new LiquidityLock(address(lp), BENEFICIARY, unlockAt);
    }

    function test_constructor_rejectsZeroLp() public {
        vm.expectRevert(LiquidityLock.ZeroAddress.selector);
        new LiquidityLock(address(0), BENEFICIARY, unlockAt);
    }

    function test_constructor_rejectsZeroBeneficiary() public {
        vm.expectRevert(LiquidityLock.ZeroAddress.selector);
        new LiquidityLock(address(lp), address(0), unlockAt);
    }

    function test_constructor_rejectsPastUnlock() public {
        vm.expectRevert(LiquidityLock.UnlockInPast.selector);
        new LiquidityLock(address(lp), BENEFICIARY, block.timestamp);
    }

    function test_constructor_state() public view {
        assertEq(address(lock.lpToken()), address(lp));
        assertEq(lock.beneficiary(), BENEFICIARY);
        assertEq(lock.unlockTimestamp(), unlockAt);
    }

    function test_withdraw_beforeUnlock_reverts() public {
        lp.mint(address(lock), 100 ether);
        vm.expectRevert(abi.encodeWithSelector(LiquidityLock.NotYetUnlocked.selector, unlockAt, block.timestamp));
        vm.prank(BENEFICIARY);
        lock.withdraw();
    }

    function test_withdraw_nonBeneficiary_reverts() public {
        vm.expectRevert(LiquidityLock.NotBeneficiary.selector);
        vm.prank(address(0xDEAD));
        lock.withdraw();
    }

    function test_withdraw_afterUnlock_happyPath() public {
        lp.mint(address(lock), 100 ether);
        vm.warp(unlockAt);
        vm.expectEmit(true, false, false, true);
        emit LiquidityLock.Withdrawn(BENEFICIARY, 100 ether);
        vm.prank(BENEFICIARY);
        lock.withdraw();

        assertEq(lp.balanceOf(BENEFICIARY), 100 ether);
        assertEq(lock.heldLpAmount(), 0);
    }

    function test_withdraw_zeroBalance_reverts() public {
        vm.warp(unlockAt);
        vm.expectRevert("nothing to withdraw");
        vm.prank(BENEFICIARY);
        lock.withdraw();
    }

    function test_timeUntilUnlock() public {
        // At t=0 we're 10 years away.
        assertEq(lock.timeUntilUnlock(), 10 * 365 days);

        vm.warp(unlockAt - 1);
        assertEq(lock.timeUntilUnlock(), 1);

        vm.warp(unlockAt);
        assertEq(lock.timeUntilUnlock(), 0);

        vm.warp(unlockAt + 100);
        assertEq(lock.timeUntilUnlock(), 0);
    }

    function test_heldLpAmount_tracks() public {
        assertEq(lock.heldLpAmount(), 0);
        lp.mint(address(lock), 42 ether);
        assertEq(lock.heldLpAmount(), 42 ether);
    }

    function test_withdraw_transferFailurePropagates() public {
        FailingLP badLp = new FailingLP();
        LiquidityLock badLock = new LiquidityLock(address(badLp), BENEFICIARY, unlockAt);
        badLp.mint(address(badLock), 1 ether);
        vm.warp(unlockAt);

        vm.expectRevert("transfer failed");
        vm.prank(BENEFICIARY);
        badLock.withdraw();
    }
}
