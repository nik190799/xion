// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {MasterTreasury} from "../treasury/MasterTreasury.sol";
import {Vault} from "../treasury/Vault.sol";

contract MockToken {
    mapping(address account => uint256 balance) public balanceOf;

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "insufficient");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}

contract TreasuryTest is Test {
    address internal constant GOV = address(0xA11CE);
    address internal constant CORE = address(0xC0DE);
    address internal constant USER = address(0xB0B);
    address internal constant TOKEN = address(0x1000);

    function test_bridgeCapRevertsWhenExceeded() public {
        MasterTreasury treasury = new MasterTreasury(GOV, 1_000, CORE);

        vm.expectRevert(MasterTreasury.BridgeCapExceeded.selector);
        treasury.assertBridgeExposure(11, 100);
    }

    function test_governanceDeploysVault() public {
        MasterTreasury treasury = new MasterTreasury(GOV, 1_000, CORE);

        vm.prank(GOV);
        address vault = treasury.deployVault(8453, CORE);

        assertEq(treasury.vaultForChain(8453), vault);
        assertEq(treasury.registeredChainCount(), 1);
        assertEq(treasury.registeredChainIdAt(0), 8453);
    }

    function test_onlyGovernanceRegistersVault() public {
        MasterTreasury treasury = new MasterTreasury(GOV, 1_000, CORE);

        vm.expectRevert(MasterTreasury.NotGovernance.selector);
        vm.prank(USER);
        treasury.registerVault(8453, address(0xCAFE));
    }

    function test_vaultTagsNativeOrBridgedAsset() public {
        Vault vault = new Vault(CORE);

        vm.prank(CORE);
        vault.tagAsset(TOKEN, true);

        assertTrue(vault.assetKnown(TOKEN));
        assertTrue(vault.nativeOrBridged(TOKEN));
    }

    function test_vaultWithdrawOnlyAuthority() public {
        Vault vault = new Vault(CORE);

        vm.expectRevert(Vault.NotAuthority.selector);
        vm.prank(USER);
        vault.withdraw(TOKEN, payable(USER), 1);
    }

    function test_vaultWithdrawTransfersKnownErc20() public {
        MockToken token = new MockToken();
        Vault vault = new Vault(CORE);
        token.mint(address(vault), 100);

        vm.prank(CORE);
        vault.tagAsset(address(token), true);
        vm.prank(CORE);
        vault.withdraw(address(token), payable(USER), 40);

        assertEq(token.balanceOf(USER), 40);
        assertEq(token.balanceOf(address(vault)), 60);
        assertEq(vault.balanceOf(address(token)), 60);
    }

    function test_vaultWithdrawTransfersKnownNativeAsset() public {
        Vault vault = new Vault(CORE);
        vm.deal(address(vault), 5 ether);

        vm.prank(CORE);
        vault.tagAsset(Vault.NATIVE_ASSET(), true);
        vm.prank(CORE);
        vault.withdraw(Vault.NATIVE_ASSET(), payable(USER), 2 ether);

        assertEq(USER.balance, 2 ether);
        assertEq(address(vault).balance, 3 ether);
        assertEq(vault.balanceOf(Vault.NATIVE_ASSET()), 3 ether);
    }

    function test_vaultWithdrawUnknownAssetReverts() public {
        Vault vault = new Vault(CORE);

        vm.expectRevert(Vault.UnknownAsset.selector);
        vm.prank(CORE);
        vault.withdraw(TOKEN, payable(USER), 1);
    }

    function test_aggregateTotalsSplitsNativeAndBridgedValue() public {
        MockToken nativeToken = new MockToken();
        MockToken bridgedToken = new MockToken();
        MasterTreasury treasury = new MasterTreasury(GOV, 1_000, CORE);

        Vault vault = new Vault(CORE);
        nativeToken.mint(address(vault), 2e18);
        bridgedToken.mint(address(vault), 3e18);

        vm.startPrank(CORE);
        vault.tagAsset(address(nativeToken), true);
        vault.tagAsset(address(bridgedToken), false);
        vm.stopPrank();

        vm.prank(GOV);
        treasury.registerVault(8453, address(vault));

        address[] memory assets = new address[](2);
        assets[0] = address(nativeToken);
        assets[1] = address(bridgedToken);
        uint256[] memory unitValues = new uint256[](2);
        unitValues[0] = 2e18;
        unitValues[1] = 5e17;

        (uint256 nativeValue, uint256 bridgedValue, uint256 totalValue) = treasury.aggregateTotals(assets, unitValues);

        assertEq(nativeValue, 4e18);
        assertEq(bridgedValue, 15e17);
        assertEq(totalValue, 55e17);
    }

    function test_requestReplenishOnlyAOCoreAuthorityAndConsumesDailyCap() public {
        MasterTreasury treasury = new MasterTreasury(GOV, 1_000, CORE);
        Vault vault = new Vault(CORE);

        vm.prank(GOV);
        treasury.registerVault(8453, address(vault));

        vm.expectRevert(MasterTreasury.NotAOCoreAuthority.selector);
        vm.prank(USER);
        treasury.requestReplenish(8453, TOKEN, 1);

        vm.prank(CORE);
        treasury.requestReplenish(8453, TOKEN, 10);

        assertEq(treasury.bridgeEgressValueToday(), 10);
    }
}
