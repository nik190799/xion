// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Vault} from "./Vault.sol";

/// @notice Registry for per-chain treasury vaults and bridge exposure caps.
contract MasterTreasury {
    error NotGovernance();
    error ZeroAddress();
    error BridgeCapExceeded();

    address public immutable governance;
    uint16 public immutable bridgeExposureCapBps;
    mapping(uint256 chainId => address vault) public vaultForChain;

    event VaultRegistered(uint256 indexed chainId, address indexed vault);
    event BridgeExposureChecked(uint256 bridgedValue, uint256 totalValue);

    constructor(address governance_, uint16 bridgeExposureCapBps_) {
        if (governance_ == address(0)) revert ZeroAddress();
        if (bridgeExposureCapBps_ > 10_000) revert BridgeCapExceeded();
        governance = governance_;
        bridgeExposureCapBps = bridgeExposureCapBps_;
    }

    modifier onlyGovernance() {
        if (msg.sender != governance) revert NotGovernance();
        _;
    }

    function deployVault(uint256 chainId, address aoCoreAuthority) external onlyGovernance returns (address vault) {
        Vault created = new Vault(aoCoreAuthority);
        vault = address(created);
        vaultForChain[chainId] = vault;
        emit VaultRegistered(chainId, vault);
    }

    function registerVault(uint256 chainId, address vault) external onlyGovernance {
        if (vault == address(0)) revert ZeroAddress();
        vaultForChain[chainId] = vault;
        emit VaultRegistered(chainId, vault);
    }

    function assertBridgeExposure(uint256 bridgedValue, uint256 totalValue) external {
        if (totalValue == 0) {
            if (bridgedValue != 0) revert BridgeCapExceeded();
            emit BridgeExposureChecked(bridgedValue, totalValue);
            return;
        }
        if (bridgedValue * 10_000 > totalValue * bridgeExposureCapBps) revert BridgeCapExceeded();
        emit BridgeExposureChecked(bridgedValue, totalValue);
    }
}
