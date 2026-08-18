import { Sparkles } from 'lucide-react'
import type { AskSource } from '@/lib/api'
import { ModalShell } from '@/components/overlays/ModalShell'

type CitationModalProps = {
  citation: AskSource | null
  onClose: () => void
}

export function CitationModal({ citation, onClose }: CitationModalProps) {
  return (
    <ModalShell
      eyebrow="SOURCE PREVIEW"
      title={citation?.source ?? 'Source'}
      onClose={onClose}
    >
      <div className="preview-body">
        <div className="preview-meta">
          <span className="type-pill violet">PDF</span>
          <span>Page {citation?.page ?? '—'}</span>
        </div>

        <p>
          Source file: <strong>{citation?.source ?? 'Unknown'}</strong>
        </p>

        <p>
          Chunk index: {citation?.chunk_index ?? '—'}
          {citation?.rerank_score != null
            ? ` · rerank ${citation.rerank_score.toFixed(3)}`
            : ''}
          {citation?.distance != null
            ? ` · distance ${citation.distance.toFixed(4)}`
            : ''}
        </p>

        <div className="insight">
          <Sparkles size={15} />
          <span>
            <strong>Retrieved source</strong>
            This citation came from your Nerva /ask or document list response.
          </span>
        </div>
      </div>
    </ModalShell>
  )
}
