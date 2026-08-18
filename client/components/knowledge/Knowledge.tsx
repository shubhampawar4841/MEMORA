'use client'

import { useMemo, useState } from 'react'
import { Plus } from 'lucide-react'
import type { DocumentItem } from '@/lib/api'
import { DocumentList } from '@/components/knowledge/DocumentList'
import { KnowledgeStats } from '@/components/knowledge/KnowledgeStats'
import { KnowledgeToolbar } from '@/components/knowledge/KnowledgeToolbar'

type KnowledgeProps = {
  documents: DocumentItem[]
  loading: boolean
  error: string | null
  onUpload: () => void
  onRefresh: () => void
}

export function Knowledge({
  documents,
  loading,
  error,
  onUpload,
  onRefresh,
}: KnowledgeProps) {
  const [query, setQuery] = useState('')

  const filtered = useMemo(
    () =>
      documents.filter((d) =>
        (d.source ?? '').toLowerCase().includes(query.toLowerCase()),
      ),
    [documents, query],
  )

  const totalChunks = documents.reduce(
    (sum, d) => sum + (d.chunks ?? 0),
    0,
  )

  return (
    <section className="content-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">YOUR SECOND BRAIN</span>
          <h1>Knowledge</h1>
          <p>PDFs indexed in your Nerva backend.</p>
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <button className="filter-btn" type="button" onClick={onRefresh}>
            Refresh
          </button>
          <button className="primary-btn" type="button" onClick={onUpload}>
            <Plus size={16} />
            Add knowledge
          </button>
        </div>
      </div>

      <KnowledgeStats
        documentCount={documents.length}
        totalChunks={totalChunks}
        loading={loading}
        error={error}
      />

      <KnowledgeToolbar query={query} onQueryChange={setQuery} />

      <DocumentList documents={filtered} loading={loading} />
    </section>
  )
}
