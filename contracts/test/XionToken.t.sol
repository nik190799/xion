// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {XionToken} from "../xion-token/XionToken.sol";

// =============================================================================
// XionToken.t.sol
//
// Covers:
//   - Constructor zero-address guard.
//   - setMinter gating: only owner, exactly once.
//   - mint gating: only minter.
//   - mint cap: respects MAX_SUPPLY (Invariant 8).
//   - mint respects remainingMintCapacity view.
//   - burn + burnFrom reduce balance but NOT totalMinted (lifetime cap).
//   - renounceOwnership disables setMinter.
// =============================================================================
contract XionTokenTest is Test {
    XionToken internal xion;
    address internal constant FOUNDATION = address(0xF00D);
    address internal constant MINTER = address(0xB111);
    address internal constant USER = address(0xA1);

    function setUp() public {
        xion = new XionToken(FOUNDATION);
    }

    function test_constructor_rejectsZeroFoundation() public {
        // OZ v5's Ownable reverts with OwnableInvalidOwner(address(0)) before
        // XionToken's own ZeroAddress guard is reached. Either is a valid
        // failure path; we assert on the OZ-native selector because that is
        // what the deployed bytecode actually throws.
        vm.expectRevert(
            abi.encodeWithSignature("OwnableInvalidOwner(address)", address(0))
        );
        new XionToken(address(0));
    }

    function test_setMinter_onlyOwner() public {
        vm.expectRevert();
        vm.prank(USER);
        xion.setMinter(MINTER);
    }

    function test_setMinter_zeroAddressRejected() public {
        vm.expectRevert(XionToken.ZeroAddress.selector);
        vm.prank(FOUNDATION);
        xion.setMinter(address(0));
    }

    function test_setMinter_onlyOnce() public {
        vm.prank(FOUNDATION);
        xion.setMinter(MINTER);

        vm.expectRevert(XionToken.MinterAlreadySet.selector);
        vm.prank(FOUNDATION);
        xion.setMinter(address(0xDEAD));
    }

    function test_setMinter_emitsEvent() public {
        vm.expectEmit(true, true, false, true);
        emit XionToken.MinterSet(address(0), MINTER);
        vm.prank(FOUNDATION);
        xion.setMinter(MINTER);
    }

    function test_mint_onlyMinter() public {
        vm.prank(FOUNDATION);
        xion.setMinter(MINTER);

        vm.expectRevert(XionToken.NotMinter.selector);
        vm.prank(USER);
        xion.mint(USER, 1 ether);
    }

    function test_mint_rejectsZeroRecipient() public {
        vm.prank(FOUNDATION);
        xion.setMinter(MINTER);

        vm.expectRevert(XionToken.ZeroAddress.selector);
        vm.prank(MINTER);
        xion.mint(address(0), 1 ether);
    }

    function test_mint_happyPath() public {
        vm.prank(FOUNDATION);
        xion.setMinter(MINTER);

        vm.expectEmit(true, false, false, true);
        emit XionToken.MintedBySchedule(USER, 1000 ether, 1000 ether);
        vm.prank(MINTER);
        xion.mint(USER, 1000 ether);

        assertEq(xion.balanceOf(USER), 1000 ether);
        assertEq(xion.totalMinted(), 1000 ether);
        assertEq(xion.remainingMintCapacity(), xion.MAX_SUPPLY() - 1000 ether);
    }

    function test_mint_respectsMaxSupply() public {
        vm.prank(FOUNDATION);
        xion.setMinter(MINTER);

        uint256 cap = xion.MAX_SUPPLY();
        vm.prank(MINTER);
        xion.mint(USER, cap);
        assertEq(xion.totalMinted(), cap);

        vm.expectRevert(abi.encodeWithSelector(XionToken.ExceedsMaxSupply.selector, 1, 0));
        vm.prank(MINTER);
        xion.mint(USER, 1);
    }

    function test_burn_doesNotReopenMintCapacity() public {
        vm.prank(FOUNDATION);
        xion.setMinter(MINTER);
        vm.prank(MINTER);
        xion.mint(USER, 100 ether);

        vm.prank(USER);
        xion.burn(40 ether);

        // balance decreases; totalMinted is lifetime (unchanged).
        assertEq(xion.balanceOf(USER), 60 ether);
        assertEq(xion.totalMinted(), 100 ether);

        // Only (MAX - 100) remaining even after the burn.
        assertEq(xion.remainingMintCapacity(), xion.MAX_SUPPLY() - 100 ether);
    }

    function test_burnFrom_requiresApproval() public {
        vm.prank(FOUNDATION);
        xion.setMinter(MINTER);
        vm.prank(MINTER);
        xion.mint(USER, 100 ether);

        vm.prank(USER);
        xion.approve(address(this), 50 ether);

        xion.burnFrom(USER, 50 ether);
        assertEq(xion.balanceOf(USER), 50 ether);
        assertEq(xion.totalMinted(), 100 ether); // unchanged
    }

    function test_renounceOwnership_disablesSetMinter() public {
        vm.prank(FOUNDATION);
        xion.renounceOwnership();

        vm.expectRevert();
        vm.prank(FOUNDATION);
        xion.setMinter(MINTER);
    }

    function test_erc20_metadata() public view {
        assertEq(xion.name(), "Xion");
        assertEq(xion.symbol(), "XION");
        assertEq(xion.decimals(), 18);
        assertEq(xion.MAX_SUPPLY(), 420_000_000_000 ether);
    }
}
