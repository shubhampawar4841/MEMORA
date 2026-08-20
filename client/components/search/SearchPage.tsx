'use client'

import { useCallback, useEffect, useState } from 'react'
import { MessageSquare, Network, Search } from 'lucide-react'
import {
  searchMemory,
  type MemoryHit,
  type MemorySearchMode,
} from '@/lib/api'

type Props = {
  initialQuery?: string | null
  onAskChat?: (query: string, documentId?: string | null) => void
  onExploreMemory?: (query: string) => void
}

const MODES: { id: MemorySearchMode; label: string }[] = [
  { id: 'hybrid', label: 'Hybrid' },
  { id: 'memories', label: 'Memories' },
  { id: 'documents', label: 'Documents' },
]

export function SearchPage({
  initialQuery = null,
  onAskChat,
  onExploreMemory,
}: Props) {
  const [query, setQuery] = useState(initialQuery || '')
  const [mode, setMode] = useState<MemorySearchMode>('hybrid')
  const [results, setResults] = useState<MemoryHit[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [containerTag, setContainerTag] = useState<string | null>(null)

  const run = useCallback(async (q: string, m: MemorySearchMode) => {
    const trimmed = q.trim()
    if (!trimmed) return
    setLoading(true)
    setError(null)
    try {
      const res = await searchMemory({ q: trimmed, mode: m, limit: 12 })
      if (res.error && !res.ok) setError(res.error)
      setResults(res.results || [])
      setContainerTag(res.container_tag || null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (initialQuery?.trim()) {
      setQuery(initialQuery)
      void run(initialQuery, mode)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery])

  return (
    <section className="content-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">RECALL</span>
          <h1>Search</h1>
          <p>
            Hybrid recall across memories and documents
            {containerTag ? (
              <>
                {' '}in <code className="inline-code">{containerTag}</code>
              </>
            ) : (
              '.'
            )}
          </p>
        </div>
      </div>

      <form
        className="memory-explore"
        onSubmit={(e) => {
          e.preventDefault()
          void run(query, mode)
        }}
      >
        <div className="field memory-field">
          <Search size={16} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search memories and knowledge…"
            autoFocus
          />
        </div>
        <button className="primary-btn" type="submit" disabled={loading || !query.trim()}>
          {loading ? 'Searching…' : 'Search'}
        </button>
      </form>

      <div className="folder-chips" style={{ marginBottom: 18 }}>
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            className={`filter-btn ${mode === m.id ? 'active' : ''}`}
            onClick={() => {
              setMode(m.id)
              if (query.trim()) void run(query, m.id)
            }}
          >
            {m.label}
          </button>
        ))}
      </div>

      {error ? <p className="form-error">{error}</p> : null}

      {results.length === 0 && !loading ? (
        <div className="empty-panel">
          <Search size={21} />
          <h2>No results yet</h2>
          <p>Try hybrid mode after uploading docs or connecting sources.</p>
        </div>
      ) : (
        <ul className="hit-list search-page-hits">
          {results.map((r) => (
            <li key={r.id}>
              <div className="search-hit-card">
                <div className="search-hit-meta">
                  <span className={`kind-pill ${r.kind}`}>{r.kind}</span>
                  <em>{r.score.toFixed(3)}</em>
                  {r.source ? <span className="muted">{r.source}</span> : null}
                </div>
                <p>{r.text}</p>
                <div className="row-actions">
                  {onExploreMemory ? (
                    <button
                      type="button"
                      className="filter-btn"
                      onClick={() => onExploreMemory(r.text.slice(0, 120))}
                    >
                      <Network size={14} />
                      Memory graph
                    </button>
                  ) : null}
                  {onAskChat ? (
                    <button
                      type="button"
                      className="filter-btn"
                      onClick={() =>
                        onAskChat(
                          r.text.slice(0, 160),
                          (r.metadata?.document_id as string) || null,
                        )
                      }
                    >
                      <MessageSquare size={14} />
                      Ask in Chat
                    </button>
                  ) : null}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
