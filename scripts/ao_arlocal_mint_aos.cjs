#!/usr/bin/env node
/**
 * Mint Winston on ArLocal for the global `aos` operator wallet (~/.aos.json).
 * ArLocal: GET /mint/{address}/{winston} then mine. See ao-localnet seed README.
 */
const fs = require('fs')
const path = require('path')
const os = require('os')

// CJS: `arweave` exports `init` on the module (no reliable `.default` across versions).
function loadArweave() {
  const m = require('arweave')
  if (m && typeof m.init === 'function') return m
  if (m && m.default && typeof m.default.init === 'function') return m.default
  throw new Error('arweave: no init(); set NODE_PATH to @permaweb/aos/node_modules')
}
const Arweave = loadArweave()

async function main() {
  // Default: fund ~/.aos.json. With one argument, fund that JWK (e.g. upstream bundler-wallet.json).
  const jwkPath = process.argv[2] ? path.resolve(process.argv[2]) : path.join(os.homedir(), '.aos.json')
  const label = process.argv[2] ? 'ao_arlocal_mint' : 'ao_arlocal_mint_aos'
  const logp = (m) => console.log(`[${label}] ${m}`)
  if (!fs.existsSync(jwkPath)) {
    console.error(`[${label}] no wallet at ${jwkPath} — run \`aos\` once, or pass a valid .json path`)
    process.exit(1)
  }
  const jwk = JSON.parse(fs.readFileSync(jwkPath, 'utf8'))
  const ar = Arweave.init({ host: 'localhost', port: 4000, protocol: 'http' })
  const addr = await ar.wallets.getAddress(jwk)
  const winston = process.env.ARLOCAL_MINT_WINSTON || '1000000000000000'
  const mintUrl = `http://localhost:4000/mint/${addr}/${winston}`
  logp(`${mintUrl}`)
  const r = await fetch(mintUrl)
  logp(`mint ${r.status} ${r.statusText}`)
  if (!r.ok) process.exit(1)
  const mineUrl = 'http://localhost:4000/mine/1'
  const m = await fetch(mineUrl)
  const j = await m.json().catch(() => ({}))
  logp(`${mineUrl} -> ${m.status} ${JSON.stringify(j)}`)
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
