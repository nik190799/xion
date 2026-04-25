// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Vault} from "./Vault.sol";

/// @notice Registry for per-chain treasury vaults and bridge exposure caps.
contract MasterTreasury {
    error NotGovernance();
    error ZeroAddress();
    error BridgeCapExceeded();
    error DailyBridgeEgressCapExceeded(uint256 day, uint256 requested, uint256 remaining);

    address public immutable governance;
    uint16 public immutable bridgeExposureCapBps;
    uint256 public constant DAILY_BRIDGE_EGRESS_CAP = 1_000_000 * 10**18;
    uint256 public currentBridgeEgressDay;
    uint256 public bridgeEgressValueToday;
    mapping(uint256 chainId => address vault) public vaultForChain;

    event VaultRegistered(uint256 indexed chainId, address indexed vault);
    event BridgeExposureChecked(uint256 bridgedValue, uint256 totalValue);
    event DailyBridgeEgressChecked(uint256 indexed day, uint256 amount, uint256 used, uint256 cap);

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

    function assertBridgeEgress(uint256 amount) external onlyGovernance {
        _enforceDailyBridgeEgress(amount);
    }

    function _enforceDailyBridgeEgress(uint256 amount) internal {
        uint256 day = block.timestamp / 1 days;
        if (day != currentBridgeEgressDay) {
            currentBridgeEgressDay = day;
            bridgeEgressValueToday = 0;
        }
        uint256 remaining = DAILY_BRIDGE_EGRESS_CAP - bridgeEgressValueToday;
        if (amount > remaining) revert DailyBridgeEgressCapExceeded(day, amount, remaining);
        bridgeEgressValueToday += amount;
        emit DailyBridgeEgressChecked(day, amount, bridgeEgressValueToday, DAILY_BRIDGE_EGRESS_CAP);
    }
}
