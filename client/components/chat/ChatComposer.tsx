import { ArrowUp, Paperclip } from 'lucide-react'
import type { DocumentItem } from '@/lib/api'
import { DocumentSelector } from '@/components/chat/DocumentSelector'

type ChatComposerProps = {
  input: string
  loading: boolean
  documents: DocumentItem[]
  selectedDocumentId: string | null
  selectedDocument: DocumentItem | undefined
  onInputChange: (value: string) => void
  onSend: () => void
  onSelectDocument: (documentId: string | null) => void
}

export function ChatComposer({
  input,
  loading,
  documents,
  selectedDocumentId,
  selectedDocument,
  onInputChange,
  onSend,
  onSelectDocument,
}: ChatComposerProps) {
  return (
    <div className="composer-wrap">
      <div className="composer">
        <textarea
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => {
            if (
              e.key === 'Enter' &&
              !e.shiftKey &&
              !e.nativeEvent.isComposing
            ) {
              e.preventDefault()
              onSend()
            }
          }}
          placeholder="Ask Nerva anything..."
          rows={1}
          disabled={loading}
        />

        <div className="composer-footer">
          <div className="composer-tools">
            <button
              type="button"
              title="Search all documents"
              onClick={() => onSelectDocument(null)}
            >
              <Paperclip size={16} />
            </button>

            <DocumentSelector
              documents={documents}
              selectedDocumentId={selectedDocumentId}
              onChange={onSelectDocument}
              disabled={loading}
            />
          </div>

          <button
            className="send-btn"
            type="button"
            onClick={onSend}
            disabled={!input.trim() || loading}
          >
            <ArrowUp size={16} />
          </button>
        </div>
      </div>

      <div className="composer-note">
        {selectedDocument ? (
          <>
            Searching only <strong>{selectedDocument.source}</strong>
          </>
        ) : (
          'Searching across all indexed documents'
        )}
        {' · '}
        Nerva can make mistakes. Verify important information.
      </div>
    </div>
  )
}
