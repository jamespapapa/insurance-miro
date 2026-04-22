import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export const repoRoot = path.resolve(__dirname, '..')

const stripQuotes = (value) => {
  if (!value) return value
  const trimmed = value.trim()
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1)
  }
  return trimmed
}

export const loadDotEnv = (envPath = path.join(repoRoot, '.env')) => {
  if (!fs.existsSync(envPath)) return

  const content = fs.readFileSync(envPath, 'utf8')
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue

    const match = line.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/)
    if (!match) continue

    const [, key, rawValue] = match
    if (process.env[key] !== undefined) continue
    process.env[key] = stripQuotes(rawValue)
  }
}

export const resolveFromRepo = (inputPath, fallbackRelativePath) => {
  const candidate = inputPath || fallbackRelativePath
  if (!candidate) return undefined
  return path.isAbsolute(candidate) ? candidate : path.resolve(repoRoot, candidate)
}

export const createBasicAuthHeader = () => {
  const password = process.env.OPENCODE_SERVER_PASSWORD
  if (!password) return undefined
  const username = process.env.OPENCODE_SERVER_USERNAME || 'opencode'
  return `Basic ${Buffer.from(`${username}:${password}`).toString('base64')}`
}
