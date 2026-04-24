# Contributing to Xion

> *Speed comes from trusting the auto-revert. You cannot make Xion improve faster by making the safety gates thinner.*

## The Workflow

1. **Scaffold:** Use the `xion new` CLI commands (`skill`, `sense`, `provider`, `verifier`, `proposal`) to generate a working skeleton. The CLI is implemented in [`xion-verify/src/xion_verify/commands/new.py`](xion-verify/src/xion_verify/commands/new.py); `xion new ...` is exposed via the [`xion`](xion-verify/pyproject.toml) console-script alias and is identical to running `xion-verify new ...`.
2. **Local Test:** Run `xion local --self-test` to boot the full stack against a temp directory and ensure your change works locally.
3. **Pull Request:** Submit your PR. The CI gates will automatically run the Harm Analyzer and the pre-warmed shadow canary.
4. **Bounty Payout:** If your proposal passes the canary, gets merged, and survives the observe window (`post_deploy: kept`), you will receive an automated XION payout from the treasury.

## Disjoint Surface Architecture

Skills don't import skills. Senses don't import senses. Specialists don't talk to specialists except through public ledgers. This guarantees that your change can be canaried in parallel with dozens of others.

## The CLI Scaffolders

- `xion new skill <name>`
- `xion new sense <name>`
- `xion new provider <name>`
- `xion new verifier <name>`
- `xion new proposal <name>`

Each generates a working skeleton with the eight-question template pre-filled and local Harm-Analyzer hooks wired.
