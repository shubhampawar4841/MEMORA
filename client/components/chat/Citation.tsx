import { ChevronRight, FileText } from 'lucide-react'
import type { AskSource } from '@/lib/api'

type CitationProps = {
  source: AskSource
  onClick: (source: AskSource) => void
}

export function Citation({ source, onClick }: CitationProps) {
  return (
    <button
      type="button"
      className="citation"
      onClick={() => onClick(source)}
    >
      <FileText size={14} />
      <span>
        <strong>{source.source ?? 'Unknown source'}</strong>
        <small>
          Page {source.page ?? '—'}
          {source.rerank_score != null
            ? ` · score ${source.rerank_score.toFixed(3)}`
            : ''}
        </small>
      </span>
      <ChevronRight size={14} />
    </button>
  )
}
