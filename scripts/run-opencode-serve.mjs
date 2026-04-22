import { spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

import { loadDotEnv, repoRoot, resolveFromRepo } from './opencode-env.mjs'

loadDotEnv()

const parseServerUrl = () => {
  const raw = process.env.OPENCODE_SERVER_URL || 'http://127.0.0.1:4096'
  const url = new URL(raw)
  return {
    hostname: process.env.OPENCODE_SERVER_HOST || url.hostname || '127.0.0.1',
    port: process.env.OPENCODE_SERVER_PORT || url.port || '4096',
  }
}

const findSourceDir = () => {
  const explicit = process.env.OPENCODE_SOURCE_DIR
  const defaultDir = path.resolve(repoRoot, '../opencode')
  const candidate = resolveFromRepo(explicit, defaultDir)
  if (candidate && fs.existsSync(candidate)) return candidate
  return undefined
}

const { hostname, port } = parseServerUrl()
const sourceDir = findSourceDir()
const env = {
  ...process.env,
}

const opencodePath = sourceDir ? path.join(sourceDir, 'packages/opencode/src/index.ts') : undefined

let command
let args
let cwd

if (sourceDir && opencodePath && fs.existsSync(opencodePath)) {
  command = 'bun'
  args = ['dev', 'serve', '--port', String(port), '--hostname', hostname]
  cwd = sourceDir
} else {
  command = 'opencode'
  args = ['serve', '--port', String(port), '--hostname', hostname]
  cwd = repoRoot
}

console.log(`Starting OpenCode server via ${command} ${args.join(' ')} (cwd=${cwd})`) // eslint-disable-line no-console

const child = spawn(command, args, {
  cwd,
  env,
  stdio: 'inherit',
})

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal)
    return
  }
  process.exit(code ?? 0)
})
