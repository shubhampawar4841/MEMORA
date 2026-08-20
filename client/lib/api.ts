const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export type DocumentItem = {
  document_id: string
  source: string
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

export async function uploadPdf(file: File) {
  const body = new FormData()
  body.append('file', file)
  const res = await fetch(`${API_URL}/upload-pdf`, {
    method: 'POST',
    body,
  })
  return handle<UploadResponse>(res)
}

export async function deleteDocument(documentId: string) {
  const res = await fetch(`${API_URL}/documents/${documentId}`, {
    method: 'DELETE',
  })
  return handle<{ document_id: string; deleted: boolean; chunks_removed: number }>(res)
}

export async function renameDocument(documentId: string, source: string) {
  const res = await fetch(`${API_URL}/documents/${documentId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source }),
  })
  return handle<{ document_id: string; source: string }>(res)
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
