'use client'

import { useEffect, useState } from 'react'
import {
  ArrowUp,
  ChevronDown,
  Link2,
  MessageSquare,
  Network,
  Sparkles,
} from 'lucide-react'
import type { AskSource, DocumentItem } from '@/lib/api'
import {
  getMemoryActivity,
  getMemoryProfile,
  listConnections,
} from '@/lib/api'
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
  const [containerTag, setContainerTag] = useState<string | null>(null)
  const [factCount, setFactCount] = useState(0)
  const [connectors, setConnectors] = useState<string[]>([])
  const [activityPreview, setActivityPreview] = useState<
    { title: string; status: string }[]
  >([])

  useEffect(() => {
    void getMemoryProfile()
      .then((p) => {
        setContainerTag(p.container_tag)
        setFactCount((p.static?.length || 0) + (p.dynamic?.length || 0))
      })
      .catch(() => undefined)
    void listConnections()
      .then((c) => {
        setConnectors(
          (c.connections || [])
            .map((x) => String(x.provider || ''))
            .filter(Boolean),
        )
        if (c.container_tag) setContainerTag(c.container_tag)
      })
      .catch(() => undefined)
    void getMemoryActivity(undefined, 3)
      .then((a) => {
        setActivityPreview(
          (a.items || []).slice(0, 3).map((i) => ({
            title: i.title,
            status: i.status,
          })),
        )
      })
      .catch(() => undefined)
  }, [])

  const connectorLabel =
    connectors.length === 0
      ? 'None connected'
      : [...new Set(connectors)].join(', ')

  return (
    <section className="content-page overview">
      <div className="page-heading">
        <div>
          <span className="eyebrow">NERVA</span>
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
            <span className="eyebrow">ASK YOUR MEMORY</span>
            <MessageSquare size={17} />
          </div>
          <h2>Chat across docs, mail, and facts</h2>
          <p>
            Same container
            {containerTag ? (
              <>
                {' '}
                <code className="inline-code">{containerTag}</code>
              </>
            ) : null}
          </p>
          <div className="card-link">
            Start conversation
            <ArrowUp size={14} />
          </div>
        </div>

        <button
          type="button"
          className="metric-card overview-click"
          onClick={() => onNavigate('memory')}
        >
          <div className="metric-icon violet">
            <Network size={17} />
          </div>
          <span>Memory facts</span>
          <strong>{factCount}</strong>
          <small>Explore graph</small>
        </button>

        <button
          type="button"
          className="metric-card overview-click"
          onClick={() => onNavigate('knowledge')}
        >
          <div className="metric-icon amber">
            <Link2 size={17} />
          </div>
          <span>Connectors</span>
          <strong style={{ fontSize: 16, marginTop: 10 }}>{connectorLabel}</strong>
          <small>{documents.length} documents indexed</small>
        </button>
      </div>

      <div className="overview-actions">
        <button className="primary-btn" type="button" onClick={() => onNavigate('chat')}>
          <MessageSquare size={16} />
          Ask Chat
        </button>
        <button className="filter-btn" type="button" onClick={() => onNavigate('memory')}>
          <Sparkles size={16} />
          Explore Memory
        </button>
        <button className="filter-btn" type="button" onClick={() => onNavigate('search')}>
          Search
        </button>
      </div>

      {activityPreview.length > 0 && (
        <div className="overview-activity">
          <div className="recent-head">
            <h2>Latest activity</h2>
            <button type="button" onClick={() => onNavigate('activity')}>
              View all
            </button>
          </div>
          <ul className="activity-list compact">
            {activityPreview.map((a, i) => (
              <li key={`${a.title}-${i}`}>
                <div className="activity-row static">
                  <span className="activity-body">
                    <strong>{a.title}</strong>
                    <span>{a.status}</span>
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <RecentDocuments
        documents={documents}
        onNavigate={onNavigate}
        onCitation={onCitation}
      />
    </section>
  )
}
