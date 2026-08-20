import { Sparkles } from 'lucide-react'
import type { AskSource } from '@/lib/api'
import { Citation } from '@/components/chat/Citation'

export type ChatMessageData = {
  role: 'user' | 'assistant'
  text: string
  sources?: AskSource[]
}

type ChatMessageProps = {
  message: ChatMessageData
  onCitation: (source: AskSource) => void
}

export function ChatMessage({ message, onCitation }: ChatMessageProps) {
  return (
    <div className={`message ${message.role}`}>
      <div className="message-label">
        {message.role === 'user' ? (
          'You'
        ) : (
          <>
            <div className="tiny-mark">
              <Sparkles size={11} />
            </div>
            Nerva
          </>
        )}
      </div>

      <p style={{ whiteSpace: 'pre-wrap' }}>{message.text}</p>

      {message.role === 'assistant' &&
        message.sources?.map((source, si) => (
          <Citation
            key={`${source.source}-${source.page}-${si}`}
            source={source}
            onClick={onCitation}
          />
        ))}
    </div>
  )
}

type LoadingMessageProps = {
  text?: string
}

export function LoadingMessage({
  text = 'Searching your knowledge…',
}: LoadingMessageProps) {
  return (
    <div className="message assistant">
      <div className="message-label">
        <div className="tiny-mark">
          <Sparkles size={11} />
        </div>
        Nerva
      </div>
      <p>{text}</p>
    </div>
  )
}
