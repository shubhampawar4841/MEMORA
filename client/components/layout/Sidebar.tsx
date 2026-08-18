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
  Upload,
  X,
} from 'lucide-react'

type SidebarProps = {
  active: string
  onNavigate: (v: string) => void
  onUpload: () => void
}

const items = [
  { label: 'Overview', icon: LayoutDashboard, id: 'overview' },
  { label: 'Chat', icon: MessageSquare, id: 'chat' },
  { label: 'Knowledge', icon: Library, id: 'knowledge' },
  { label: 'Collections', icon: Folder, id: 'collections' },
]

export function Sidebar({ active, onNavigate, onUpload }: SidebarProps) {
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
        onClick={() => onNavigate('chat')}
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
