import { ArrowUp, BookOpen, FileCode2, Sparkles, Zap } from 'lucide-react'

const prompts = [
  'How should I structure a RAG evaluation?',
  'Scrape https://example.com and tell me the title',
  'Search the web for the latest Firecrawl documentation',
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
        Ask about your PDFs, or send me to the web to search, scrape, and extract.
        <br />
        I&apos;ll show tool progress and cite sources when answering from your knowledge base.
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
