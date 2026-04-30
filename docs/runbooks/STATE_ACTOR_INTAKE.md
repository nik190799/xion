# State-Actor Intake Runbook

## Property

Every state-actor interaction is recorded in `GOVERNANCE_LEDGER` before Xion
responds in a way that could touch the Covenant, an Invariant, or a user's
legal posture.

## Scope

Use this runbook for regulator notices, subpoenas, takedown demands,
mandatory-controller requests, sanctions correspondence, law-enforcement
inquiries, and audit-firm disclosures that need a public governance row.

## Steps

1. Preserve the original demand artifact outside the repo. Do not paste user
   content into the ledger.
2. Classify the interaction using `docs/REGULATORY-POSTURE.md` Part IV:
   `A`, `B`, `C`, or `D`.
3. Compute `demand_summary_hash` over the operator's content-minimized summary.
4. Choose the response category: `comply`, `refuse`, `escalate-pending`, or
   `comply-with-disclosure`.
5. Append through the operator-only API:

```bash
curl -X POST "$XION_RELAY_URL/governance/state-actor" \
  -H "Authorization: Bearer $XION_OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  --data @state-actor-row.json
```

For offline operation, call `orchestrator.governance.append_governance_row`
directly from a local script against `ledgers/GOVERNANCE_LEDGER.jsonl`.

6. Verify:

```bash
xion-verify regulatory-ledger
```

7. If the row is class `C`, also run:

```bash
xion-verify regulatory-ledger --check-safety-link
```

8. Publish the row hash in the next State-of-Xion memo. If the response is
   still pending, publish the pending status rather than waiting silently.

## Failure Modes

- **Artifact cannot be published:** store a redacted URI and explain the
  restriction in `response_artifact_uri`.
- **User-specific demand:** notify the user unless doing so is legally barred;
  if barred, set `user_notification` to the legal reason.
- **Covenant collision:** mark the row `refuse` or `escalate-pending`; do not
  create an Arbiter override or a ledger deletion path.
