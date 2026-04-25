// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Per-chain vault with native-or-bridged asset tagging.
contract Vault {
    error NotAuthority();
    error ZeroAddress();
    error UnknownAsset();

    address public immutable aoCoreAuthority;
    mapping(address asset => bool nativeAsset) public nativeOrBridged;
    mapping(address asset => bool knownAsset) public assetKnown;

    event AssetTagged(address indexed asset, bool nativeAsset);
    event Withdrawal(address indexed asset, address indexed to, uint256 amount);

    constructor(address authority) {
        if (authority == address(0)) revert ZeroAddress();
        aoCoreAuthority = authority;
    }

    modifier onlyAuthority() {
        if (msg.sender != aoCoreAuthority) revert NotAuthority();
        _;
    }

    function tagAsset(address asset, bool nativeAsset) external onlyAuthority {
        if (asset == address(0)) revert ZeroAddress();
        assetKnown[asset] = true;
        nativeOrBridged[asset] = nativeAsset;
        emit AssetTagged(asset, nativeAsset);
    }

    function withdraw(address asset, address payable to, uint256 amount) external onlyAuthority {
        if (to == address(0)) revert ZeroAddress();
        if (!assetKnown[asset]) revert UnknownAsset();
        emit Withdrawal(asset, to, amount);
    }
}
