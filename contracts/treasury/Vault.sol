// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/// @notice Per-chain vault with native-or-bridged asset tagging.
contract Vault {
    using SafeERC20 for IERC20;

    error NotAuthority();
    error ZeroAddress();
    error UnknownAsset();
    error NativeTransferFailed();

    address public immutable aoCoreAuthority;
    address public constant NATIVE_ASSET = address(0);
    mapping(address asset => bool nativeAsset) public nativeOrBridged;
    mapping(address asset => bool knownAsset) public assetKnown;

    event AssetTagged(address indexed asset, bool nativeAsset);
    event Withdrawal(address indexed asset, address indexed to, uint256 amount);

    constructor(address authority) {
        if (authority == address(0)) revert ZeroAddress();
        aoCoreAuthority = authority;
    }

    receive() external payable {}

    modifier onlyAuthority() {
        if (msg.sender != aoCoreAuthority) revert NotAuthority();
        _;
    }

    function tagAsset(address asset, bool nativeAsset) external onlyAuthority {
        assetKnown[asset] = true;
        nativeOrBridged[asset] = nativeAsset;
        emit AssetTagged(asset, nativeAsset);
    }

    function withdraw(address asset, address payable to, uint256 amount) external onlyAuthority {
        if (to == address(0)) revert ZeroAddress();
        if (!assetKnown[asset]) revert UnknownAsset();
        if (asset == NATIVE_ASSET) {
            (bool ok,) = to.call{value: amount}("");
            if (!ok) revert NativeTransferFailed();
        } else {
            IERC20(asset).safeTransfer(to, amount);
        }
        emit Withdrawal(asset, to, amount);
    }

    function balanceOf(address asset) external view returns (uint256) {
        if (asset == NATIVE_ASSET) {
            return address(this).balance;
        }
        return IERC20(asset).balanceOf(address(this));
    }
}
