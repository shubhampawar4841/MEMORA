import type { DocumentItem } from '@/lib/api'

type DocumentSelectorProps = {
  documents: DocumentItem[]
  selectedDocumentId: string | null
  onChange: (documentId: string | null) => void
  disabled?: boolean
}

export function DocumentSelector({
  documents,
  selectedDocumentId,
  onChange,
  disabled,
}: DocumentSelectorProps) {
  return (
    <select
      value={selectedDocumentId ?? ''}
      onChange={(e) => {
        const value = e.target.value
        onChange(value || null)
      }}
      disabled={disabled}
      aria-label="Select document to search"
    >
      <option value="">Search all documents</option>
      {documents.map((doc) => (
        <option key={doc.document_id} value={doc.document_id}>
          {doc.source}
        </option>
      ))}
    </select>
  )
}
