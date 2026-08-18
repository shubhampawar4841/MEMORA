import { ArrowUp, ChevronDown, Library, MessageSquare, Zap } from 'lucide-react'
import type { AskSource, DocumentItem } from '@/lib/api'
import { MetricCard } from '@/components/overview/MetricCard'
import { RecentDocuments } from '@/components/overview/RecentDocuments'

type OverviewProps = {
  documents: DocumentItem[]
  apiOk: boolean | null
  apiMessage: string | null
  onNavigate: (v: string) => void
  onCitation: (source: AskSource) => void
}

export function Overview({
  documents,
  apiOk,
  apiMessage,
  onNavigate,
  onCitation,
}: OverviewProps) {
  const totalChunks = documents.reduce((s, d) => s + d.chunks, 0)

  return (
    <section className="content-page overview">
      <div className="page-heading">
        <div>
          <span className="eyebrow">NERVA BACKEND</span>
          <h1>Good morning.</h1>
          <p>{apiMessage ?? 'Connecting to your API…'}</p>
        </div>

        <div className="health">
          <span className="pulse" />
          {apiOk == null ? 'Checking…' : apiOk ? 'API healthy' : 'API offline'}
          <ChevronDown size={14} />
        </div>
      </div>

      <div className="overview-grid">
        <div className="focus-card" onClick={() => onNavigate('chat')}>
          <div className="card-top">
            <span className="eyebrow">ASK YOUR DOCS</span>
            <MessageSquare size={17} />
          </div>
          <h2>Chat with your indexed PDFs</h2>
          <p>Uses POST /ask across all documents</p>
          <div className="card-link">
            Start conversation
            <ArrowUp size={14} />
          </div>
        </div>

        <MetricCard
          icon={<Library size={17} />}
          iconClassName="violet"
          label="Indexed PDFs"
          value={documents.length}
          suffix="documents"
        />

        <MetricCard
          icon={<Zap size={17} />}
          iconClassName="amber"
          label="Total chunks"
          value={totalChunks}
          suffix="embedded"
        />
      </div>

      <RecentDocuments
        documents={documents}
        onNavigate={onNavigate}
        onCitation={onCitation}
      />
    </section>
  )
}
