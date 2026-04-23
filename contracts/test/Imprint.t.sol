// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {Imprint} from "../imprint/Imprint.sol";

// =============================================================================
// Imprint.t.sol — Foundry coverage for contracts/imprint/Imprint.sol
//
// Covers:
//   - Constructor zero-address guards (both constructor params).
//   - attest: happy path, Locked event on first mint, reason tag emission,
//     only-attestor gate, zero-recipient guard, overflow guard
//     (KW-CONTRACTS-004), totalMinted accounting.
//   - slash: balance clamp, totalSlashed accounting, only-attestor gate.
//   - Decay math at periods = 0, 1, 12, 240 (KW-CONTRACTS-003 — DECAY_BPS=42).
//   - Decay cap at 240 periods (gas-grenade bound, KW-CONTRACTS-008).
//   - Rotation lattice (KW-CONTRACTS-001):
//       * Attestor rotation: 7d timelock — propose, cancel, execute at
//         6d23h59m (revert), 7d (success).
//       * Governance rotation: 30d timelock — same shape.
//       * Non-governance cannot propose or cancel.
//       * Idempotency: no pending rotation → execute reverts.
//   - Soulbound reverts: transfer / transferFrom / approve all revert.
//   - totalSupply = totalMinted - totalSlashed invariant.
//   - locked(holder) returns true iff decayedBalance > 0.
// =============================================================================

contract ImprintTest is Test {
    Imprint internal imprint;

    address internal constant ATTESTOR = address(0xA11CE);
    address internal constant GOV = address(0xB0B);
    address internal constant ALICE = address(0xD09);
    address internal constant BOB = address(0xCA7);
    address internal constant NEW_ATTESTOR = address(0xBEEF);
    address internal constant NEW_GOV = address(0xFADE);

    bytes32 internal constant REASON = keccak256("relationship_thread_month");

    function setUp() public {
        imprint = new Imprint(ATTESTOR, GOV);
    }

    // -------------------------------------------------------------------------
    // Construction
    // -------------------------------------------------------------------------
    function test_constructor_setsState() public view {
        assertEq(imprint.engagementAttestor(), ATTESTOR);
        assertEq(imprint.governance(), GOV);
        assertEq(imprint.totalMinted(), 0);
        assertEq(imprint.totalSlashed(), 0);
        assertEq(imprint.DECAY_BPS_PER_30D(), 42);
        assertEq(imprint.DECAY_PERIOD(), 30 days);
    }

    function test_constructor_rejectsZeroAttestor() public {
        vm.expectRevert(Imprint.ZeroAddress.selector);
        new Imprint(address(0), GOV);
    }

    function test_constructor_rejectsZeroGovernance() public {
        vm.expectRevert(Imprint.ZeroAddress.selector);
        new Imprint(ATTESTOR, address(0));
    }

    // -------------------------------------------------------------------------
    // attest — KW-CONTRACTS-004 (overflow) and happy path
    // -------------------------------------------------------------------------
    function test_attest_happyPath_emitsLockedOnFirstMint() public {
        vm.expectEmit(true, false, false, true);
        emit Imprint.Locked(ALICE);
        vm.expectEmit(true, false, true, true);
        emit Imprint.Attested(ALICE, 100 ether, REASON, 100 ether);

        vm.prank(ATTESTOR);
        imprint.attest(ALICE, 100 ether, REASON);

        assertEq(imprint.balanceOf(ALICE), 100 ether);
        assertEq(imprint.totalMinted(), 100 ether);
        assertTrue(imprint.locked(ALICE));
    }

    function test_attest_secondMintDoesNotEmitLockedAgain() public {
        vm.prank(ATTESTOR);
        imprint.attest(ALICE, 100 ether, REASON);

        // Second mint: no Locked; record logs and verify no Locked event.
        vm.recordLogs();
        vm.prank(ATTESTOR);
        imprint.attest(ALICE, 50 ether, REASON);
        Vm.Log[] memory entries = vm.getRecordedLogs();
        bytes32 lockedSig = keccak256("Locked(address)");
        for (uint256 i = 0; i < entries.length; i++) {
            assertFalse(entries[i].topics[0] == lockedSig, "Locked should not re-emit");
        }
    }

    function test_attest_onlyAttestor() public {
        vm.expectRevert(Imprint.NotAttestor.selector);
        vm.prank(ALICE);
        imprint.attest(BOB, 1 ether, REASON);
    }

    function test_attest_rejectsZeroRecipient() public {
        vm.expectRevert(Imprint.ZeroAddress.selector);
        vm.prank(ATTESTOR);
        imprint.attest(address(0), 1 ether, REASON);
    }

    function test_attest_rejectsOverflow() public {
        // Pre-seed to near uint128.max so the next attest overflows.
        vm.prank(ATTESTOR);
        imprint.attest(ALICE, type(uint128).max, REASON);

        vm.expectRevert(Imprint.AmountOverflow.selector);
        vm.prank(ATTESTOR);
        imprint.attest(ALICE, 1, REASON);
    }

    function test_attest_acceptsExactlyUint128Max() public {
        vm.prank(ATTESTOR);
        imprint.attest(ALICE, type(uint128).max, REASON);
        assertEq(imprint.balanceOf(ALICE), type(uint128).max);
    }

    // -------------------------------------------------------------------------
    // slash
    // -------------------------------------------------------------------------
    function test_slash_happyPath() public {
        vm.prank(ATTESTOR);
        imprint.attest(ALICE, 100 ether, REASON);

        vm.expectEmit(true, false, true, true);
        emit Imprint.Slashed(ALICE, 30 ether, REASON, 70 ether);
        vm.prank(ATTESTOR);
        imprint.slash(ALICE, 30 ether, REASON);

        assertEq(imprint.balanceOf(ALICE), 70 ether);
        assertEq(imprint.totalSlashed(), 30 ether);
    }

    function test_slash_clampsToBalance() public {
        vm.prank(ATTESTOR);
        imprint.attest(ALICE, 50 ether, REASON);

        vm.prank(ATTESTOR);
        imprint.slash(ALICE, 1000 ether, REASON);

        assertEq(imprint.balanceOf(ALICE), 0);
        assertEq(imprint.totalSlashed(), 50 ether);
    }

    function test_slash_onlyAttestor() public {
        vm.expectRevert(Imprint.NotAttestor.selector);
        vm.prank(BOB);
        imprint.slash(ALICE, 1, REASON);
    }

    // -------------------------------------------------------------------------
    // Decay math — KW-CONTRACTS-003 (42 bps / 30 days)
    // -------------------------------------------------------------------------
    function test_decay_period0_noDecay() public {
        vm.prank(ATTESTOR);
        imprint.attest(ALICE, 1000 ether, REASON);
        assertEq(imprint.balanceOf(ALICE), 1000 ether);
    }

    function test_decay_period1() public {
        vm.prank(ATTESTOR);
        imprint.attest(ALICE, 1000 ether, REASON);

        vm.warp(block.timestamp + 30 days);
        // 1000 * (10000 - 42) / 10000 = 995.8 ether
        assertEq(imprint.balanceOf(ALICE), (1000 ether * 9958) / 10000);
    }

    function test_decay_period12_approxFivePercentAnnual() public {
        vm.prank(ATTESTOR);
        imprint.attest(ALICE, 1000 ether, REASON);

        vm.warp(block.timestamp + 12 * 30 days);
        uint256 expected = 1000 ether;
        for (uint256 i = 0; i < 12; i++) {
            expected = (expected * 9958) / 10000;
        }
        assertEq(imprint.balanceOf(ALICE), expected);
        // Sanity: after 12 periods (~11 months), balance is ~95.1% of original
        // — within the "~5%/year" window named in docs/16-CURRENCY.md.
        assertGt(expected, 950 ether);
        assertLt(expected, 956 ether);
    }

    function test_decay_period240_capped() public {
        vm.prank(ATTESTOR);
        imprint.attest(ALICE, 1000 ether, REASON);

        // 241 periods elapsed; loop caps at 240 (gas-grenade bound).
        vm.warp(block.timestamp + 241 * 30 days);
        uint256 expected = 1000 ether;
        for (uint256 i = 0; i < 240; i++) {
            expected = (expected * 9958) / 10000;
        }
        assertEq(imprint.balanceOf(ALICE), expected);
    }

    function test_decay_untouchedWalletBeforeFirstPeriod() public {
        vm.prank(ATTESTOR);
        imprint.attest(ALICE, 1000 ether, REASON);

        vm.warp(block.timestamp + 29 days + 23 hours);
        // Strictly less than one DECAY_PERIOD -> no decay applied.
        assertEq(imprint.balanceOf(ALICE), 1000 ether);
    }

    function test_locked_falseForZeroBalance() public view {
        assertFalse(imprint.locked(BOB));
    }

    function test_balanceOf_zeroForUnseenWallet() public view {
        assertEq(imprint.balanceOf(BOB), 0);
    }

    // -------------------------------------------------------------------------
    // Attestor rotation lattice
    // -------------------------------------------------------------------------
    function test_attestorRotation_happyPath() public {
        vm.expectEmit(true, false, false, true);
        emit Imprint.AttestorRotationProposed(NEW_ATTESTOR, block.timestamp + 7 days);
        vm.prank(GOV);
        imprint.proposeAttestorRotation(NEW_ATTESTOR);

        assertEq(imprint.pendingAttestor(), NEW_ATTESTOR);
        assertEq(imprint.pendingAttestorEta(), block.timestamp + 7 days);

        // 6d23h59m → still not matured.
        vm.warp(block.timestamp + 7 days - 1);
        vm.expectRevert(Imprint.RotationNotMatured.selector);
        imprint.executeAttestorRotation();

        // 7 days → success.
        vm.warp(block.timestamp + 1);
        vm.expectEmit(true, true, false, true);
        emit Imprint.AttestorRotationExecuted(ATTESTOR, NEW_ATTESTOR);
        imprint.executeAttestorRotation();

        assertEq(imprint.engagementAttestor(), NEW_ATTESTOR);
        assertEq(imprint.pendingAttestor(), address(0));
        assertEq(imprint.pendingAttestorEta(), 0);

        // New attestor can mint; old attestor cannot.
        vm.prank(NEW_ATTESTOR);
        imprint.attest(ALICE, 1 ether, REASON);
        assertEq(imprint.balanceOf(ALICE), 1 ether);

        vm.expectRevert(Imprint.NotAttestor.selector);
        vm.prank(ATTESTOR);
        imprint.attest(BOB, 1 ether, REASON);
    }

    function test_attestorRotation_cancellable() public {
        vm.prank(GOV);
        imprint.proposeAttestorRotation(NEW_ATTESTOR);

        vm.expectEmit(true, false, false, true);
        emit Imprint.AttestorRotationCancelled(NEW_ATTESTOR);
        vm.prank(GOV);
        imprint.cancelAttestorRotation();

        assertEq(imprint.pendingAttestor(), address(0));
        assertEq(imprint.pendingAttestorEta(), 0);

        vm.warp(block.timestamp + 8 days);
        vm.expectRevert(Imprint.NoPendingRotation.selector);
        imprint.executeAttestorRotation();
    }

    function test_attestorRotation_nonGovernanceCannotPropose() public {
        vm.expectRevert(Imprint.NotGovernance.selector);
        vm.prank(ALICE);
        imprint.proposeAttestorRotation(NEW_ATTESTOR);
    }

    function test_attestorRotation_nonGovernanceCannotCancel() public {
        vm.prank(GOV);
        imprint.proposeAttestorRotation(NEW_ATTESTOR);

        vm.expectRevert(Imprint.NotGovernance.selector);
        vm.prank(ALICE);
        imprint.cancelAttestorRotation();
    }

    function test_attestorRotation_rejectsZeroAddress() public {
        vm.expectRevert(Imprint.ZeroAddress.selector);
        vm.prank(GOV);
        imprint.proposeAttestorRotation(address(0));
    }

    function test_attestorRotation_cancelWithoutPendingReverts() public {
        vm.expectRevert(Imprint.NoPendingRotation.selector);
        vm.prank(GOV);
        imprint.cancelAttestorRotation();
    }

    function test_attestorRotation_executeWithoutPendingReverts() public {
        vm.expectRevert(Imprint.NoPendingRotation.selector);
        imprint.executeAttestorRotation();
    }

    // -------------------------------------------------------------------------
    // Governance rotation lattice
    // -------------------------------------------------------------------------
    function test_governanceRotation_happyPath() public {
        vm.prank(GOV);
        imprint.proposeGovernanceRotation(NEW_GOV);

        vm.warp(block.timestamp + 30 days - 1);
        vm.expectRevert(Imprint.RotationNotMatured.selector);
        imprint.executeGovernanceRotation();

        vm.warp(block.timestamp + 1);
        vm.expectEmit(true, true, false, true);
        emit Imprint.GovernanceRotationExecuted(GOV, NEW_GOV);
        imprint.executeGovernanceRotation();

        assertEq(imprint.governance(), NEW_GOV);
        assertEq(imprint.pendingGovernance(), address(0));
        assertEq(imprint.pendingGovernanceEta(), 0);

        // New governance can propose; old governance cannot.
        vm.prank(NEW_GOV);
        imprint.proposeAttestorRotation(NEW_ATTESTOR);

        vm.expectRevert(Imprint.NotGovernance.selector);
        vm.prank(GOV);
        imprint.proposeAttestorRotation(NEW_ATTESTOR);
    }

    function test_governanceRotation_cancellable() public {
        vm.prank(GOV);
        imprint.proposeGovernanceRotation(NEW_GOV);
        vm.prank(GOV);
        imprint.cancelGovernanceRotation();
        assertEq(imprint.pendingGovernance(), address(0));
    }

    function test_governanceRotation_nonGovernanceCannotPropose() public {
        vm.expectRevert(Imprint.NotGovernance.selector);
        vm.prank(ALICE);
        imprint.proposeGovernanceRotation(NEW_GOV);
    }

    function test_governanceRotation_nonGovernanceCannotCancel() public {
        vm.prank(GOV);
        imprint.proposeGovernanceRotation(NEW_GOV);
        vm.expectRevert(Imprint.NotGovernance.selector);
        vm.prank(ALICE);
        imprint.cancelGovernanceRotation();
    }

    function test_governanceRotation_rejectsZeroAddress() public {
        vm.expectRevert(Imprint.ZeroAddress.selector);
        vm.prank(GOV);
        imprint.proposeGovernanceRotation(address(0));
    }

    function test_governanceRotation_cancelWithoutPendingReverts() public {
        vm.expectRevert(Imprint.NoPendingRotation.selector);
        vm.prank(GOV);
        imprint.cancelGovernanceRotation();
    }

    function test_governanceRotation_executeWithoutPendingReverts() public {
        vm.expectRevert(Imprint.NoPendingRotation.selector);
        imprint.executeGovernanceRotation();
    }

    // -------------------------------------------------------------------------
    // Soulbound (Invariant 10) — these functions must revert or return 0.
    // -------------------------------------------------------------------------
    function test_soulbound_transferReverts() public {
        vm.expectRevert();
        imprint.transfer(BOB, 1);
    }

    function test_soulbound_transferFromReverts() public {
        vm.expectRevert();
        imprint.transferFrom(ALICE, BOB, 1);
    }

    function test_soulbound_approveReverts() public {
        vm.expectRevert();
        imprint.approve(BOB, 1);
    }

    function test_soulbound_allowanceAlwaysZero() public view {
        assertEq(imprint.allowance(ALICE, BOB), 0);
    }

    // -------------------------------------------------------------------------
    // totalSupply invariant
    // -------------------------------------------------------------------------
    function test_totalSupply_equalsMintedMinusSlashed() public {
        vm.prank(ATTESTOR);
        imprint.attest(ALICE, 100 ether, REASON);
        vm.prank(ATTESTOR);
        imprint.attest(BOB, 50 ether, REASON);
        assertEq(imprint.totalSupply(), 150 ether);

        vm.prank(ATTESTOR);
        imprint.slash(ALICE, 10 ether, REASON);
        assertEq(imprint.totalSupply(), 140 ether);
    }
}
