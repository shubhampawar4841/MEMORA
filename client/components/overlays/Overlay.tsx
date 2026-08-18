import type { AskSource } from '@/lib/api'
import { CitationModal } from '@/components/overlays/CitationModal'
import { SearchModal } from '@/components/overlays/SearchModal'
import { UploadModal } from '@/components/overlays/UploadModal'

export type OverlayType = 'upload' | 'search' | 'citation'

type OverlayProps = {
  type: OverlayType
  onClose: () => void
  onUploaded: () => void
  citation: AskSource | null
  searchDocumentId?: string | null
  searchDocumentLabel?: string | null
}

export function Overlay({
  type,
  onClose,
  onUploaded,
  citation,
  searchDocumentId = null,
  searchDocumentLabel = null,
}: OverlayProps) {
  if (type === 'upload') {
    return <UploadModal onClose={onClose} onUploaded={onUploaded} />
  }

  if (type === 'search') {
    return (
      <SearchModal
        onClose={onClose}
        documentId={searchDocumentId}
        documentLabel={searchDocumentLabel}
      />
    )
  }

  return <CitationModal citation={citation} onClose={onClose} />
}
