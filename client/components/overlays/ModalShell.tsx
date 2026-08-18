import type { ReactNode } from 'react'
import { X } from 'lucide-react'
import { IconButton } from '@/components/ui/IconButton'

type ModalShellProps = {
  eyebrow: string
  title: string
  onClose: () => void
  children: ReactNode
}

export function ModalShell({
  eyebrow,
  title,
  onClose,
  children,
}: ModalShellProps) {
  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <span className="eyebrow">{eyebrow}</span>
            <h2>{title}</h2>
          </div>
          <IconButton onClick={onClose}>
            <X size={18} />
          </IconButton>
        </div>
        {children}
      </div>
    </div>
  )
}
