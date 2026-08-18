'use client'

import { useState } from 'react'
import {
  askQuestion,
  type AskSource,
  type DocumentItem,
} from '@/lib/api'
import { ChatComposer } from '@/components/chat/ChatComposer'
import {
  ChatMessage,
  LoadingMessage,
  type ChatMessageData,
} from '@/components/chat/ChatMessage'
import { EmptyChat } from '@/components/chat/EmptyChat'

type ChatProps = {
  documents: DocumentItem[]
  onCitation: (source: AskSource) => void
}

export function Chat({ documents, onCitation }: ChatProps) {
  const [messages, setMessages] = useState<ChatMessageData[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  // null = search all documents
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(
    null,
  )

  const selectedDocument = documents.find(
    (doc) => doc.document_id === selectedDocumentId,
  )

  const send = async (text = input) => {
    const question = text.trim()
    if (!question || loading) return

    setMessages((m) => [...m, { role: 'user', text: question }])
    setInput('')
    setLoading(true)

    try {
      const response = await askQuestion(
        question,
        selectedDocumentId ?? undefined,
      )

      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          text: response.answer,
          sources: response.sources,
        },
      ])
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          text:
            err instanceof Error
              ? err.message
              : 'Failed to get an answer from the API.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="chat-page">
      {messages.length === 0 ? (
        <EmptyChat onPrompt={(p) => void send(p)} />
      ) : (
        <div className="messages">
          {messages.map((m, i) => (
            <ChatMessage
              key={`${m.role}-${i}`}
              message={m}
              onCitation={onCitation}
            />
          ))}
          {loading && <LoadingMessage />}
        </div>
      )}

      <ChatComposer
        input={input}
        loading={loading}
        documents={documents}
        selectedDocumentId={selectedDocumentId}
        selectedDocument={selectedDocument}
        onInputChange={setInput}
        onSend={() => void send()}
        onSelectDocument={setSelectedDocumentId}
      />
    </section>
  )
}
