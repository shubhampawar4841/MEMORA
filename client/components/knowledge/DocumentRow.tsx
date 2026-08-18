import { MoreHorizontal } from 'lucide-react'
import type { DocumentItem } from '@/lib/api'
import { FileIcon } from '@/components/ui/FileIcon'
import { IconButton } from '@/components/ui/IconButton'

type DocumentRowProps = {
  document: DocumentItem
}

export function DocumentRow({ document }: DocumentRowProps) {
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

      <IconButton>
        <MoreHorizontal size={16} />
      </IconButton>
    </div>
  )
}
