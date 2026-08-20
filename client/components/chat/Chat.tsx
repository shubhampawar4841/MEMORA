'use client'

import { useEffect, useState } from 'react'
import {
  agentChatStream,
  createConversation,
  getConversation,
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

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

type ChatProps = {
  documents: DocumentItem[]
  onCitation: (source: AskSource) => void
  conversationId: string | null
  initialDocumentId?: string | null
  onConversationCreated?: (id: string) => void
  onConversationUpdated?: () => void
}

export function Chat({
  documents,
  onCitation,
  conversationId,
  initialDocumentId = null,
  onConversationCreated,
  onConversationUpdated,
}: ChatProps) {
  const [messages, setMessages] = useState<ChatMessageData[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [statusText, setStatusText] = useState<string | null>(null)
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(
    initialDocumentId,
  )
  const [activeConversationId, setActiveConversationId] = useState<string | null>(
    conversationId,
  )

  useEffect(() => {
    setActiveConversationId(conversationId)
    setSelectedDocumentId(initialDocumentId)

    if (!conversationId) {
      setMessages([])
      return
    }

    void getConversation(conversationId)
      .then((detail) => {
        setSelectedDocumentId(detail.document_id)
        setMessages(
          detail.messages.map((m) => ({
            role: m.role as 'user' | 'assistant',
            text: m.content,
            sources: m.sources,
          })),
        )
      })
      .catch(() => setMessages([]))
  }, [conversationId, initialDocumentId])

  const selectedDocument = documents.find(
    (doc) => doc.document_id === selectedDocumentId,
  )

  const send = async (text = input) => {
    const question = text.trim()
    if (!question || loading) return

    setMessages((m) => [...m, { role: 'user', text: question }])
    setInput('')
    setLoading(true)
    setStatusText('Thinking…')

    try {
      let convoId = activeConversationId
      if (!convoId) {
        const created = await createConversation({
          document_id: selectedDocumentId,
        })
        convoId = created.id
        setActiveConversationId(convoId)
        onConversationCreated?.(convoId)
      }

      const statuses: string[] = []
      setMessages((m) => [...m, { role: 'assistant', text: '' }])

      const result = await agentChatStream(question, {
        documentId: selectedDocumentId,
        conversationId: convoId,
        onStatus: (status) => {
          statuses.push(status)
          setStatusText(status)
          const preview =
            statuses.length > 0
              ? statuses.map((s) => `• ${s}`).join('\n')
              : status
          setMessages((m) => {
            const next = [...m]
            const last = next[next.length - 1]
            if (last?.role === 'assistant') {
              next[next.length - 1] = { ...last, text: preview }
            }
            return next
          })
        },
      })

      const answer = result.message || 'No response.'
      setMessages((m) => {
        const next = [...m]
        const last = next[next.length - 1]
        if (last?.role === 'assistant') {
          next[next.length - 1] = {
            role: 'assistant',
            text: answer,
            sources: result.sources,
          }
        }
        return next
      })

      await fetch(`${API_URL}/conversations/${convoId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_content: question,
          assistant_content: answer,
          sources: result.sources ?? [],
        }),
      })

      onConversationUpdated?.()
    } catch (err) {
      setMessages((m) => [
        ...m.filter((msg) => !(msg.role === 'assistant' && msg.text === '')),
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
      setStatusText(null)
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
          {loading && messages[messages.length - 1]?.role !== 'assistant' && (
            <LoadingMessage text={statusText ?? 'Working…'} />
          )}
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
