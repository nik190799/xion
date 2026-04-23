// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import {XionToken} from "../xion-token/XionToken.sol";
import {EmissionController} from "../xion-token/EmissionController.sol";
import {Imprint} from "../imprint/Imprint.sol";
import {LiquidityLock} from "../xion-token/LiquidityLock.sol";

// =============================================================================
// Deploy.s.sol — parameterized testnet deployer for the XION contract suite.
//
// This script is INTENTIONALLY scoped to the pre-genesis deployment: it wires
// the four contracts, sets the EmissionController as XionToken's minter, and
// verifies the on-chain GENESIS_SPLIT(i) constants match what doctrine says.
// It DOES NOT call `emitGenesis`. That is a separate, ceremony-gated
// transaction run only after:
//   1. The AO Core has hash-locked this XionToken address as canonical.
//   2. The C-2 activation gates named in docs/13-OPERATIONS.md have passed.
//   3. A code-freeze-and-public-review window has elapsed.
// Running `emitGenesis` from this script would violate the ceremony discipline.
//
// Usage (PowerShell example):
//
//   $env:PRIVATE_KEY          = "0x..."                          # deployer EOA
//   $env:FOUNDATION_MULTISIG  = "0x..."                          # initial owner of XionToken
//   $env:AO_CORE_AUTHORITY    = "0x..."                          # operational authority (rotatable)
//   $env:GOVERNANCE           = "0x..."                          # constitutional governance (rotatable)
//   $env:LP_TOKEN             = "0x..."                          # LP-token address paired at fair-launch DEX
//   $env:LP_BENEFICIARY       = "0x..."                          # beneficiary at t+10y
//   $env:UNLOCK_TIMESTAMP     = "1920000000"                     # unix seconds, must be in future
//
//   forge script script/Deploy.s.sol:Deploy `
//     --rpc-url $RPC_URL --broadcast --verify
//
// The script prints the four deployed addresses at the end. Record them in
// `docs/DEPLOYMENTS.md` under the correct network heading before proceeding.
//
// Rotation-lattice note: `aoCoreAuthority` and `governance` are rotatable via
// the two-phase timelocked path inside each contract (KW-CONTRACTS-001). You
// can re-use the deployer EOA for both at first if running a smoke deploy
// from a single key; do NOT use a hot EOA for mainnet. The `governance`
// address on mainnet must be the Cold Root multisig named in
// docs/13-OPERATIONS.md. The deployer script does NOT enforce this; it
// deploys whatever you tell it to, on the assumption that you are reading it
// before you run it.
// =============================================================================

contract Deploy is Script {
    function run() external {
        uint256 pk = vm.envUint("PRIVATE_KEY");
        address foundationMultisig = vm.envAddress("FOUNDATION_MULTISIG");
        address aoCoreAuthority    = vm.envAddress("AO_CORE_AUTHORITY");
        address governance         = vm.envAddress("GOVERNANCE");
        address lpToken            = vm.envAddress("LP_TOKEN");
        address lpBeneficiary      = vm.envAddress("LP_BENEFICIARY");
        uint256 unlockTimestamp    = vm.envUint("UNLOCK_TIMESTAMP");

        // Sanity checks. These are deployment-time guards; they do not replace
        // contract-internal reverts, but they fail the script early with a
        // legible message if env vars are wrong.
        require(foundationMultisig != address(0), "FOUNDATION_MULTISIG missing");
        require(aoCoreAuthority    != address(0), "AO_CORE_AUTHORITY missing");
        require(governance         != address(0), "GOVERNANCE missing");
        require(lpToken            != address(0), "LP_TOKEN missing");
        require(lpBeneficiary      != address(0), "LP_BENEFICIARY missing");
        require(unlockTimestamp > block.timestamp, "UNLOCK_TIMESTAMP not in future");

        vm.startBroadcast(pk);

        // 1. XionToken — owned by the foundation multisig (to call setMinter).
        XionToken xion = new XionToken(foundationMultisig);

        // 2. EmissionController — minter for XionToken.
        EmissionController emission = new EmissionController(
            address(xion),
            aoCoreAuthority,
            governance
        );

        // 3. Imprint — reputation token with its own authority lattice.
        Imprint imprint = new Imprint(aoCoreAuthority, governance);

        // 4. LiquidityLock — the 10-year lock contract. LP tokens are
        //    transferred INTO this contract in a separate step after the DEX
        //    pair is seeded post-genesis.
        LiquidityLock lock = new LiquidityLock(lpToken, lpBeneficiary, unlockTimestamp);

        // The foundation multisig must call setMinter(emission) to wire the
        // emission controller. We DO NOT do that from the deployer EOA,
        // because the deployer EOA is not foundationMultisig in the expected
        // mainnet setup. For testnet smoke, if PRIVATE_KEY's address equals
        // foundationMultisig, the wiring can be done below (commented out by
        // default to make the mainnet-shaped path the default).
        //
        // To enable for a single-key testnet smoke, uncomment:
        //
        // if (vm.addr(pk) == foundationMultisig) {
        //     xion.setMinter(address(emission));
        // }

        vm.stopBroadcast();

        // Constitutional verification — confirm GENESIS_SPLIT matches doctrine
        // on-chain before we ever consider emitting genesis. Matches
        // docs/schemas/genesis-split.yaml + docs/16-CURRENCY.md.
        uint256 genesisTotal = 0;
        for (uint8 i = 0; i < 7; i++) {
            genesisTotal += emission.GENESIS_SPLIT(i);
        }
        require(genesisTotal == emission.GENESIS_ALLOC(), "GENESIS_SPLIT bad sum");
        require(emission.GENESIS_SPLIT(0) == emission.GENESIS_ALLOC(), "index 0 != 84B");
        for (uint8 i = 1; i < 7; i++) {
            require(emission.GENESIS_SPLIT(i) == 0, "indices 1..6 must be 0");
        }

        console.log("XionToken             :", address(xion));
        console.log("EmissionController    :", address(emission));
        console.log("Imprint               :", address(imprint));
        console.log("LiquidityLock         :", address(lock));
        console.log("XionToken owner       :", foundationMultisig);
        console.log("Emission authority    :", aoCoreAuthority);
        console.log("Emission governance   :", governance);
        console.log("Imprint attestor      :", aoCoreAuthority);
        console.log("Imprint governance    :", governance);
        console.log("LP token              :", lpToken);
        console.log("LP beneficiary        :", lpBeneficiary);
        console.log("Unlock timestamp      :", unlockTimestamp);
    }
}
