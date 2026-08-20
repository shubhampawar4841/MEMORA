'use client'

import { useCallback, useEffect, useState } from 'react'
import { MessageSquare, Pencil, Trash2 } from 'lucide-react'
import {
  deleteConversation,
  listConversations,
  renameConversation,
  type ConversationSummary,
} from '@/lib/api'

type Props = {
  activeConversationId: string | null
  onOpenChat: (id: string) => void
  onClearedActive?: () => void
  refreshToken?: number
}

export function ChatsManager({
  activeConversationId,
  onOpenChat,
  onClearedActive,
  refreshToken = 0,
}: Props) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listConversations()
      setConversations(res.conversations)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chats')
      setConversations([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh, refreshToken])

  const run = async (id: string, fn: () => Promise<void>) => {
    setBusyId(id)
    try {
      await fn()
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action failed')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section className="content-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">WORKSPACE</span>
          <h1>Chats</h1>
          <p>Manage all conversations. Sidebar shows only the 5 most recent.</p>
        </div>
      </div>

      {error ? (
        <p style={{ color: '#f87171', marginBottom: 12 }}>{error}</p>
      ) : null}

      {loading ? (
        <p style={{ color: '#737b94' }}>Loading…</p>
      ) : conversations.length === 0 ? (
        <div className="empty-panel">
          <MessageSquare size={21} />
          <h2>No conversations yet</h2>
          <p>Start a new chat from the sidebar.</p>
        </div>
      ) : (
        <div className="chats-manage-list">
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`chats-manage-row ${
                activeConversationId === c.id ? 'active' : ''
              }`}
            >
              <button
                type="button"
                className="chats-manage-open"
                onClick={() => onOpenChat(c.id)}
              >
                <strong>{c.title || 'Untitled'}</strong>
                <span>{c.id.slice(0, 8)}…</span>
              </button>
              <div className="row-actions">
                <button
                  type="button"
                  className="filter-btn"
                  disabled={busyId === c.id}
                  onClick={() =>
                    void run(c.id, async () => {
                      const title = window.prompt(
                        'Rename conversation',
                        c.title,
                      )
                      if (!title?.trim()) return
                      await renameConversation(c.id, title.trim())
                    })
                  }
                >
                  <Pencil size={14} />
                  Rename
                </button>
                <button
                  type="button"
                  className="filter-btn"
                  disabled={busyId === c.id}
                  onClick={() =>
                    void run(c.id, async () => {
                      if (!window.confirm(`Delete “${c.title || 'Untitled'}”?`)) {
                        return
                      }
                      await deleteConversation(c.id)
                      if (activeConversationId === c.id) onClearedActive?.()
                    })
                  }
                >
                  <Trash2 size={14} />
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
