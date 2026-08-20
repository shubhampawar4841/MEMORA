import { Search } from 'lucide-react'
import { KNOWLEDGE_FOLDERS } from '@/lib/api'

type KnowledgeToolbarProps = {
  query: string
  onQueryChange: (value: string) => void
  folder: string
  onFolderChange: (value: string) => void
}

export function KnowledgeToolbar({
  query,
  onQueryChange,
  folder,
  onFolderChange,
}: KnowledgeToolbarProps) {
  return (
    <div className="section-toolbar knowledge-toolbar">
      <div className="field">
        <Search size={16} />
        <input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Filter by title..."
        />
      </div>

      <div className="folder-chips">
        <button
          className={`filter-btn${folder === 'all' ? ' active' : ''}`}
          type="button"
          onClick={() => onFolderChange('all')}
        >
          All
        </button>
        {KNOWLEDGE_FOLDERS.map((item) => (
          <button
            key={item}
            className={`filter-btn${folder === item ? ' active' : ''}`}
            type="button"
            onClick={() => onFolderChange(item)}
          >
            {item.charAt(0).toUpperCase() + item.slice(1)}
          </button>
        ))}
      </div>
    </div>
  )
}
