'use client'

import { useMemo, useState } from 'react'
import { Plus } from 'lucide-react'
import {
  deleteDocument,
  reindexDocument,
  renameDocument,
  type DocumentItem,
} from '@/lib/api'
import { DocumentList } from '@/components/knowledge/DocumentList'
import { KnowledgeStats } from '@/components/knowledge/KnowledgeStats'
import { KnowledgeToolbar } from '@/components/knowledge/KnowledgeToolbar'

type KnowledgeProps = {
  documents: DocumentItem[]
  loading: boolean
  error: string | null
  onUpload: () => void
  onRefresh: () => void
  onChatDocument: (document: DocumentItem) => void
  onSearchDocument: (document: DocumentItem) => void
}

export function Knowledge({
  documents,
  loading,
  error,
  onUpload,
  onRefresh,
  onChatDocument,
  onSearchDocument,
}: KnowledgeProps) {
  const [query, setQuery] = useState('')
  const [busyId, setBusyId] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

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

  const run = async (documentId: string, fn: () => Promise<void>) => {
    setBusyId(documentId)
    setActionError(null)
    try {
      await fn()
      onRefresh()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Action failed')
    } finally {
      setBusyId(null)
    }
  }

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
        error={error ?? actionError}
      />

      <KnowledgeToolbar query={query} onQueryChange={setQuery} />

      <DocumentList
        documents={filtered}
        loading={loading}
        busyId={busyId}
        onChat={onChatDocument}
        onSearch={onSearchDocument}
        onDelete={(doc) =>
          void run(doc.document_id, async () => {
            if (!window.confirm(`Delete ${doc.source}?`)) return
            await deleteDocument(doc.document_id)
          })
        }
        onReindex={(doc) =>
          void run(doc.document_id, async () => {
            const res = await reindexDocument(doc.document_id)
            if (res.error) throw new Error(res.error)
          })
        }
        onRename={(doc) =>
          void run(doc.document_id, async () => {
            const next = window.prompt('Rename document', doc.source ?? '')
            if (!next?.trim()) return
            await renameDocument(doc.document_id, next.trim())
          })
        }
      />
    </section>
  )
}
