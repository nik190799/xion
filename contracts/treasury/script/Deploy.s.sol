// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import {MasterTreasury} from "../MasterTreasury.sol";

contract DeployTreasury is Script {
    function run() external returns (MasterTreasury treasury) {
        address governance = vm.envAddress("XION_TREASURY_GOVERNANCE");
        address aoCoreAuthority = vm.envAddress("XION_AO_CORE_AUTHORITY");
        uint16 bridgeCapBps = uint16(vm.envUint("XION_BRIDGE_CAP_BPS"));
        vm.startBroadcast();
        treasury = new MasterTreasury(governance, bridgeCapBps, aoCoreAuthority);
        vm.stopBroadcast();
    }
}
