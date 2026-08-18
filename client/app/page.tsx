'use client'

import { useCallback, useEffect, useState } from 'react'
import { Sparkles } from 'lucide-react'
import {
  getHome,
  listDocuments,
  type AskSource,
  type DocumentItem,
} from '@/lib/api'
import { Chat } from '@/components/chat/Chat'
import { Knowledge } from '@/components/knowledge/Knowledge'
import { Sidebar } from '@/components/layout/Sidebar'
import { Topbar } from '@/components/layout/Topbar'
import { Overview } from '@/components/overview/Overview'
import { Overlay, type OverlayType } from '@/components/overlays/Overlay'

export default function Page() {
  const [active, setActive] = useState('overview')
  const [modal, setModal] = useState<OverlayType | null>(null)
  const [mobile, setMobile] = useState(false)
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [docsLoading, setDocsLoading] = useState(true)
  const [docsError, setDocsError] = useState<string | null>(null)
  const [apiOk, setApiOk] = useState<boolean | null>(null)
  const [apiMessage, setApiMessage] = useState<string | null>(null)
  const [citation, setCitation] = useState<AskSource | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [chatDocumentId, setChatDocumentId] = useState<string | null>(null)
  const [searchDocumentId, setSearchDocumentId] = useState<string | null>(null)
  const [searchDocumentLabel, setSearchDocumentLabel] = useState<string | null>(null)
  const [conversationRefresh, setConversationRefresh] = useState(0)

  const refreshDocuments = useCallback(async () => {
    setDocsLoading(true)
    setDocsError(null)

    try {
      const res = await listDocuments()
      setDocuments(res.documents)
    } catch (err) {
      setDocsError(
        err instanceof Error ? err.message : 'Failed to load documents',
      )
      setDocuments([])
    } finally {
      setDocsLoading(false)
    }
  }, [])

  useEffect(() => {
    void getHome()
      .then((res) => {
        setApiOk(true)
        setApiMessage(res.message)
      })
      .catch(() => {
        setApiOk(false)
        setApiMessage('Backend unreachable at localhost:8000')
      })

    void refreshDocuments()
  }, [refreshDocuments])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setSearchDocumentId(null)
        setSearchDocumentLabel(null)
        setModal('search')
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'n') {
        e.preventDefault()
        setConversationId(null)
        setChatDocumentId(null)
        setActive('chat')
      }
    }

    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const navigate = (v: string) => {
    if (v === 'search') {
      setSearchDocumentId(null)
      setSearchDocumentLabel(null)
      setModal('search')
      setMobile(false)
      return
    }

    setActive(v)
    setMobile(false)
  }

  const openCitation = (source: AskSource) => {
    setCitation(source)
    setModal('citation')
  }

  const sidebarProps = {
    active,
    onNavigate: navigate,
    onUpload: () => setModal('upload'),
    activeConversationId: conversationId,
    onSelectConversation: (id: string | null) => {
      setConversationId(id)
      setChatDocumentId(null)
    },
    refreshToken: conversationRefresh,
  }

  return (
    <main className="app-shell">
      <Sidebar {...sidebarProps} />

      <div className="main-column">
        <Topbar
          active={active}
          onMenu={() => setMobile(!mobile)}
          onSearch={() => {
            setSearchDocumentId(null)
            setSearchDocumentLabel(null)
            setModal('search')
          }}
          apiOk={apiOk}
        />

        {mobile && (
          <div className="mobile-sidebar">
            <Sidebar {...sidebarProps} />
          </div>
        )}

        <div className="page-content">
          {active === 'overview' && (
            <Overview
              documents={documents}
              apiOk={apiOk}
              apiMessage={apiMessage}
              onNavigate={navigate}
              onCitation={openCitation}
            />
          )}

          {active === 'chat' && (
            <Chat
              documents={documents}
              onCitation={openCitation}
              conversationId={conversationId}
              initialDocumentId={chatDocumentId}
              onConversationCreated={(id) => {
                setConversationId(id)
                setConversationRefresh((n) => n + 1)
              }}
              onConversationUpdated={() => setConversationRefresh((n) => n + 1)}
            />
          )}

          {active === 'knowledge' && (
            <Knowledge
              documents={documents}
              loading={docsLoading}
              error={docsError}
              onUpload={() => setModal('upload')}
              onRefresh={() => void refreshDocuments()}
              onChatDocument={(doc) => {
                setConversationId(null)
                setChatDocumentId(doc.document_id)
                setActive('chat')
              }}
              onSearchDocument={(doc) => {
                setSearchDocumentId(doc.document_id)
                setSearchDocumentLabel(doc.source)
                setModal('search')
              }}
            />
          )}

          {active !== 'overview' &&
            active !== 'chat' &&
            active !== 'knowledge' && (
              <div className="content-page">
                <div className="page-heading">
                  <div>
                    <span className="eyebrow">WORKSPACE</span>
                    <h1>{active[0].toUpperCase() + active.slice(1)}</h1>
                    <p>This area is ready for your knowledge workflow.</p>
                  </div>
                </div>
                <div className="empty-panel">
                  <Sparkles size={21} />
                  <h2>Coming together in your vault</h2>
                  <p>Use the sidebar to return to chat or knowledge sources.</p>
                </div>
              </div>
            )}
        </div>
      </div>

      {modal && (
        <Overlay
          type={modal}
          onClose={() => setModal(null)}
          onUploaded={() => void refreshDocuments()}
          citation={citation}
          searchDocumentId={searchDocumentId}
          searchDocumentLabel={searchDocumentLabel}
        />
      )}
    </main>
  )
}
