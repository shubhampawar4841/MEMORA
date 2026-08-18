'use client'

import { MessageSquare, MoreHorizontal, RefreshCw, Search, Trash2 } from 'lucide-react'
import type { DocumentItem } from '@/lib/api'
import { FileIcon } from '@/components/ui/FileIcon'
import { IconButton } from '@/components/ui/IconButton'

type DocumentRowProps = {
  document: DocumentItem
  onChat: (document: DocumentItem) => void
  onSearch: (document: DocumentItem) => void
  onDelete: (document: DocumentItem) => void
  onReindex: (document: DocumentItem) => void
  onRename: (document: DocumentItem) => void
  busy?: boolean
}

export function DocumentRow({
  document,
  onChat,
  onSearch,
  onDelete,
  onReindex,
  onRename,
  busy,
}: DocumentRowProps) {
  return (
    <div className="source-row">
      <div className="source-name">
        <FileIcon color="amber" />
        <div>
          <strong>{document.source ?? 'Untitled PDF'}</strong>
          <small>
            {document.pages?.length ?? 0}
            {' pages · '}
            {document.chunks}
            {' chunks · '}
            {document.document_id.slice(0, 8)}
          </small>
        </div>
      </div>

      <span className="type-pill amber">PDF</span>
      <span className="updated">{document.chunks} chunks</span>

      <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
        <IconButton title="Chat with this PDF" onClick={() => onChat(document)} disabled={busy}>
          <MessageSquare size={15} />
        </IconButton>
        <IconButton title="Search this PDF" onClick={() => onSearch(document)} disabled={busy}>
          <Search size={15} />
        </IconButton>
        <IconButton title="Rename" onClick={() => onRename(document)} disabled={busy}>
          <MoreHorizontal size={15} />
        </IconButton>
        <IconButton title="Re-index" onClick={() => onReindex(document)} disabled={busy}>
          <RefreshCw size={15} />
        </IconButton>
        <IconButton title="Delete" onClick={() => onDelete(document)} disabled={busy}>
          <Trash2 size={15} />
        </IconButton>
      </div>
    </div>
  )
}
