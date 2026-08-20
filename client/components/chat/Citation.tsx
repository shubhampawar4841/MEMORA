import { ChevronRight, FileText, Network } from 'lucide-react'
import type { AskSource } from '@/lib/api'

type CitationProps = {
  source: AskSource
  onClick: (source: AskSource) => void
  onExplore?: (query: string) => void
}

function inferKind(source: AskSource): 'memory' | 'document' {
  if (source.folder === 'memory' || (source as { kind?: string }).kind === 'memory') {
    return 'memory'
  }
  if (source.page == null && source.chunk_index == null) return 'memory'
  return 'document'
}

export function Citation({ source, onClick, onExplore }: CitationProps) {
  const kind = inferKind(source)

  return (
    <div className="citation-wrap">
      <button
        type="button"
        className="citation"
        onClick={() => onClick(source)}
      >
        <FileText size={14} />
        <span>
          <strong>
            <span className={`kind-pill ${kind}`}>{kind}</span>{' '}
            {source.source ?? 'Unknown source'}
          </strong>
          <small>
            {kind === 'document' ? `Page ${source.page ?? '—'}` : 'Memory'}
            {source.rerank_score != null
              ? ` · score ${source.rerank_score.toFixed(3)}`
              : ''}
          </small>
        </span>
        <ChevronRight size={14} />
      </button>
      {onExplore && (source.text || source.source) ? (
        <button
          type="button"
          className="citation-explore"
          onClick={() =>
            onExplore((source.text || source.source || '').slice(0, 120))
          }
        >
          <Network size={12} />
          Explore related
        </button>
      ) : null}
    </div>
  )
}
