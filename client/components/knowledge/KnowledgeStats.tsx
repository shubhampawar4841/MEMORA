import { StatusBadge } from '@/components/ui/StatusBadge'

type KnowledgeStatsProps = {
  documentCount: number
  totalChunks: number
  loading: boolean
  error: string | null
}

export function KnowledgeStats({
  documentCount,
  totalChunks,
  loading,
  error,
}: KnowledgeStatsProps) {
  return (
    <div className="stats">
      <div>
        <span>Indexed sources</span>
        <strong>{documentCount}</strong>
        <small>From /documents</small>
      </div>

      <div>
        <span>Knowledge chunks</span>
        <strong>{totalChunks}</strong>
        <small>Across all documents</small>
      </div>

      <div>
        <span>Status</span>
        <strong>{loading ? '…' : error ? 'Error' : 'Ready'}</strong>
        <StatusBadge label={error ?? 'Synced with API'} />
      </div>
    </div>
  )
}
