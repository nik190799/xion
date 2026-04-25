#!/usr/bin/env node
// Send a Commit-State message to the AO process, signed by the *owner's* wallet
// (~/.aos.json by default), and print the resulting message id on stdout.
//
// Why this exists: aos's `--run "Send({...})"` posts an outbox message *from the
// process itself*, so `msg.From == ao.id`. The Phase 6.1 skeleton's commit-state
// handler authorizes only `[Owner]` (see ao/core/main.lua), so a self-Send is
// rejected with `Action = State-Rejection, Reason = non_authorised_caller`. The
// real authority lattice will eventually populate `AuthorizedSigners` with hot
// and warm tier addresses; for the seal we use the canonical "owner sends from
// outside the process" path, which is what the doctrine actually models.
//
// Why .cjs (not .mjs): the only place `@permaweb/aoconnect` is installed in this
// environment is inside `aos`'s own node_modules. Setting NODE_PATH lets Node
// resolve the bare specifier in CommonJS mode (`require(...)`), but Node's ESM
// loader does *not* honor NODE_PATH for `exports`-field resolution — `import`
// from a bare specifier under NODE_PATH fails with ERR_MODULE_NOT_FOUND.
// aoconnect's package.json explicitly exports a `require: './dist/index.cjs'`
// entry for exactly this case, so a CJS helper is both shorter and correct.
//
// Usage: node scripts/ao-localnet-send-commit-state.cjs <pid>
//
// Env (with defaults):
//   WALLET=~/.aos.json
//   GATE=http://localhost:4000   CU=http://localhost:4004   MU=http://localhost:4002
//   TIP_HEIGHT=1
//   STATE_ROOT_SHA256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
//                     (sha256 of the empty byte string — first commit-state per
//                      docs/runbooks/AO_DEPLOY_LOCALNET.md)
//
// Output: a single line containing the AO message id (43-char base64url) on success;
//         non-zero exit + diagnostic on stderr on failure.

const { connect, createDataItemSigner } = require('@permaweb/aoconnect')
const { readFileSync } = require('node:fs')
const { homedir } = require('node:os')
const { join } = require('node:path')

async function main() {
  const PID = process.argv[2] || process.env.AO_PID
  if (!PID || !/^[A-Za-z0-9_-]{43}$/.test(PID)) {
    console.error('ao-localnet-send-commit-state: missing or malformed pid (need 43-char base64url).')
    console.error('usage: node scripts/ao-localnet-send-commit-state.cjs <pid>')
    process.exit(2)
  }

  const TIP_HEIGHT = process.env.TIP_HEIGHT || '1'
  const STATE_ROOT = process.env.STATE_ROOT_SHA256 ||
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
  const WALLET_PATH = process.env.WALLET || join(homedir(), '.aos.json')
  const GATEWAY = process.env.GATE || 'http://localhost:4000'
  const CU = process.env.CU || 'http://localhost:4004'
  const MU = process.env.MU || 'http://localhost:4002'

  let wallet
  try {
    wallet = JSON.parse(readFileSync(WALLET_PATH, 'utf-8'))
  } catch (err) {
    console.error(`ao-localnet-send-commit-state: cannot read wallet at ${WALLET_PATH}: ${err.message}`)
    process.exit(1)
  }

  const signer = createDataItemSigner(wallet)
  const ao = connect({ GATEWAY_URL: GATEWAY, CU_URL: CU, MU_URL: MU })

  let messageId
  try {
    messageId = await ao.message({
      process: PID,
      signer,
      tags: [
        { name: 'Action', value: 'Commit-State' },
        { name: 'Tip-Height', value: TIP_HEIGHT },
        { name: 'State-Root-Sha256', value: STATE_ROOT },
      ],
    })
  } catch (err) {
    console.error(`ao-localnet-send-commit-state: aoconnect.message failed: ${err.stack || err.message || err}`)
    process.exit(1)
  }

  if (!messageId || typeof messageId !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(messageId)) {
    console.error(`ao-localnet-send-commit-state: aoconnect returned an unexpected message id: ${JSON.stringify(messageId)}`)
    process.exit(1)
  }

  process.stdout.write(messageId + '\n')
  // aoconnect's underlying fetch keeps HTTP keep-alive sockets / agent timers
  // open and the event loop won't drain on its own; exit explicitly so callers
  // (the seal script, CI) don't have to add a kill timeout.
  process.exit(0)
}

main()
