import type { ReactNode } from 'react'

type IconButtonProps = {
  children: ReactNode
  onClick?: () => void
  className?: string
  type?: 'button' | 'submit'
  title?: string
  disabled?: boolean
}

export function IconButton({
  children,
  onClick,
  className = '',
  type = 'button',
  title,
  disabled,
}: IconButtonProps) {
  return (
    <button
      className={`icon-btn ${className}`.trim()}
      type={type}
      onClick={onClick}
      title={title}
      disabled={disabled}
    >
      {children}
    </button>
  )
}
