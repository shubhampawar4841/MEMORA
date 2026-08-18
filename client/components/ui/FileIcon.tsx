import { FileText } from 'lucide-react'

type FileIconProps = {
  color?: 'amber' | 'violet' | 'indigo' | 'mint'
  size?: number
}

export function FileIcon({ color = 'amber', size = 16 }: FileIconProps) {
  return (
    <div className={`file-icon ${color}`}>
      <FileText size={size} />
    </div>
  )
}
