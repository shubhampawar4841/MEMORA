import { Check, ChevronRight } from 'lucide-react'
import type { AskSource, DocumentItem } from '@/lib/api'
import { FileIcon } from '@/components/ui/FileIcon'

type RecentDocumentsProps = {
  documents: DocumentItem[]
  onNavigate: (v: string) => void
  onCitation: (source: AskSource) => void
}

export function RecentDocuments({
  documents,
  onNavigate,
  onCitation,
}: RecentDocumentsProps) {
  return (
    <>
      <div className="recent-head">
        <h2>Recently indexed</h2>
        <button type="button" onClick={() => onNavigate('knowledge')}>
          View all
          <ChevronRight size={14} />
        </button>
      </div>

      <div className="recent-list">
        {documents.length === 0 && (
          <button
            className="recent-item"
            type="button"
            onClick={() => onNavigate('knowledge')}
          >
            <FileIcon color="violet" />
            <div>
              <strong>No PDFs yet</strong>
              <span>Upload from Knowledge to index content</span>
            </div>
          </button>
        )}

        {documents.slice(0, 4).map((doc) => (
          <button
            key={doc.document_id}
            className="recent-item"
            type="button"
            onClick={() =>
              onCitation({
                source: doc.source,
                page: doc.pages?.[0] ?? null,
                chunk_index: null,
                distance: 0,
                rerank_score: 0,
              })
            }
          >
            <FileIcon color="amber" />
            <div>
              <strong>{doc.source ?? 'Untitled PDF'}</strong>
              <span>
                PDF · {doc.chunks}
                {' chunks · '}
                {doc.pages?.length ?? 0}
                {' pages'}
              </span>
            </div>
            <Check size={15} />
          </button>
        ))}
      </div>
    </>
  )
}
