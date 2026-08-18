import { ChevronDown, Search } from 'lucide-react'

type KnowledgeToolbarProps = {
  query: string
  onQueryChange: (value: string) => void
}

export function KnowledgeToolbar({
  query,
  onQueryChange,
}: KnowledgeToolbarProps) {
  return (
    <div className="section-toolbar">
      <div className="field">
        <Search size={16} />
        <input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Filter your sources..."
        />
      </div>

      <button className="filter-btn" type="button">
        PDF
        <ChevronDown size={14} />
      </button>
    </div>
  )
}
