const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export const KNOWLEDGE_FOLDERS = [
  'personal',
  'work',
  'study',
  'other',
] as const

export type KnowledgeFolder = (typeof KNOWLEDGE_FOLDERS)[number]

export type DocumentItem = {
  document_id: string
  source: string
  folder?: KnowledgeFolder | string
  pages: number[]
  chunks: number
}

export type AskSource = {
  source: string | null
  page: number | null
  chunk_index: number | null
  distance: number
  rerank_score: number
  text?: string | null
  folder?: string | null
}

export type AskResponse = {
  query: string
  document_id: string | null
  answer: string
  sources: AskSource[]
}

export type SearchResult = {
  text: string
  distance: number
  rerank_score: number
  metadata: {
    source?: string
    page?: number
    document_id?: string
    chunk_index?: number
    folder?: string
  }
}

export type SearchResponse = {
  query: string
  document_id: string | null
  results: SearchResult[]
}

export type UploadResponse = {
  filename: string
  document_id: string
  pages: number
  chunks: number
  embedding_dimension: number
  folder?: string
  source?: string
  error?: string
}

export type BatchUploadItemResult = {
  fileName: string
  ok: boolean
  response?: UploadResponse
  error?: string
}

export type ConversationSummary = {
  id: string
  title: string
  document_id: string | null
  created_at: string
  updated_at: string
  message_count: number
}

export type ConversationMessage = {
  id: string
  role: string
  content: string
  sources: AskSource[]
  created_at: string
}

export type ConversationDetail = {
  id: string
  title: string
  document_id: string | null
  created_at: string
  updated_at: string
  messages: ConversationMessage[]
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text()
    try {
      const data = JSON.parse(text) as { detail?: unknown }
      if (typeof data.detail === 'string' && data.detail.trim()) {
        throw new Error(data.detail)
      }
    } catch (err) {
      if (err instanceof Error && err.message !== text) throw err
    }
    throw new Error(text || `Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

export async function getHome() {
  const res = await fetch(`${API_URL}/`)
  return handle<{ message: string }>(res)
}

export async function listDocuments() {
  const res = await fetch(`${API_URL}/documents`)
  return handle<{ documents: DocumentItem[] }>(res)
}

export async function uploadDocument(
  file: File,
  options?: { folder?: string; source?: string },
) {
  const body = new FormData()
  body.append('file', file)
  body.append('folder', options?.folder || 'other')
  if (options?.source?.trim()) {
    body.append('source', options.source.trim())
  }

  // Prefer /upload-document; fall back to /upload-pdf for older backend processes.
  let res = await fetch(`${API_URL}/upload-document`, {
    method: 'POST',
    body,
  })
  if (res.status === 404) {
    const retry = new FormData()
    retry.append('file', file)
    retry.append('folder', options?.folder || 'other')
    if (options?.source?.trim()) {
      retry.append('source', options.source.trim())
    }
    res = await fetch(`${API_URL}/upload-pdf`, {
      method: 'POST',
      body: retry,
    })
  }

  if (!res.ok) {
    const text = await res.text()
    let message = text || `Request failed (${res.status})`
    try {
      const parsed = JSON.parse(text) as { detail?: unknown; error?: string }
      if (typeof parsed.detail === 'string') message = parsed.detail
      else if (parsed.error) message = parsed.error
    } catch {
      // keep raw text
    }
    throw new Error(message)
  }
  return res.json() as Promise<UploadResponse>
}

export async function uploadDocuments(
  files: File[],
  options?: {
    folder?: string
    sourceForFile?: (file: File) => string | undefined
    onProgress?: (completed: number, total: number, fileName: string) => void
  },
): Promise<BatchUploadItemResult[]> {
  const results: BatchUploadItemResult[] = []
  const total = files.length

  for (let index = 0; index < files.length; index += 1) {
    const file = files[index]
    options?.onProgress?.(index, total, file.name)

    try {
      const response = await uploadDocument(file, {
        folder: options?.folder,
        source: options?.sourceForFile?.(file),
      })

      if (response.error) {
        results.push({
          fileName: file.name,
          ok: false,
          error: response.error,
        })
      } else {
        results.push({
          fileName: file.name,
          ok: true,
          response,
        })
      }
    } catch (err) {
      results.push({
        fileName: file.name,
        ok: false,
        error: err instanceof Error ? err.message : 'Upload failed',
      })
    }
  }

  options?.onProgress?.(total, total, '')
  return results
}

/** @deprecated Use uploadDocument */
export async function uploadPdf(
  file: File,
  options?: { folder?: string; source?: string },
) {
  return uploadDocument(file, options)
}

export async function deleteDocument(documentId: string) {
  const res = await fetch(`${API_URL}/documents/${documentId}`, {
    method: 'DELETE',
  })
  return handle<{ document_id: string; deleted: boolean; chunks_removed: number }>(res)
}

export async function renameDocument(
  documentId: string,
  payload: { source?: string; folder?: string },
) {
  const res = await fetch(`${API_URL}/documents/${documentId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return handle<{ document_id: string; source: string | null; folder: string }>(
    res,
  )
}

export async function reindexDocument(documentId: string) {
  const res = await fetch(`${API_URL}/documents/${documentId}/reindex`, {
    method: 'POST',
  })
  return handle<{
    document_id: string
    filename: string | null
    pages: number
    chunks: number
    embedding_dimension: number
    error: string | null
    folder?: string | null
  }>(res)
}

export async function searchKnowledge(query: string, documentId?: string) {
  const params = new URLSearchParams({ query })
  if (documentId) params.set('document_id', documentId)
  const res = await fetch(`${API_URL}/search?${params}`, { method: 'POST' })
  return handle<SearchResponse>(res)
}

export async function askQuestion(query: string, documentId?: string) {
  const params = new URLSearchParams({ query })
  if (documentId) params.set('document_id', documentId)
  const res = await fetch(`${API_URL}/ask?${params}`, { method: 'POST' })
  return handle<AskResponse>(res)
}

export async function askQuestionStream(
  query: string,
  documentId: string | undefined,
  onToken: (token: string) => void,
): Promise<AskResponse> {
  const params = new URLSearchParams({ query })
  if (documentId) params.set('document_id', documentId)

  const res = await fetch(`${API_URL}/ask/stream?${params}`, {
    method: 'POST',
  })

  if (!res.ok || !res.body) {
    const text = await res.text()
    throw new Error(text || `Stream failed (${res.status})`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let answer = ''
  let sources: AskSource[] = []

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''

    for (const part of parts) {
      const line = part
        .split('\n')
        .find((l) => l.startsWith('data: '))
      if (!line) continue
      const payload = JSON.parse(line.slice(6)) as {
        type: string
        token?: string
        answer?: string
        sources?: AskSource[]
      }
      if (payload.type === 'token' && payload.token) {
        answer += payload.token
        onToken(payload.token)
      }
      if (payload.type === 'final') {
        answer = payload.answer ?? answer
        sources = payload.sources ?? []
      }
    }
  }

  return {
    query,
    document_id: documentId ?? null,
    answer,
    sources,
  }
}

export async function listConversations() {
  const res = await fetch(`${API_URL}/conversations`)
  return handle<{ conversations: ConversationSummary[] }>(res)
}

export async function createConversation(input?: {
  title?: string
  document_id?: string | null
}) {
  const res = await fetch(`${API_URL}/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input ?? {}),
  })
  return handle<ConversationDetail>(res)
}

export async function getConversation(id: string) {
  const res = await fetch(`${API_URL}/conversations/${id}`)
  return handle<ConversationDetail>(res)
}

export async function renameConversation(id: string, title: string) {
  const res = await fetch(`${API_URL}/conversations/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
  return handle<ConversationDetail>(res)
}

export async function deleteConversation(id: string) {
  const res = await fetch(`${API_URL}/conversations/${id}`, {
    method: 'DELETE',
  })
  return handle<{ deleted: boolean; id: string }>(res)
}

export async function askInConversation(conversationId: string, query: string) {
  const params = new URLSearchParams({ query })
  const res = await fetch(
    `${API_URL}/conversations/${conversationId}/ask?${params}`,
    { method: 'POST' },
  )
  return handle<AskResponse>(res)
}

export type AgentStep = {
  tool: string
  status: string
}

export type AgentChatResponse = {
  success: boolean
  message: string
  route?: string | null
  steps: AgentStep[]
  requires_confirmation?: boolean
  pending_tool?: string | null
  sources?: AskSource[]
  document_id?: string | null
  conversation_id?: string | null
}

export type WebIngestResponse = {
  document_id: string | null
  source: string | null
  url: string | null
  mode: string | null
  pages: number
  chunks: number
  embedding_dimension: number
  error: string | null
}

export async function agentChatStream(
  message: string,
  options: {
    documentId?: string | null
    conversationId?: string | null
    forceWeb?: boolean
    onStatus?: (status: string) => void
    onRoute?: (route: string) => void
  } = {},
): Promise<AgentChatResponse> {
  const res = await fetch(`${API_URL}/api/agent/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      documentId: options.documentId ?? undefined,
      conversationId: options.conversationId ?? undefined,
      forceWeb: options.forceWeb ?? false,
    }),
  })

  if (!res.ok || !res.body) {
    const text = await res.text()
    let detail = text || `Agent stream failed (${res.status})`
    try {
      const parsed = JSON.parse(text) as { detail?: string; message?: string }
      detail = parsed.detail || parsed.message || detail
    } catch {
      // keep raw text
    }
    throw new Error(detail)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let final: AgentChatResponse = {
    success: true,
    message: '',
    steps: [],
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''

    for (const part of parts) {
      const line = part
        .split('\n')
        .find((l) => l.startsWith('data: '))
      if (!line) continue
      const payload = JSON.parse(line.slice(6)) as {
        type: string
        message?: string
        route?: string
        success?: boolean
        steps?: AgentStep[]
        requires_confirmation?: boolean
        pending_tool?: string | null
        sources?: AskSource[]
        document_id?: string | null
        conversation_id?: string | null
      }

      if (payload.type === 'route' && payload.route) {
        options.onRoute?.(payload.route)
      }
      if (payload.type === 'status' && payload.message) {
        options.onStatus?.(payload.message)
      }
      if (payload.type === 'final') {
        final = {
          success: payload.success ?? true,
          message: payload.message ?? '',
          route: payload.route,
          steps: payload.steps ?? [],
          requires_confirmation: payload.requires_confirmation,
          pending_tool: payload.pending_tool,
          sources: payload.sources,
          document_id: payload.document_id,
          conversation_id: payload.conversation_id,
        }
      }
    }
  }

  return final
}

export async function ingestWebsite(input: {
  url: string
  mode?: string
  limit?: number
  search?: string
  documentId?: string
}) {
  const res = await fetch(`${API_URL}/api/agent/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  return handle<WebIngestResponse>(res)
}

// ------------------------------------------------------------
// Supermemory connectors (Gmail / GitHub OAuth)
// ------------------------------------------------------------

export type ConnectionItem = {
  id?: string
  provider?: string
  email?: string | null
  createdAt?: string
  documentLimit?: number | null
  [key: string]: unknown
}

export type ConnectStartResponse = {
  ok: boolean
  provider: string
  user_id: string
  container_tag: string
  auth_link: string
  connection_id?: string
  expires_in?: string
  redirects_to?: string
  plan_note?: string
}

export async function getConnectDefaults() {
  const res = await fetch(`${API_URL}/connect/me`)
  return handle<{
    user_id: string
    container_tag: string
    plan_notes: Record<string, string>
  }>(res)
}

export async function listConnections(userId?: string) {
  const q = userId ? `?user_id=${encodeURIComponent(userId)}` : ''
  const res = await fetch(`${API_URL}/connections${q}`)
  return handle<{
    ok: boolean
    user_id?: string
    container_tag?: string
    connections: ConnectionItem[]
    error?: string
    plan_notes?: Record<string, string>
  }>(res)
}

export async function startConnect(
  provider: 'gmail' | 'github',
  options?: { userId?: string; redirectUrl?: string },
) {
  const path =
    provider === 'gmail' ? '/connect/gmail' : '/connect/github'
  const redirectUrl =
    options?.redirectUrl ||
    `${typeof window !== 'undefined' ? window.location.origin : ''}/?integrations=connected`
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: options?.userId,
      redirect_url: redirectUrl,
    }),
  })
  return handle<ConnectStartResponse>(res)
}

export async function deleteConnection(
  connectionId: string,
  deleteDocuments = false,
) {
  const q = deleteDocuments ? '?delete_documents=true' : ''
  const res = await fetch(
    `${API_URL}/connections/${encodeURIComponent(connectionId)}${q}`,
    { method: 'DELETE' },
  )
  return handle<{ ok: boolean; result?: unknown }>(res)
}

// ------------------------------------------------------------
// Memory / graph / hybrid search (Supermemory)
// ------------------------------------------------------------

export type MemorySearchMode = 'hybrid' | 'memories' | 'documents'

export type MemoryHit = {
  id: string
  text: string
  score: number
  kind: 'memory' | 'document' | string
  source?: string | null
  metadata?: Record<string, unknown>
  related?: unknown[]
}

export type MemoryProfile = {
  ok: boolean
  user_id: string
  container_tag: string
  static: string[]
  dynamic: string[]
  static_count?: number
  dynamic_count?: number
  error?: string
}

export type MemoryGraphNode = {
  id: string
  label: string
  kind: string
  score: number
}

export type MemoryGraphEdge = {
  id: string
  source: string
  target: string
  relation: string
}

export type MemoryActivityItem = {
  id: string
  type: 'document' | 'connection' | string
  title: string
  status: string
  at?: string | null
  provider?: string | null
  email?: string | null
}

export async function getMemoryProfile(userId?: string) {
  const q = userId ? `?user_id=${encodeURIComponent(userId)}` : ''
  const res = await fetch(`${API_URL}/memory/profile${q}`)
  return handle<MemoryProfile>(res)
}

export async function searchMemory(input: {
  q: string
  mode?: MemorySearchMode
  limit?: number
  userId?: string
}) {
  const res = await fetch(`${API_URL}/memory/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      q: input.q,
      mode: input.mode || 'hybrid',
      limit: input.limit ?? 10,
      user_id: input.userId,
    }),
  })
  return handle<{
    ok: boolean
    query: string
    mode: string
    results: MemoryHit[]
    count?: number
    container_tag?: string
    error?: string
  }>(res)
}

export async function getMemoryGraph(input: {
  q: string
  limit?: number
  userId?: string
}) {
  const res = await fetch(`${API_URL}/memory/graph`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      q: input.q,
      limit: input.limit ?? 12,
      user_id: input.userId,
    }),
  })
  return handle<{
    ok: boolean
    query: string
    nodes: MemoryGraphNode[]
    edges: MemoryGraphEdge[]
    results: MemoryHit[]
    container_tag?: string
    error?: string
  }>(res)
}

export async function getMemoryActivity(userId?: string, limit = 30) {
  const params = new URLSearchParams()
  if (userId) params.set('user_id', userId)
  params.set('limit', String(limit))
  const res = await fetch(`${API_URL}/memory/activity?${params}`)
  return handle<{
    ok: boolean
    user_id: string
    container_tag: string
    items: MemoryActivityItem[]
    error?: string
  }>(res)
}

export async function getVoiceStatus() {
  const res = await fetch(`${API_URL}/voice/status`)
  return handle<{
    configured: boolean
    url_set: boolean
    agent_name?: string
  }>(res)
}

export type GoogleAuthStatus = {
  connected: boolean
  user_id?: string
  email?: string
  name?: string | null
  scopes?: string[]
  has_refresh_token?: boolean
  expires_at?: number | null
  updated_at?: string
}

export function getGoogleSignInUrl() {
  return `${API_URL}/auth/google`
}

export async function getGoogleAuthStatus() {
  const res = await fetch(`${API_URL}/auth/google/status`)
  return handle<GoogleAuthStatus>(res)
}

