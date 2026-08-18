import type { ReactNode } from 'react'

type MetricCardProps = {
  icon: ReactNode
  iconClassName: string
  label: string
  value: number
  suffix: string
}

export function MetricCard({
  icon,
  iconClassName,
  label,
  value,
  suffix,
}: MetricCardProps) {
  return (
    <div className="metric-card">
      <div className={`metric-icon ${iconClassName}`}>{icon}</div>
      <span>{label}</span>
      <strong>
        {value}
        <small>{` ${suffix}`}</small>
      </strong>
    </div>
  )
}
