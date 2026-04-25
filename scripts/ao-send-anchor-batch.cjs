#!/usr/bin/env node
// Send an Anchor-Interaction-Batch message to the AO process, signed by the owner's wallet.
//
// Usage: node scripts/ao-send-anchor-batch.cjs <pid> <wallet_path> <batch_root> <batch_size> <period_start> <period_end> <ledger_kind>

const { connect, createDataItemSigner } = require('@permaweb/aoconnect')
const { readFileSync } = require('node:fs')

async function main() {
  const PID = process.argv[2]
  const WALLET_PATH = process.argv[3]
  const BATCH_ROOT = process.argv[4]
  const BATCH_SIZE = process.argv[5]
  const PERIOD_START = process.argv[6]
  const PERIOD_END = process.argv[7]
  const LEDGER_KIND = process.argv[8]

  if (!PID || !WALLET_PATH || !BATCH_ROOT || !BATCH_SIZE || !PERIOD_START || !PERIOD_END || !LEDGER_KIND) {
    console.error('Usage: node scripts/ao-send-anchor-batch.cjs <pid> <wallet> <root> <size> <start> <end> <kind>')
    process.exit(2)
  }

  const GATEWAY = process.env.XION_AO_GATEWAY_URL || 'http://localhost:4000'
  const CU = process.env.XION_AO_CU_URL || 'http://localhost:4004'
  const MU = process.env.XION_AO_MU_URL || 'http://localhost:4002'

  let wallet
  try {
    wallet = JSON.parse(readFileSync(WALLET_PATH, 'utf-8'))
  } catch (err) {
    console.error(`ao-send-anchor-batch: cannot read wallet at ${WALLET_PATH}: ${err.message}`)
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
        { name: 'Action', value: 'Anchor-Interaction-Batch' },
        { name: 'Batch-Root-Sha256', value: BATCH_ROOT },
        { name: 'Batch-Size', value: BATCH_SIZE },
        { name: 'Period-Start-Unix', value: PERIOD_START },
        { name: 'Period-End-Unix', value: PERIOD_END },
        { name: 'Ledger-Kind', value: LEDGER_KIND },
      ],
    })
  } catch (err) {
    console.error(`ao-send-anchor-batch: aoconnect.message failed: ${err.stack || err.message || err}`)
    process.exit(1)
  }

  if (!messageId || typeof messageId !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(messageId)) {
    console.error(`ao-send-anchor-batch: aoconnect returned an unexpected message id: ${JSON.stringify(messageId)}`)
    process.exit(1)
  }

  process.stdout.write(messageId + '\n')
  process.exit(0)
}

main()
