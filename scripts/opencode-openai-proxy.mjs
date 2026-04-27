import http from 'node:http'
import { randomUUID } from 'node:crypto'
import { URL } from 'node:url'

import { createBasicAuthHeader, loadDotEnv, repoRoot } from './opencode-env.mjs'

loadDotEnv()

const host = process.env.OPENCODE_PROXY_HOST || '127.0.0.1'
const port = Number(process.env.OPENCODE_PROXY_PORT || '4097')
const directory = process.env.OPENCODE_DIRECTORY || repoRoot
const opencodeServerUrl = (process.env.OPENCODE_SERVER_URL || 'http://127.0.0.1:4096').replace(/\/$/, '')
const defaultProviderID = process.env.OPENCODE_MODEL_PROVIDER_ID || 'openai'
const defaultModelID = process.env.OPENCODE_MODEL_ID || process.env.LLM_MODEL_NAME || 'gpt-5.2'
const defaultVariant = process.env.OPENCODE_MODEL_VARIANT || undefined
const authHeader = createBasicAuthHeader()
const skipNgrokWarning = !['0', 'false', 'no'].includes(
  String(process.env.OPENCODE_NGROK_SKIP_BROWSER_WARNING || '').toLowerCase()
)

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, content-type',
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
}

const sendJson = (res, statusCode, payload) => {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    ...corsHeaders,
  })
  res.end(JSON.stringify(payload))
}

const readBody = async (req) => {
  const chunks = []
  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk))
  }
  const raw = Buffer.concat(chunks).toString('utf8')
  if (!raw) return {}
  return JSON.parse(raw)
}

const normalizeMessageContent = (content) => {
  if (typeof content === 'string') return content.trim()
  if (!Array.isArray(content)) return ''

  return content
    .map((part) => {
      if (!part || typeof part !== 'object') return ''
      if (part.type === 'text') return typeof part.text === 'string' ? part.text : ''
      if (part.type === 'image_url') {
        const url = typeof part.image_url === 'string' ? part.image_url : part.image_url?.url
        return url ? `[image] ${url}` : '[image]'
      }
      return ''
    })
    .filter(Boolean)
    .join('\n')
    .trim()
}

const buildPromptPayload = (messages, responseFormat) => {
  const systemSections = []
  const transcript = []

  for (const message of messages) {
    if (!message || typeof message !== 'object') continue
    const role = message.role || 'user'
    const text = normalizeMessageContent(message.content)

    if (role === 'system') {
      if (text) systemSections.push(text)
      continue
    }

    if (!text) continue

    if (role === 'assistant') transcript.push(`Assistant:\n${text}`)
    else if (role === 'tool') transcript.push(`Tool${message.tool_call_id ? ` (${message.tool_call_id})` : ''}:\n${text}`)
    else transcript.push(`User:\n${text}`)
  }

  if (responseFormat?.type === 'json_object') {
    systemSections.push(
      'Return exactly one valid JSON object. Do not wrap it in markdown fences. Do not add any commentary before or after the JSON.'
    )
  }

  transcript.push('Please answer the latest user request as the assistant.')

  return {
    system: systemSections.join('\n\n').trim() || undefined,
    prompt: transcript.join('\n\n').trim(),
  }
}

const selectModel = (requestedModel) => {
  const candidate = typeof requestedModel === 'string' && requestedModel.trim() ? requestedModel.trim() : defaultModelID
  if (candidate.includes('/')) {
    const [providerID, ...rest] = candidate.split('/')
    return {
      providerID,
      modelID: rest.join('/') || defaultModelID,
    }
  }

  return {
    providerID: defaultProviderID,
    modelID: candidate,
  }
}

const parseJsonCandidate = (text) => {
  const cleaned = text
    .trim()
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/\s*```$/, '')
    .trim()

  const candidates = [cleaned]
  const firstBrace = cleaned.indexOf('{')
  const lastBrace = cleaned.lastIndexOf('}')
  if (firstBrace >= 0 && lastBrace > firstBrace) {
    candidates.push(cleaned.slice(firstBrace, lastBrace + 1))
  }

  for (const candidate of candidates) {
    try {
      return JSON.stringify(JSON.parse(candidate))
    } catch {
      // keep trying
    }
  }

  throw new Error(`OpenCode did not return valid JSON: ${cleaned.slice(0, 400)}`)
}

const opencodeRequest = async (pathname, { method = 'GET', body } = {}) => {
  const headers = {}
  if (authHeader) headers.Authorization = authHeader
  if (skipNgrokWarning) headers['ngrok-skip-browser-warning'] = 'true'
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  const response = await fetch(`${opencodeServerUrl}${pathname}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  const text = await response.text()
  let data
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }

  if (!response.ok) {
    const message = typeof data === 'string' ? data : JSON.stringify(data)
    throw new Error(`OpenCode ${method} ${pathname} failed (${response.status}): ${message}`)
  }

  return data
}

const createSession = async () => {
  const encodedDirectory = encodeURIComponent(directory)
  return opencodeRequest(`/session?directory=${encodedDirectory}`, {
    method: 'POST',
    body: { title: 'MiroFish OpenCode bridge' },
  })
}

const promptSession = async ({ sessionID, body, promptPayload, modelSelection }) => {
  const encodedDirectory = encodeURIComponent(directory)
  const payload = {
    model: {
      providerID: modelSelection.providerID,
      modelID: modelSelection.modelID,
      ...(defaultVariant ? { variant: defaultVariant } : {}),
    },
    ...(promptPayload.system ? { system: promptPayload.system } : {}),
    parts: [
      {
        type: 'text',
        text: promptPayload.prompt,
      },
    ],
  }

  return opencodeRequest(`/session/${sessionID}/message?directory=${encodedDirectory}`, {
    method: 'POST',
    body: payload,
  })
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const getMessage = async ({ sessionID, messageID }) => {
  const encodedDirectory = encodeURIComponent(directory)
  return opencodeRequest(`/session/${sessionID}/message/${messageID}?directory=${encodedDirectory}`)
}

const getSessionMessages = async ({ sessionID, limit = 10 }) => {
  const encodedDirectory = encodeURIComponent(directory)
  return opencodeRequest(`/session/${sessionID}/message?directory=${encodedDirectory}&limit=${limit}`)
}

const partsToText = (parts = []) =>
  parts
    .filter((part) => part?.type === 'text' && typeof part.text === 'string' && !part.ignored)
    .map((part) => part.text)
    .join('')
    .trim()

const formatInfoError = (error) => {
  if (!error) return undefined
  if (typeof error === 'string') return error
  if (typeof error.message === 'string' && error.message.trim()) return error.message.trim()
  try {
    return JSON.stringify(error)
  } catch {
    return String(error)
  }
}

const resolveAssistantContent = async ({ sessionID, opencodeResponse }) => {
  let content = partsToText(opencodeResponse.parts)
  if (content) return content

  const immediateError = formatInfoError(opencodeResponse?.info?.error)
  const messageID = opencodeResponse?.info?.id

  if (messageID) {
    for (let attempt = 0; attempt < 8; attempt += 1) {
      await sleep(350 * (attempt + 1))
      const latestMessage = await getMessage({ sessionID, messageID })
      content = partsToText(latestMessage.parts)
      if (content) return content

      const delayedError = formatInfoError(latestMessage?.info?.error)
      if (delayedError) {
        throw new Error(`OpenCode message error: ${delayedError}`)
      }
    }
  }

  const sessionMessages = await getSessionMessages({ sessionID, limit: 20 })
  if (Array.isArray(sessionMessages)) {
    for (const message of [...sessionMessages].reverse()) {
      if (message?.info?.role !== 'assistant') continue
      content = partsToText(message.parts)
      if (content) return content
      const sessionError = formatInfoError(message?.info?.error)
      if (sessionError) {
        throw new Error(`OpenCode session error: ${sessionError}`)
      }
    }
  }

  if (immediateError) {
    throw new Error(`OpenCode response error: ${immediateError}`)
  }

  throw new Error('OpenCode returned no assistant text parts')
}

const buildChatCompletionResponse = ({ requestBody, opencodeResponse, content, modelSelection }) => {
  const promptTokens = opencodeResponse?.info?.tokens?.input ?? 0
  const completionTokens = opencodeResponse?.info?.tokens?.output ?? 0

  return {
    id: `chatcmpl_${randomUUID()}`,
    object: 'chat.completion',
    created: Math.floor(Date.now() / 1000),
    model: typeof requestBody.model === 'string' && requestBody.model ? requestBody.model : modelSelection.modelID,
    choices: [
      {
        index: 0,
        message: {
          role: 'assistant',
          content,
        },
        finish_reason: 'stop',
      },
    ],
    usage: {
      prompt_tokens: promptTokens,
      completion_tokens: completionTokens,
      total_tokens: promptTokens + completionTokens,
    },
  }
}

const server = http.createServer(async (req, res) => {
  if (!req.url) {
    sendJson(res, 400, { error: { message: 'Missing request URL', type: 'invalid_request_error' } })
    return
  }

  const url = new URL(req.url, `http://${req.headers.host || `${host}:${port}`}`)

  if (req.method === 'OPTIONS') {
    res.writeHead(204, corsHeaders)
    res.end()
    return
  }

  if (req.method === 'GET' && (url.pathname === '/health' || url.pathname === '/v1/health')) {
    sendJson(res, 200, {
      ok: true,
      opencodeServerUrl,
      directory,
      defaultProviderID,
      defaultModelID,
    })
    return
  }

  if (req.method === 'GET' && url.pathname === '/v1/models') {
    sendJson(res, 200, {
      object: 'list',
      data: [
        {
          id: defaultModelID,
          object: 'model',
          owned_by: defaultProviderID,
        },
      ],
    })
    return
  }

  if (req.method !== 'POST' || !['/v1/chat/completions', '/chat/completions'].includes(url.pathname)) {
    sendJson(res, 404, { error: { message: 'Not found', type: 'invalid_request_error' } })
    return
  }

  try {
    const requestBody = await readBody(req)
    const messages = Array.isArray(requestBody.messages) ? requestBody.messages : []
    const promptPayload = buildPromptPayload(messages, requestBody.response_format)
    const modelSelection = selectModel(requestBody.model)

    const session = await createSession()
    const opencodeResponse = await promptSession({
      sessionID: session.id,
      body: requestBody,
      promptPayload,
      modelSelection,
    })

    let content = await resolveAssistantContent({
      sessionID: session.id,
      opencodeResponse,
    })

    if (requestBody.response_format?.type === 'json_object') {
      content = parseJsonCandidate(content)
    }

    sendJson(
      res,
      200,
      buildChatCompletionResponse({
        requestBody,
        opencodeResponse,
        content,
        modelSelection,
      })
    )
  } catch (error) {
    sendJson(res, 502, {
      error: {
        message: error instanceof Error ? error.message : String(error),
        type: 'server_error',
      },
    })
  }
})

server.listen(port, host, () => {
  console.log(`OpenCode OpenAI-compatible proxy listening on http://${host}:${port}/v1`) // eslint-disable-line no-console
  console.log(`Forwarding to ${opencodeServerUrl} with default model ${defaultProviderID}/${defaultModelID}`) // eslint-disable-line no-console
})
