import type { DocumentItem } from '@/lib/api'
import { FileIcon } from '@/components/ui/FileIcon'
import { DocumentRow } from '@/components/knowledge/DocumentRow'

type DocumentListProps = {
  documents: DocumentItem[]
  loading: boolean
  busyId?: string | null
  onChat: (document: DocumentItem) => void
  onSearch: (document: DocumentItem) => void
  onDelete: (document: DocumentItem) => void
  onReindex: (document: DocumentItem) => void
  onRename: (document: DocumentItem) => void
}

export function DocumentList({
  documents,
  loading,
  busyId,
  onChat,
  onSearch,
  onDelete,
  onReindex,
  onRename,
}: DocumentListProps) {
  return (
    <div className="source-table">
      <div className="table-head">
        <span>Source</span>
        <span>Type</span>
        <span>Chunks</span>
        <span>Actions</span>
      </div>

      {loading && (
        <div className="source-row">
          <div className="source-name">
            <FileIcon color="amber" />
            <div>
              <strong>Loading documents…</strong>
              <small>Calling GET /documents</small>
            </div>
          </div>
        </div>
      )}

      {!loading && documents.length === 0 && (
        <div className="source-row">
          <div className="source-name">
            <FileIcon color="violet" />
            <div>
              <strong>No documents yet</strong>
              <small>Upload a PDF to get started</small>
            </div>
          </div>
        </div>
      )}

      {!loading &&
        documents.map((doc) => (
          <DocumentRow
            key={doc.document_id}
            document={doc}
            busy={busyId === doc.document_id}
            onChat={onChat}
            onSearch={onSearch}
            onDelete={onDelete}
            onReindex={onReindex}
            onRename={onRename}
          />
        ))}
    </div>
  )
}
