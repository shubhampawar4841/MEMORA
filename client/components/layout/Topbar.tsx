import { Bell, ChevronRight, Menu, Search } from 'lucide-react'

type TopbarProps = {
  active: string
  onMenu: () => void
  onSearch: () => void
  apiOk: boolean | null
}

export function Topbar({ active, onMenu, onSearch, apiOk }: TopbarProps) {
  return (
    <header className="topbar">
      <button className="icon-btn menu-btn" type="button" onClick={onMenu}>
        <Menu size={19} />
      </button>

      <div className="crumb">
        <span>Workspace</span>
        <ChevronRight size={14} />
        <strong>{active[0].toUpperCase() + active.slice(1)}</strong>
      </div>

      <div className="top-actions">
        <button className="search-pill" type="button" onClick={onSearch}>
          <Search size={15} />
          Search anything
          <kbd>⌘ K</kbd>
        </button>

        <button className="icon-btn" type="button">
          <Bell size={17} />
          {apiOk === false && <i />}
        </button>

        <div className="mini-avatar">SP</div>
      </div>
    </header>
  )
}
