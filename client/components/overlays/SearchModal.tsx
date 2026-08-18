'use client'

import { useState } from 'react'
import { Command, Search } from 'lucide-react'
import { searchKnowledge, type SearchResult } from '@/lib/api'
import { FileIcon } from '@/components/ui/FileIcon'
import { ModalShell } from '@/components/overlays/ModalShell'

type SearchModalProps = {
  onClose: () => void
  documentId?: string | null
  documentLabel?: string | null
}

export function SearchModal({
  onClose,
  documentId = null,
  documentLabel = null,
}: SearchModalProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searchError, setSearchError] = useState<string | null>(null)

  const runSearch = async () => {
    const q = searchQuery.trim()
    if (!q || searching) return

    setSearching(true)
    setSearchError(null)

    try {
      const res = await searchKnowledge(q, documentId ?? undefined)
      setSearchResults(res.results)
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : 'Search failed')
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }

  return (
    <ModalShell
      eyebrow="COMMAND CENTER"
      title={documentLabel ? `Search ${documentLabel}` : 'Search workspace'}
      onClose={onClose}
    >
      <div>
        <div className="command-search">
          <Search size={18} />
          <input
            autoFocus
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void runSearch()
            }}
            placeholder="Search indexed chunks..."
          />
          <kbd>ENTER</kbd>
        </div>

        <div className="command-hint">
          <Command size={14} />
          Uses POST /search{documentId ? ' (document-scoped)' : ''}
        </div>

        {searching && (
          <p style={{ marginTop: 48, color: '#9298ae' }}>Searching…</p>
        )}

        {searchError && (
          <p style={{ marginTop: 48, color: '#f2b84b' }}>{searchError}</p>
        )}

        {!searching && searchResults.length > 0 && (
          <div className="recent-list" style={{ marginTop: 48 }}>
            {searchResults.map((r, i) => (
              <div
                className="recent-item"
                key={`${r.metadata.document_id}-${i}`}
              >
                <FileIcon color="violet" />
                <div>
                  <strong>{r.metadata.source ?? 'Chunk'}</strong>
                  <span>
                    Page {r.metadata.page ?? '—'}
                    {' · score '}
                    {r.rerank_score.toFixed(3)}
                  </span>
                  <span
                    style={{
                      display: 'block',
                      marginTop: 6,
                      color: '#a4aabe',
                    }}
                  >
                    {r.text.slice(0, 180)}
                    {r.text.length > 180 ? '…' : ''}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </ModalShell>
  )
}
