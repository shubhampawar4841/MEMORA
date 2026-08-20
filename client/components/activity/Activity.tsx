'use client'

import { useCallback, useEffect, useState } from 'react'
import { Activity as ActivityIcon, Link2, FileText } from 'lucide-react'
import {
  getMemoryActivity,
  type MemoryActivityItem,
} from '@/lib/api'

type Props = {
  onOpenKnowledge?: () => void
  onExploreMemory?: (query: string) => void
}

export function Activity({ onOpenKnowledge, onExploreMemory }: Props) {
  const [items, setItems] = useState<MemoryActivityItem[]>([])
  const [containerTag, setContainerTag] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getMemoryActivity(undefined, 40)
      setItems(res.items || [])
      setContainerTag(res.container_tag || null)
      if (res.error && !res.ok) setError(res.error)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load activity')
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return (
    <section className="content-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">TIMELINE</span>
          <h1>Activity</h1>
          <p>
            Recent documents and connectors
            {containerTag ? (
              <>
                {' '}for <code className="inline-code">{containerTag}</code>
              </>
            ) : null}
            .
          </p>
        </div>
        <button className="filter-btn" type="button" onClick={() => void refresh()}>
          Refresh
        </button>
      </div>

      {error ? <p className="form-error">{error}</p> : null}

      {loading ? (
        <p className="muted">Loading…</p>
      ) : items.length === 0 ? (
        <div className="empty-panel">
          <ActivityIcon size={21} />
          <h2>No activity yet</h2>
          <p>Uploads and OAuth connectors will show up here.</p>
        </div>
      ) : (
        <ul className="activity-list">
          {items.map((item) => (
            <li key={`${item.type}-${item.id}`}>
              <button
                type="button"
                className="activity-row"
                onClick={() => {
                  if (item.type === 'connection') {
                    onOpenKnowledge?.()
                    return
                  }
                  onExploreMemory?.(item.title)
                }}
              >
                <span className="activity-icon">
                  {item.type === 'connection' ? (
                    <Link2 size={16} />
                  ) : (
                    <FileText size={16} />
                  )}
                </span>
                <span className="activity-body">
                  <strong>{item.title}</strong>
                  <span>
                    {item.type} · {item.status}
                    {item.provider ? ` · ${item.provider}` : ''}
                    {item.at ? ` · ${String(item.at).slice(0, 19)}` : ''}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
