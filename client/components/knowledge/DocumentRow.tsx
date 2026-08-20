'use client'

import {
  FolderInput,
  MessageSquare,
  MoreHorizontal,
  RefreshCw,
  Search,
  Trash2,
} from 'lucide-react'
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
  onMoveFolder: (document: DocumentItem) => void
  busy?: boolean
}

function folderLabel(folder?: string) {
  const value = (folder || 'other').toLowerCase()
  return value.charAt(0).toUpperCase() + value.slice(1)
}

export function DocumentRow({
  document,
  onChat,
  onSearch,
  onDelete,
  onReindex,
  onRename,
  onMoveFolder,
  busy,
}: DocumentRowProps) {
  return (
    <div className="source-row">
      <div className="source-name">
        <FileIcon color="amber" />
        <div>
          <strong>{document.source ?? 'Untitled document'}</strong>
          <small>
            {document.pages?.length ?? 0}
            {' pages · '}
            {document.chunks}
            {' chunks · '}
            {document.document_id.slice(0, 8)}
          </small>
        </div>
      </div>

      <span className="type-pill amber">{folderLabel(document.folder)}</span>
      <span className="updated">{document.chunks} chunks</span>

      <div className="row-actions">
        <IconButton title="Chat with this document" onClick={() => onChat(document)} disabled={busy}>
          <MessageSquare size={15} />
        </IconButton>
        <IconButton title="Search this document" onClick={() => onSearch(document)} disabled={busy}>
          <Search size={15} />
        </IconButton>
        <IconButton title="Rename" onClick={() => onRename(document)} disabled={busy}>
          <MoreHorizontal size={15} />
        </IconButton>
        <IconButton
          title="Move folder"
          onClick={() => onMoveFolder(document)}
          disabled={busy}
        >
          <FolderInput size={15} />
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
