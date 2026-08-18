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
