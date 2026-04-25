// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {MasterTreasury} from "../treasury/MasterTreasury.sol";
import {Vault} from "../treasury/Vault.sol";

contract TreasuryTest is Test {
    address internal constant GOV = address(0xA11CE);
    address internal constant CORE = address(0xC0DE);
    address internal constant USER = address(0xB0B);
    address internal constant TOKEN = address(0x1000);

    function test_bridgeCapRevertsWhenExceeded() public {
        MasterTreasury treasury = new MasterTreasury(GOV, 1_000);

        vm.expectRevert(MasterTreasury.BridgeCapExceeded.selector);
        treasury.assertBridgeExposure(11, 100);
    }

    function test_governanceDeploysVault() public {
        MasterTreasury treasury = new MasterTreasury(GOV, 1_000);

        vm.prank(GOV);
        address vault = treasury.deployVault(8453, CORE);

        assertEq(treasury.vaultForChain(8453), vault);
    }

    function test_onlyGovernanceRegistersVault() public {
        MasterTreasury treasury = new MasterTreasury(GOV, 1_000);

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
}
