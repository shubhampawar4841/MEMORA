import { ArrowUp, BookOpen, FileCode2, Sparkles, Zap } from 'lucide-react'

const prompts = [
  'How should I structure a RAG evaluation?',
  'Find the latest notes on Raava',
  'Summarize my TypeScript patterns',
]

type EmptyChatProps = {
  onPrompt: (p: string) => void
}

export function EmptyChat({ onPrompt }: EmptyChatProps) {
  return (
    <div className="empty-chat">
      <div className="hero-orbit">
        <div className="orbit-ring ring-one" />
        <div className="orbit-ring ring-two" />
        <div className="core">
          <Sparkles size={22} />
        </div>
      </div>

      <h1>What&apos;s on your mind?</h1>

      <p>
        Ask anything about your uploaded PDFs.
        <br />
        I&apos;ll search your indexed knowledge and answer with sources.
      </p>

      <div className="prompt-list">
        {prompts.map((p, i) => (
          <button key={p} type="button" onClick={() => onPrompt(p)}>
            <span>
              {i === 0 ? (
                <Zap size={15} />
              ) : i === 1 ? (
                <BookOpen size={15} />
              ) : (
                <FileCode2 size={15} />
              )}
            </span>
            {p}
            <ArrowUp size={14} />
          </button>
        ))}
      </div>
    </div>
  )
}
