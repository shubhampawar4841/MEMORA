'use client'

import { useEffect, useState } from 'react'
import {
  Activity,
  Folder,
  LayoutDashboard,
  Library,
  MessageSquare,
  MoreHorizontal,
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

const items = [
  { label: 'Overview', icon: LayoutDashboard, id: 'overview' },
  { label: 'Chat', icon: MessageSquare, id: 'chat' },
  { label: 'Knowledge', icon: Library, id: 'knowledge' },
  { label: 'Collections', icon: Folder, id: 'collections' },
]

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
        New conversation
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
            {item.id === 'chat' && <span className="online-dot" />}
          </button>
        ))}
      </nav>

      <nav className="nav-group">
        <span className="eyebrow">Conversations</span>
        {conversations.length === 0 && (
          <div className="nav-item" style={{ cursor: 'default' }}>
            No chats yet
          </div>
        )}
        {conversations.slice(0, 8).map((c) => (
          <div
            key={c.id}
            className={`nav-item ${activeConversationId === c.id ? 'active' : ''}`}
            style={{ justifyContent: 'space-between' }}
          >
            <button
              type="button"
              style={{
                background: 'transparent',
                border: 0,
                color: 'inherit',
                textAlign: 'left',
                flex: 1,
                padding: 0,
              }}
              onClick={() => {
                onSelectConversation(c.id)
                onNavigate('chat')
              }}
            >
              {c.title || 'Untitled'}
            </button>
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
              <MoreHorizontal size={14} />
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
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </nav>

      <nav className="nav-group">
        <span className="eyebrow">Sources</span>
        <button
          type="button"
          className={`nav-item ${active === 'search' ? 'active' : ''}`}
          onClick={() => onNavigate('search')}
        >
          <Search size={17} />
          Search
          <kbd>⌘K</kbd>
        </button>
        <button type="button" className="nav-item" onClick={onUpload}>
          <Upload size={17} />
          Add knowledge
        </button>
      </nav>

      <div className="sidebar-bottom">
        <button
          type="button"
          className="nav-item"
          onClick={() => onNavigate('activity')}
        >
          <Activity size={17} />
          Activity
        </button>
        <button
          type="button"
          className="nav-item"
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
          <MoreHorizontal size={17} />
        </div>
      </div>
    </aside>
  )
}
