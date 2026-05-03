// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Vault} from "./Vault.sol";

/// @notice Registry for per-chain treasury vaults and bridge exposure caps.
contract MasterTreasury {
    error NotGovernance();
    error NotAOCoreAuthority();
    error ZeroAddress();
    error BridgeCapExceeded();
    error ArrayLengthMismatch();
    error NoPendingRotation();
    error RotationNotMatured();
    error DailyBridgeEgressCapExceeded(uint256 day, uint256 requested, uint256 remaining);

    address public immutable governance;
    address public aoCoreAuthority;
    address public pendingAuthority;
    uint256 public pendingAuthorityEta;
    uint16 public immutable bridgeExposureCapBps;
    uint256 public constant AUTHORITY_ROTATION_DELAY = 7 days;
    uint256 public constant DAILY_BRIDGE_EGRESS_CAP = 1_000_000 * 10**18;
    uint256 public currentBridgeEgressDay;
    uint256 public bridgeEgressValueToday;
    mapping(uint256 chainId => address vault) public vaultForChain;
    mapping(uint256 chainId => bool registered) public registeredChain;
    uint256[] private _registeredChainIds;

    event VaultRegistered(uint256 indexed chainId, address indexed vault);
    event BridgeExposureChecked(uint256 bridgedValue, uint256 totalValue);
    event DailyBridgeEgressChecked(uint256 indexed day, uint256 amount, uint256 used, uint256 cap);
    event ReplenishRequested(uint256 indexed chainId, address indexed token, uint256 amountNeeded);
    event AuthorityRotationProposed(address indexed proposed, uint256 eta);
    event AuthorityRotationExecuted(address indexed previous, address indexed current);

    constructor(address governance_, uint16 bridgeExposureCapBps_, address aoCoreAuthority_) {
        if (governance_ == address(0)) revert ZeroAddress();
        if (aoCoreAuthority_ == address(0)) revert ZeroAddress();
        if (bridgeExposureCapBps_ > 10_000) revert BridgeCapExceeded();
        governance = governance_;
        aoCoreAuthority = aoCoreAuthority_;
        bridgeExposureCapBps = bridgeExposureCapBps_;
    }

    modifier onlyGovernance() {
        if (msg.sender != governance) revert NotGovernance();
        _;
    }

    modifier onlyAOCoreAuthority() {
        if (msg.sender != aoCoreAuthority) revert NotAOCoreAuthority();
        _;
    }

    function deployVault(uint256 chainId, address vaultAuthority) external onlyGovernance returns (address vault) {
        Vault created = new Vault(vaultAuthority);
        vault = address(created);
        _registerVault(chainId, vault);
        emit VaultRegistered(chainId, vault);
    }

    function registerVault(uint256 chainId, address vault) external onlyGovernance {
        if (vault == address(0)) revert ZeroAddress();
        _registerVault(chainId, vault);
        emit VaultRegistered(chainId, vault);
    }

    function registeredChainCount() external view returns (uint256) {
        return _registeredChainIds.length;
    }

    function registeredChainIdAt(uint256 index) external view returns (uint256) {
        return _registeredChainIds[index];
    }

    function aggregateTotals(address[] calldata assets, uint256[] calldata unitValues) external view returns (uint256 nativeValue, uint256 bridgedValue, uint256 totalValue) {
        if (assets.length != unitValues.length) revert ArrayLengthMismatch();
        for (uint256 chainIndex = 0; chainIndex < _registeredChainIds.length; chainIndex++) {
            Vault vault = Vault(payable(vaultForChain[_registeredChainIds[chainIndex]]));
            for (uint256 assetIndex = 0; assetIndex < assets.length; assetIndex++) {
                uint256 value = (vault.balanceOf(assets[assetIndex]) * unitValues[assetIndex]) / 1e18;
                if (vault.nativeOrBridged(assets[assetIndex])) {
                    nativeValue += value;
                } else {
                    bridgedValue += value;
                }
            }
        }
        totalValue = nativeValue + bridgedValue;
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

    function requestReplenish(uint256 chainId, address token, uint256 amountNeeded) external onlyAOCoreAuthority {
        if (vaultForChain[chainId] == address(0)) revert ZeroAddress();
        _enforceDailyBridgeEgress(amountNeeded);
        emit ReplenishRequested(chainId, token, amountNeeded);
    }

    function proposeAuthorityRotation(address newAuthority) external onlyGovernance {
        if (newAuthority == address(0)) revert ZeroAddress();
        pendingAuthority = newAuthority;
        pendingAuthorityEta = block.timestamp + AUTHORITY_ROTATION_DELAY;
        emit AuthorityRotationProposed(newAuthority, pendingAuthorityEta);
    }

    function executeAuthorityRotation() external {
        address next = pendingAuthority;
        if (next == address(0)) revert NoPendingRotation();
        if (block.timestamp < pendingAuthorityEta) revert RotationNotMatured();
        address previous = aoCoreAuthority;
        aoCoreAuthority = next;
        pendingAuthority = address(0);
        pendingAuthorityEta = 0;
        emit AuthorityRotationExecuted(previous, next);
    }

    function _registerVault(uint256 chainId, address vault) internal {
        vaultForChain[chainId] = vault;
        if (!registeredChain[chainId]) {
            registeredChain[chainId] = true;
            _registeredChainIds.push(chainId);
        }
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
