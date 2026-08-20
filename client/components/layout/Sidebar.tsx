'use client'

import { useEffect, useState } from 'react'
import {
  Activity,
  LayoutDashboard,
  Library,
  MessageSquare,
  MoreHorizontal,
  Network,
  Plus,
  Search,
  Settings,
  Sparkles,
  Trash2,
  Upload,
  X,
} from 'lucide-react'
import {
  deleteConversation,
  listConversations,
  renameConversation,
  type ConversationSummary,
} from '@/lib/api'

type SidebarProps = {
  active: string
  onNavigate: (v: string) => void
  onUpload: () => void
  activeConversationId: string | null
  onSelectConversation: (id: string | null) => void
  refreshToken?: number
}

const RECENT_LIMIT = 5

const items = [
  { label: 'Overview', icon: LayoutDashboard, id: 'overview' },
  { label: 'Chat', icon: MessageSquare, id: 'chat' },
  { label: 'Memory', icon: Network, id: 'memory' },
  { label: 'Knowledge', icon: Library, id: 'knowledge' },
  { label: 'Search', icon: Search, id: 'search' },
]

function truncateTitle(title: string, max = 22) {
  const t = (title || 'Untitled').trim() || 'Untitled'
  return t.length > max ? `${t.slice(0, max - 1)}…` : t
}

export function Sidebar({
  active,
  onNavigate,
  onUpload,
  activeConversationId,
  onSelectConversation,
  refreshToken = 0,
}: SidebarProps) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])

  const refresh = () => {
    void listConversations()
      .then((res) => setConversations(res.conversations))
      .catch(() => setConversations([]))
  }

  useEffect(() => {
    refresh()
  }, [refreshToken])

  const recent = conversations.slice(0, RECENT_LIMIT)
  const extra = Math.max(0, conversations.length - RECENT_LIMIT)

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          <Sparkles size={17} />
        </div>
        <div>
          <strong>Nerva</strong>
          <span>Personal intelligence</span>
        </div>
        <button className="icon-btn mobile-close" type="button">
          <X size={16} />
        </button>
      </div>

      <button
        className="new-chat"
        type="button"
        onClick={() => {
          onSelectConversation(null)
          onNavigate('chat')
        }}
      >
        <Plus size={16} />
        New chat
        <kbd>⌘N</kbd>
      </button>

      <nav className="nav-group">
        <span className="eyebrow">Workspace</span>
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`nav-item ${active === item.id ? 'active' : ''}`}
            onClick={() => onNavigate(item.id)}
          >
            <item.icon size={17} />
            {item.label}
            {item.id === 'search' && <kbd>⌘K</kbd>}
          </button>
        ))}
      </nav>

      <nav className="nav-group chat-history">
        <div className="chat-history-head">
          <span className="eyebrow">Recent</span>
          {conversations.length > 0 && (
            <button
              type="button"
              className="chat-history-manage"
              onClick={() => onNavigate('chats')}
            >
              Manage
            </button>
          )}
        </div>

        {conversations.length === 0 && (
          <div className="nav-item muted" style={{ cursor: 'default' }}>
            No chats yet
          </div>
        )}

        {recent.map((c) => (
          <div
            key={c.id}
            className={`chat-row ${activeConversationId === c.id ? 'active' : ''}`}
          >
            <button
              type="button"
              className="chat-row-title"
              title={c.title || 'Untitled'}
              onClick={() => {
                onSelectConversation(c.id)
                onNavigate('chat')
              }}
            >
              {truncateTitle(c.title)}
            </button>
            <div className="chat-row-actions">
              <button
                type="button"
                className="icon-btn"
                title="Rename"
                onClick={() => {
                  const title = window.prompt('Rename conversation', c.title)
                  if (!title?.trim()) return
                  void renameConversation(c.id, title.trim()).then(refresh)
                }}
              >
                <MoreHorizontal size={13} />
              </button>
              <button
                type="button"
                className="icon-btn"
                title="Delete"
                onClick={() => {
                  if (!window.confirm('Delete this conversation?')) return
                  void deleteConversation(c.id).then(() => {
                    if (activeConversationId === c.id) onSelectConversation(null)
                    refresh()
                  })
                }}
              >
                <Trash2 size={13} />
              </button>
            </div>
          </div>
        ))}

        {extra > 0 && (
          <button
            type="button"
            className="chat-history-more"
            onClick={() => onNavigate('chats')}
          >
            +{extra} more — manage all
          </button>
        )}
      </nav>

      <nav className="nav-group">
        <span className="eyebrow">Sources</span>
        <button type="button" className="nav-item" onClick={onUpload}>
          <Upload size={17} />
          Add knowledge
        </button>
      </nav>

      <div className="sidebar-bottom">
        <button
          type="button"
          className={`nav-item ${active === 'activity' ? 'active' : ''}`}
          onClick={() => onNavigate('activity')}
        >
          <Activity size={17} />
          Activity
        </button>
        <button
          type="button"
          className={`nav-item ${active === 'settings' ? 'active' : ''}`}
          onClick={() => onNavigate('settings')}
        >
          <Settings size={17} />
          Settings
        </button>
        <div className="profile">
          <div className="avatar">SP</div>
          <div>
            <strong>Shubham</strong>
            <span>Personal workspace</span>
          </div>
        </div>
      </div>
    </aside>
  )
}
