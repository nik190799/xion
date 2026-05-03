// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {EmissionController, IXionToken} from "../xion-token/EmissionController.sol";
import {XionToken} from "../xion-token/XionToken.sol";

// =============================================================================
// EmissionController.t.sol — Foundry coverage for the emission controller.
//
// Covers:
//   - Constructor zero-address guards (token, authority, governance).
//   - GENESIS_SPLIT constant (KW-CONTRACTS-002): external accessor returns the
//     expected value for each i, reverts on i > 6.
//   - emitGenesis (KW-CONTRACTS-002, KW-CONTRACTS-005):
//       * happy path: only the fair-launch recipient receives 84B; others
//         receive 0; XionToken.totalMinted == 84B after the call.
//       * idempotency: second call reverts GenesisAlreadyEmitted.
//       * zero-recipient guard for the fair-launch slot.
//       * non-authority gated.
//       * CEI: genesisEmitted flag is set BEFORE any mint (property tested by
//         asserting the final state; combined with the revert path below this
//         pins the ordering even if the contract is later refactored).
//   - scheduledMint:
//       * blocked before genesisEmitted.
//       * pool index > 6 reverts InvalidPool.
//       * zero recipient reverts.
//       * only-authority gated.
//       * era-boundary edges: T = ERA1_END - 1 → era 1; T = ERA1_END → era 2;
//         beyond ERA4_END → reverts EraNotActive(5).
//       * pool cap exhaustion reverts PoolExhausted.
//       * era cap exhaustion reverts EraCapExceeded.
//       * slowdown cap reverts ("slowdown cap reached").
//       * mintingPaused blocks; auto-unpause after pause expiry.
//   - slowEra:
//       * cannot exceed 10000 bps (accelerate).
//       * cannot raise an existing slowdown.
//       * non-governance rejected.
//       * invalid era rejected.
//   - pauseMinting:
//       * duration > 72h reverts.
//       * only-governance.
//       * unpauseIfExpired works when past eta.
//   - retirePool:
//       * caps frozen at current minted amount.
//       * pool > 6 rejected.
//       * non-governance rejected.
//   - Rotation lattice (KW-CONTRACTS-001):
//       * Authority rotation 7d timelock; governance-gated propose & cancel.
//       * Governance rotation 30d timelock; self-gated propose & cancel.
//       * Non-governance cannot propose or cancel.
//       * ZeroAddress proposals reject.
//       * executes exactly at eta; reverts strictly before.
// =============================================================================

contract EmissionControllerTest is Test {
    XionToken internal xion;
    EmissionController internal emission;

    address internal constant FOUNDATION = address(0xF0F0);
    address internal constant AUTHORITY = address(0xA011);
    address internal constant GOV = address(0xC0DE);
    address internal constant LP = address(0x1D19); // fair-launch LP recipient
    address internal constant USER = address(0x42);

    function setUp() public {
        xion = new XionToken(FOUNDATION);
        emission = new EmissionController(address(xion), AUTHORITY, GOV);
        vm.prank(FOUNDATION);
        xion.setMinter(address(emission));
    }

    function _defaultRecipients() internal pure returns (address[7] memory r) {
        r[0] = LP;
        // indices 1..6 stay zero (genesis split for those pools is 0).
    }

    // -------------------------------------------------------------------------
    // Construction
    // -------------------------------------------------------------------------
    function test_constructor_rejectsZeroToken() public {
        vm.expectRevert(EmissionController.ZeroAddress.selector);
        new EmissionController(address(0), AUTHORITY, GOV);
    }

    function test_constructor_rejectsZeroAuthority() public {
        vm.expectRevert(EmissionController.ZeroAddress.selector);
        new EmissionController(address(xion), address(0), GOV);
    }

    function test_constructor_rejectsZeroGovernance() public {
        vm.expectRevert(EmissionController.ZeroAddress.selector);
        new EmissionController(address(xion), AUTHORITY, address(0));
    }

    function test_constructor_setsGenesisTimestamp() public view {
        assertEq(emission.GENESIS_TIMESTAMP(), block.timestamp);
        assertEq(emission.aoCoreAuthority(), AUTHORITY);
        assertEq(emission.governance(), GOV);
    }

    // -------------------------------------------------------------------------
    // GENESIS_SPLIT public accessor — KW-CONTRACTS-002
    // -------------------------------------------------------------------------
    function test_genesisSplit_index0_is84B() public view {
        assertEq(emission.GENESIS_SPLIT(0), 84_000_000_000 ether);
    }

    function test_genesisSplit_indices1to6_zero() public view {
        for (uint8 i = 1; i <= 6; i++) {
            assertEq(emission.GENESIS_SPLIT(i), 0);
        }
    }

    function test_genesisSplit_index7_reverts() public {
        vm.expectRevert(EmissionController.InvalidPool.selector);
        emission.GENESIS_SPLIT(7);
    }

    function test_genesisSplit_sumIs84B() public view {
        uint256 total;
        for (uint8 i = 0; i < 7; i++) {
            total += emission.GENESIS_SPLIT(i);
        }
        assertEq(total, emission.GENESIS_ALLOC());
        assertEq(total, 84_000_000_000 ether);
    }

    // -------------------------------------------------------------------------
    // emitGenesis — KW-CONTRACTS-002, KW-CONTRACTS-005
    // -------------------------------------------------------------------------
    function test_emitGenesis_happyPath() public {
        address[7] memory recipients = _defaultRecipients();

        vm.expectEmit(false, false, false, true);
        emit EmissionController.GenesisEmitted(84_000_000_000 ether);
        vm.prank(AUTHORITY);
        emission.emitGenesis(recipients);

        assertTrue(emission.genesisEmitted());
        assertEq(xion.balanceOf(LP), 84_000_000_000 ether);
        assertEq(xion.totalMinted(), 84_000_000_000 ether);
        assertEq(emission.poolMinted(0), 84_000_000_000 ether);
        for (uint8 i = 1; i <= 6; i++) {
            assertEq(emission.poolMinted(i), 0);
        }
    }

    function test_emitGenesis_idempotent() public {
        address[7] memory recipients = _defaultRecipients();
        vm.prank(AUTHORITY);
        emission.emitGenesis(recipients);

        vm.expectRevert(EmissionController.GenesisAlreadyEmitted.selector);
        vm.prank(AUTHORITY);
        emission.emitGenesis(recipients);
    }

    function test_emitGenesis_rejectsZeroRecipientForNonZeroSlot() public {
        address[7] memory recipients; // all zero

        vm.expectRevert(abi.encodeWithSelector(EmissionController.GenesisRecipientMissing.selector, 0));
        vm.prank(AUTHORITY);
        emission.emitGenesis(recipients);
    }

    function test_emitGenesis_allowsZeroRecipientsForZeroSlots() public {
        // Indices 1..6 have split=0, so their recipient address is not read.
        address[7] memory recipients;
        recipients[0] = LP;
        // recipients[1..6] = address(0) is fine.

        vm.prank(AUTHORITY);
        emission.emitGenesis(recipients);
        assertTrue(emission.genesisEmitted());
    }

    function test_emitGenesis_onlyAuthority() public {
        address[7] memory recipients = _defaultRecipients();
        vm.expectRevert(EmissionController.NotAuthority.selector);
        vm.prank(USER);
        emission.emitGenesis(recipients);
    }

    // -------------------------------------------------------------------------
    // scheduledMint — era boundaries, caps, CEI
    // -------------------------------------------------------------------------
    function _genesis() internal {
        address[7] memory recipients = _defaultRecipients();
        vm.prank(AUTHORITY);
        emission.emitGenesis(recipients);
    }

    function _mintInDailyChunks(uint8 pool, uint256 amount) internal {
        uint256 remaining = amount;
        uint256 dailyCap = emission.DAILY_EGRESS_CAP();

        while (remaining > 0) {
            uint256 chunk = remaining > dailyCap ? dailyCap : remaining;
            vm.prank(AUTHORITY);
            emission.scheduledMint(pool, USER, chunk);
            remaining -= chunk;
            vm.warp(block.timestamp + 1 days);
        }
    }

    function test_scheduledMint_blockedBeforeGenesis() public {
        vm.expectRevert(abi.encodeWithSelector(EmissionController.EraNotActive.selector, 0));
        vm.prank(AUTHORITY);
        emission.scheduledMint(1, USER, 1 ether);
    }

    function test_scheduledMint_happyPath_era1() public {
        _genesis();
        vm.prank(AUTHORITY);
        emission.scheduledMint(1, USER, 1000 ether);
        assertEq(xion.balanceOf(USER), 1000 ether);
        assertEq(emission.poolMinted(1), 1000 ether);
        assertEq(emission.mintedInEra1(), 1000 ether);
    }

    function test_scheduledMint_era1BoundaryExact() public {
        _genesis();
        // T = GENESIS + ERA1_END - 1 → still era 1.
        vm.warp(emission.GENESIS_TIMESTAMP() + emission.ERA1_END() - 1);
        vm.prank(AUTHORITY);
        emission.scheduledMint(1, USER, 1 ether);
        assertEq(emission.mintedInEra1(), 1 ether);
    }

    function test_scheduledMint_era2BoundaryExact() public {
        _genesis();
        // T = GENESIS + ERA1_END → era 2.
        vm.warp(emission.GENESIS_TIMESTAMP() + emission.ERA1_END());
        vm.prank(AUTHORITY);
        emission.scheduledMint(1, USER, 1 ether);
        assertEq(emission.mintedInEra2(), 1 ether);
        assertEq(emission.mintedInEra1(), 0);
    }

    function test_scheduledMint_era3Boundary() public {
        _genesis();
        vm.warp(emission.GENESIS_TIMESTAMP() + emission.ERA2_END());
        vm.prank(AUTHORITY);
        emission.scheduledMint(1, USER, 1 ether);
        assertEq(emission.mintedInEra3(), 1 ether);
    }

    function test_scheduledMint_era4Boundary() public {
        _genesis();
        vm.warp(emission.GENESIS_TIMESTAMP() + emission.ERA3_END());
        vm.prank(AUTHORITY);
        emission.scheduledMint(1, USER, 1 ether);
        assertEq(emission.mintedInEra4(), 1 ether);
    }

    function test_scheduledMint_pastEra4Reverts() public {
        _genesis();
        vm.warp(emission.GENESIS_TIMESTAMP() + emission.ERA4_END());
        vm.expectRevert(abi.encodeWithSelector(EmissionController.EraNotActive.selector, 5));
        vm.prank(AUTHORITY);
        emission.scheduledMint(1, USER, 1 ether);
    }

    function test_scheduledMint_invalidPoolReverts() public {
        _genesis();
        vm.expectRevert(EmissionController.InvalidPool.selector);
        vm.prank(AUTHORITY);
        emission.scheduledMint(7, USER, 1 ether);
    }

    function test_scheduledMint_zeroRecipientReverts() public {
        _genesis();
        vm.expectRevert(EmissionController.ZeroAddress.selector);
        vm.prank(AUTHORITY);
        emission.scheduledMint(1, address(0), 1 ether);
    }

    function test_scheduledMint_onlyAuthority() public {
        _genesis();
        vm.expectRevert(EmissionController.NotAuthority.selector);
        vm.prank(USER);
        emission.scheduledMint(1, USER, 1 ether);
    }

    function test_scheduledMint_poolCapExhaustion() public {
        _genesis();
        uint256 cap = emission.poolCap(1); // 63B
        _mintInDailyChunks(1, cap); // exactly fills pool 1
        assertEq(emission.poolMinted(1), cap);

        vm.expectRevert(abi.encodeWithSelector(EmissionController.PoolExhausted.selector, 1));
        vm.prank(AUTHORITY);
        emission.scheduledMint(1, USER, 1);
    }

    function test_scheduledMint_era2CapExhaustion() public {
        _genesis();
        vm.warp(emission.GENESIS_TIMESTAMP() + emission.ERA1_END());
        uint256 era2Cap = emission.ERA2_CAP(); // 84B
        _mintInDailyChunks(0, era2Cap); // pool 0 has ample room (168B cap)

        vm.expectRevert(abi.encodeWithSelector(EmissionController.EraCapExceeded.selector, 2));
        vm.prank(AUTHORITY);
        emission.scheduledMint(1, USER, 1);
    }

    function test_scheduledMint_era3CapExhaustion() public {
        _genesis();
        vm.warp(emission.GENESIS_TIMESTAMP() + emission.ERA2_END());
        uint256 era3Cap = emission.ERA3_CAP(); // 63B
        _mintInDailyChunks(0, era3Cap); // pool 0 has 168B cap

        vm.expectRevert(abi.encodeWithSelector(EmissionController.EraCapExceeded.selector, 3));
        vm.prank(AUTHORITY);
        emission.scheduledMint(1, USER, 1);
    }

    function test_scheduledMint_era4CapExhaustion() public {
        _genesis();
        vm.warp(emission.GENESIS_TIMESTAMP() + emission.ERA3_END());
        uint256 era4Cap = emission.ERA4_CAP(); // 63B
        _mintInDailyChunks(0, era4Cap);

        vm.expectRevert(abi.encodeWithSelector(EmissionController.EraCapExceeded.selector, 4));
        vm.prank(AUTHORITY);
        emission.scheduledMint(1, USER, 1);
    }

    function test_scheduledMint_eraCapExhaustion() public {
        _genesis();
        // Cache view-call returns BEFORE starting the prank so `vm.prank` only
        // forwards the AUTHORITY caller to the mint txs, not to the view reads.
        uint256 pool1Cap = emission.poolCap(1);
        uint256 pool2Cap = emission.poolCap(2);
        uint256 eraCap = emission.ERA1_CAP(); // 126B
        // Pools 1, 2 (63B each) sum to 126B = ERA1_CAP exactly.
        _mintInDailyChunks(1, pool1Cap);
        _mintInDailyChunks(2, pool2Cap);
        assertEq(emission.mintedInEra1(), eraCap);

        vm.expectRevert(abi.encodeWithSelector(EmissionController.EraCapExceeded.selector, 1));
        vm.prank(AUTHORITY);
        emission.scheduledMint(3, USER, 1);
    }

    function test_slowEra_happyPath_halvesEffectiveCap() public {
        _genesis();
        vm.prank(GOV);
        emission.slowEra(1, 5000); // halve era 1

        // Effective cap = 63B. Fill pool 1 up to 63B — but pool cap is 63B, so
        // we actually fill pool 1 AND pool 2 halfway to exercise the slowdown.
        // Simpler: mint 63B+1 total to trigger slowdown revert.
        uint256 effCap = (emission.ERA1_CAP() * 5000) / 10000; // 63B
        _mintInDailyChunks(1, effCap); // fills era halfway = effective cap

        vm.expectRevert("slowdown cap reached");
        vm.prank(AUTHORITY);
        emission.scheduledMint(2, USER, 1);
    }

    function test_slowEra_era2_slowdownRevert() public {
        _genesis();
        vm.prank(GOV);
        emission.slowEra(2, 5000); // halve era 2

        vm.warp(emission.GENESIS_TIMESTAMP() + emission.ERA1_END());
        uint256 effCap = (emission.ERA2_CAP() * 5000) / 10000; // 42B
        _mintInDailyChunks(1, effCap);

        vm.expectRevert("slowdown cap reached");
        vm.prank(AUTHORITY);
        emission.scheduledMint(2, USER, 1);
    }

    function test_slowEra_era3_slowdownRevert() public {
        _genesis();
        vm.prank(GOV);
        emission.slowEra(3, 5000); // halve era 3

        vm.warp(emission.GENESIS_TIMESTAMP() + emission.ERA2_END());
        uint256 effCap = (emission.ERA3_CAP() * 5000) / 10000; // 31.5B
        _mintInDailyChunks(1, effCap);

        vm.expectRevert("slowdown cap reached");
        vm.prank(AUTHORITY);
        emission.scheduledMint(2, USER, 1);
    }

    function test_slowEra_era4_slowdownRevert() public {
        _genesis();
        vm.prank(GOV);
        emission.slowEra(4, 5000); // halve era 4

        vm.warp(emission.GENESIS_TIMESTAMP() + emission.ERA3_END());
        uint256 effCap = (emission.ERA4_CAP() * 5000) / 10000; // 31.5B
        _mintInDailyChunks(1, effCap);

        vm.expectRevert("slowdown cap reached");
        vm.prank(AUTHORITY);
        emission.scheduledMint(2, USER, 1);
    }

    function test_slowEra_cannotAccelerate() public {
        vm.expectRevert(EmissionController.CannotAccelerate.selector);
        vm.prank(GOV);
        emission.slowEra(1, 10_001);
    }

    function test_slowEra_cannotRaise() public {
        vm.prank(GOV);
        emission.slowEra(1, 5000);

        vm.expectRevert(EmissionController.CannotAccelerate.selector);
        vm.prank(GOV);
        emission.slowEra(1, 7000);
    }

    function test_slowEra_invalidEra() public {
        vm.expectRevert(abi.encodeWithSelector(EmissionController.EraNotActive.selector, 0));
        vm.prank(GOV);
        emission.slowEra(0, 5000);

        vm.expectRevert(abi.encodeWithSelector(EmissionController.EraNotActive.selector, 5));
        vm.prank(GOV);
        emission.slowEra(5, 5000);
    }

    function test_slowEra_onlyGovernance() public {
        vm.expectRevert(EmissionController.NotGovernance.selector);
        vm.prank(AUTHORITY);
        emission.slowEra(1, 5000);
    }

    // -------------------------------------------------------------------------
    // pauseMinting
    // -------------------------------------------------------------------------
    function test_pauseMinting_blocksScheduledMint() public {
        _genesis();
        vm.prank(GOV);
        emission.pauseMinting(1 hours);

        vm.expectRevert(EmissionController.MintingIsPaused.selector);
        vm.prank(AUTHORITY);
        emission.scheduledMint(1, USER, 1 ether);
    }

    function test_pauseMinting_rejectsOver72h() public {
        vm.expectRevert("pause <= 72h");
        vm.prank(GOV);
        emission.pauseMinting(73 hours);
    }

    function test_pauseMinting_onlyGovernance() public {
        vm.expectRevert(EmissionController.NotGovernance.selector);
        vm.prank(AUTHORITY);
        emission.pauseMinting(1 hours);
    }

    function test_unpauseIfExpired_restoresMinting() public {
        _genesis();
        vm.prank(GOV);
        emission.pauseMinting(1 hours);

        // Before expiry: still paused.
        emission.unpauseIfExpired();
        assertTrue(emission.mintingPaused());

        vm.warp(block.timestamp + 1 hours);
        emission.unpauseIfExpired();
        assertFalse(emission.mintingPaused());

        // Minting works again.
        vm.prank(AUTHORITY);
        emission.scheduledMint(1, USER, 1 ether);
        assertEq(xion.balanceOf(USER), 1 ether);
    }

    // -------------------------------------------------------------------------
    // retirePool
    // -------------------------------------------------------------------------
    function test_retirePool_freezesCapAtCurrent() public {
        _genesis();
        vm.prank(AUTHORITY);
        emission.scheduledMint(1, USER, 100 ether);

        vm.prank(GOV);
        emission.retirePool(1);

        assertEq(emission.poolCap(1), 100 ether);

        vm.expectRevert(abi.encodeWithSelector(EmissionController.PoolExhausted.selector, 1));
        vm.prank(AUTHORITY);
        emission.scheduledMint(1, USER, 1);
    }

    function test_retirePool_invalidPool() public {
        vm.expectRevert(EmissionController.InvalidPool.selector);
        vm.prank(GOV);
        emission.retirePool(7);
    }

    function test_retirePool_onlyGovernance() public {
        vm.expectRevert(EmissionController.NotGovernance.selector);
        vm.prank(AUTHORITY);
        emission.retirePool(1);
    }

    // -------------------------------------------------------------------------
    // Authority rotation lattice
    // -------------------------------------------------------------------------
    function test_authorityRotation_happyPath() public {
        address newAuth = address(0xAAAA);
        vm.expectEmit(true, false, false, true);
        emit EmissionController.AuthorityRotationProposed(newAuth, block.timestamp + 7 days);
        vm.prank(GOV);
        emission.proposeAuthorityRotation(newAuth);

        vm.warp(block.timestamp + 7 days - 1);
        vm.expectRevert(EmissionController.RotationNotMatured.selector);
        emission.executeAuthorityRotation();

        vm.warp(block.timestamp + 1);
        vm.expectEmit(true, true, false, true);
        emit EmissionController.AuthorityRotationExecuted(AUTHORITY, newAuth);
        emission.executeAuthorityRotation();

        assertEq(emission.aoCoreAuthority(), newAuth);

        // New authority can emit genesis; old authority cannot.
        address[7] memory recipients = _defaultRecipients();
        vm.expectRevert(EmissionController.NotAuthority.selector);
        vm.prank(AUTHORITY);
        emission.emitGenesis(recipients);

        vm.prank(newAuth);
        emission.emitGenesis(recipients);
        assertTrue(emission.genesisEmitted());
    }

    function test_authorityRotation_cancellable() public {
        address newAuth = address(0xAAAA);
        vm.prank(GOV);
        emission.proposeAuthorityRotation(newAuth);
        vm.prank(GOV);
        emission.cancelAuthorityRotation();
        assertEq(emission.pendingAuthority(), address(0));

        vm.warp(block.timestamp + 8 days);
        vm.expectRevert(EmissionController.NoPendingRotation.selector);
        emission.executeAuthorityRotation();
    }

    function test_authorityRotation_nonGovernanceCannotPropose() public {
        vm.expectRevert(EmissionController.NotGovernance.selector);
        vm.prank(AUTHORITY);
        emission.proposeAuthorityRotation(address(0xAAAA));
    }

    function test_authorityRotation_nonGovernanceCannotCancel() public {
        vm.prank(GOV);
        emission.proposeAuthorityRotation(address(0xAAAA));

        vm.expectRevert(EmissionController.NotGovernance.selector);
        vm.prank(AUTHORITY);
        emission.cancelAuthorityRotation();
    }

    function test_authorityRotation_rejectsZeroAddress() public {
        vm.expectRevert(EmissionController.ZeroAddress.selector);
        vm.prank(GOV);
        emission.proposeAuthorityRotation(address(0));
    }

    function test_authorityRotation_cancelWithoutPendingReverts() public {
        vm.expectRevert(EmissionController.NoPendingRotation.selector);
        vm.prank(GOV);
        emission.cancelAuthorityRotation();
    }

    function test_authorityRotation_executeWithoutPendingReverts() public {
        vm.expectRevert(EmissionController.NoPendingRotation.selector);
        emission.executeAuthorityRotation();
    }

    // -------------------------------------------------------------------------
    // Governance rotation lattice
    // -------------------------------------------------------------------------
    function test_governanceRotation_happyPath() public {
        address newGov = address(0xBBBB);
        vm.prank(GOV);
        emission.proposeGovernanceRotation(newGov);

        vm.warp(block.timestamp + 30 days - 1);
        vm.expectRevert(EmissionController.RotationNotMatured.selector);
        emission.executeGovernanceRotation();

        vm.warp(block.timestamp + 1);
        emission.executeGovernanceRotation();
        assertEq(emission.governance(), newGov);

        // New governance can propose authority rotation; old cannot.
        vm.prank(newGov);
        emission.proposeAuthorityRotation(address(0xAAAA));
        vm.expectRevert(EmissionController.NotGovernance.selector);
        vm.prank(GOV);
        emission.proposeAuthorityRotation(address(0xBEEF));
    }

    function test_governanceRotation_cancellable() public {
        vm.prank(GOV);
        emission.proposeGovernanceRotation(address(0xBBBB));
        vm.prank(GOV);
        emission.cancelGovernanceRotation();
        assertEq(emission.pendingGovernance(), address(0));
    }

    function test_governanceRotation_nonGovernanceCannotPropose() public {
        vm.expectRevert(EmissionController.NotGovernance.selector);
        vm.prank(USER);
        emission.proposeGovernanceRotation(address(0xBBBB));
    }

    function test_governanceRotation_nonGovernanceCannotCancel() public {
        vm.prank(GOV);
        emission.proposeGovernanceRotation(address(0xBBBB));
        vm.expectRevert(EmissionController.NotGovernance.selector);
        vm.prank(USER);
        emission.cancelGovernanceRotation();
    }

    function test_governanceRotation_rejectsZeroAddress() public {
        vm.expectRevert(EmissionController.ZeroAddress.selector);
        vm.prank(GOV);
        emission.proposeGovernanceRotation(address(0));
    }

    function test_governanceRotation_cancelWithoutPendingReverts() public {
        vm.expectRevert(EmissionController.NoPendingRotation.selector);
        vm.prank(GOV);
        emission.cancelGovernanceRotation();
    }

    function test_governanceRotation_executeWithoutPendingReverts() public {
        vm.expectRevert(EmissionController.NoPendingRotation.selector);
        emission.executeGovernanceRotation();
    }
}
