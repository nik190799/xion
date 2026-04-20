// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

// =============================================================================
//  XionToken — the fungible native currency of Xion
//
//  Genesis-Locked Invariants enforced by this contract:
//   - Invariant 8: Total supply <= 420,000,000,000 forever. No handler raises it.
//   - Invariant 9: Minting is gated through the EmissionController, which has
//                  no handler to accelerate the schedule. Slow/Pause/Retire only.
//
//  Out of scope for this contract (enforced elsewhere):
//   - Invariant 13 (Treasury cannot price-impact) — AO Core Treasury-Spend handler.
//   - The Covenant-Economy firewall — orchestrator/safety.py + AO Core Spend.
//
//  Design notes:
//   - Owner-less after deployment. The `renounceOwnership` call at step 4 of
//     deployment makes this contract have no admin. Only the registered Minter
//     can mint. Setting a new Minter is *not* possible after renounce (see
//     `setMinter`'s `onlyOwner` modifier — after renounce, it is uncallable).
//   - Pausing is not supported. No `pause()` function exists. The token cannot
//     be frozen.
//   - Blacklisting is not supported. No `blacklist()` function exists. Users
//     cannot be excluded from transfers.
//   - Burning is supported (`burn`, `burnFrom`) but cap is measured against
//     `_totalMinted`, not `totalSupply()`. Burning does NOT re-enable minting.
//     The cap is over the lifetime of the token.
// =============================================================================

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract XionToken is ERC20, ERC20Burnable, Ownable {
    // -------------------------------------------------------------------------
    // Invariant 8: Total supply cap. 420,000,000,000 * 10^18 wei.
    // -------------------------------------------------------------------------
    uint256 public constant MAX_SUPPLY = 420_000_000_000 * 10**18;

    // -------------------------------------------------------------------------
    // The only address authorized to mint. Set once at deployment; cleared
    // after renounceOwnership. Not upgradeable.
    // -------------------------------------------------------------------------
    address public minter;

    // -------------------------------------------------------------------------
    // Lifetime mint counter. Burns do NOT decrement this. The cap is on total
    // ever-minted, not on circulating supply. This is intentional: once all
    // 420B have been minted (Year 20), minting stops forever regardless of burns.
    // -------------------------------------------------------------------------
    uint256 public totalMinted;

    event MinterSet(address indexed previous, address indexed current);
    event MintedBySchedule(address indexed to, uint256 amount, uint256 totalMintedAfter);

    error NotMinter();
    error MinterAlreadySet();
    error ExceedsMaxSupply(uint256 requested, uint256 remaining);
    error ZeroAddress();

    constructor(address foundationMultisig) ERC20("Xion", "XION") Ownable(foundationMultisig) {
        if (foundationMultisig == address(0)) revert ZeroAddress();
        // No mint at constructor. The EmissionController will mint the genesis
        // allocation (84B) in a separate post-deploy transaction, AFTER the
        // AO Core has hash-locked this contract's address as canonical and
        // after the C-2 activation gates have been verified on-chain.
    }

    // -------------------------------------------------------------------------
    // setMinter — called exactly once in the deployment sequence, then owner
    // renounces. After renounce, this function reverts with OwnableUnauthorized.
    // -------------------------------------------------------------------------
    function setMinter(address newMinter) external onlyOwner {
        if (newMinter == address(0)) revert ZeroAddress();
        if (minter != address(0)) revert MinterAlreadySet();
        address prev = minter;
        minter = newMinter;
        emit MinterSet(prev, newMinter);
    }

    // -------------------------------------------------------------------------
    // mint — the only path to create XION. Callable only by the registered
    // minter (the EmissionController). Checks the cap against lifetime mints.
    // -------------------------------------------------------------------------
    function mint(address to, uint256 amount) external {
        if (msg.sender != minter) revert NotMinter();
        if (to == address(0)) revert ZeroAddress();

        uint256 newTotalMinted = totalMinted + amount;
        if (newTotalMinted > MAX_SUPPLY) {
            revert ExceedsMaxSupply(amount, MAX_SUPPLY - totalMinted);
        }

        totalMinted = newTotalMinted;
        _mint(to, amount);
        emit MintedBySchedule(to, amount, newTotalMinted);
    }

    // -------------------------------------------------------------------------
    // Helpful read-only: remaining capacity available to the EmissionController.
    // The EmissionController also enforces era-specific caps; this is only the
    // lifetime cap.
    // -------------------------------------------------------------------------
    function remainingMintCapacity() external view returns (uint256) {
        return MAX_SUPPLY - totalMinted;
    }
}
