import { Check } from 'lucide-react'

type StatusBadgeProps = {
  label: string
}

export function StatusBadge({ label }: StatusBadgeProps) {
  return (
    <small className="status">
      <Check size={13} />
      {label}
    </small>
  )
}
