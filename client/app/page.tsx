'use client'

import { useCallback, useEffect, useState } from 'react'
import {
  getHome,
  listDocuments,
  type AskSource,
  type DocumentItem,
} from '@/lib/api'
import { Activity } from '@/components/activity/Activity'
import { Call } from '@/components/call/Call'
import { Chat } from '@/components/chat/Chat'
import { ChatsManager } from '@/components/chats/ChatsManager'
import { Knowledge } from '@/components/knowledge/Knowledge'
import { Sidebar } from '@/components/layout/Sidebar'
import { Topbar } from '@/components/layout/Topbar'
import { Memory } from '@/components/memory/Memory'
import { Overview } from '@/components/overview/Overview'
import { Overlay, type OverlayType } from '@/components/overlays/Overlay'
import { SearchPage } from '@/components/search/SearchPage'
import { Settings } from '@/components/settings/Settings'

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
  const [chatSeed, setChatSeed] = useState<string | null>(null)
  const [searchDocumentId, setSearchDocumentId] = useState<string | null>(null)
  const [searchDocumentLabel, setSearchDocumentLabel] = useState<string | null>(null)
  const [conversationRefresh, setConversationRefresh] = useState(0)
  const [memoryQuery, setMemoryQuery] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState<string | null>(null)

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
        setApiMessage(
          `Backend unreachable at ${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}`,
        )
      })

    void refreshDocuments()
  }, [refreshDocuments])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    if (params.get('integrations') !== 'connected') return
    const provider = params.get('provider') || 'integration'
    setActive('knowledge')
    setApiMessage(
      `${provider} connected via Supermemory. Sync may take a few minutes — then ask in Chat.`,
    )
    setApiOk(true)
    window.history.replaceState({}, '', window.location.pathname)
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    if (params.get('google') === 'connected') {
      const email = params.get('email')
      setActive('settings')
      setApiMessage(
        email
          ? `Google connected as ${email}. Gmail and Calendar access is stored on the backend.`
          : 'Google connected. Gmail and Calendar access is stored on the backend.',
      )
      setApiOk(true)
      window.history.replaceState({}, '', window.location.pathname)
      return
    }
    if (params.get('google') === 'error') {
      const message = params.get('message') || 'Google sign-in failed.'
      setActive('settings')
      setApiMessage(message)
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  const navigate = useCallback((v: string) => {
    setActive(v)
    setMobile(false)
  }, [])

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
        setChatSeed(null)
        setActive('chat')
      }
    }

    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const openCitation = (source: AskSource) => {
    setCitation(source)
    setModal('citation')
  }

  const openMemory = (q: string) => {
    setMemoryQuery(q)
    setActive('memory')
    setMobile(false)
  }

  const openSearchPage = (q?: string) => {
    setSearchQuery(q || null)
    setActive('search')
    setMobile(false)
    setModal(null)
  }

  const openChatWith = (q: string, documentId?: string | null) => {
    setConversationId(null)
    setChatDocumentId(documentId ?? null)
    setChatSeed(q)
    setActive('chat')
    setMobile(false)
  }

  const sidebarProps = {
    active,
    onNavigate: (v: string) => {
      if (v === 'search') {
        openSearchPage()
        return
      }
      navigate(v)
    },
    onUpload: () => setModal('upload'),
    activeConversationId: conversationId,
    onSelectConversation: (id: string | null) => {
      setConversationId(id)
      setChatDocumentId(null)
      setChatSeed(null)
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
              onNavigate={(v) => {
                if (v === 'search') openSearchPage()
                else navigate(v)
              }}
              onCitation={openCitation}
            />
          )}

          {active === 'chat' && (
            <Chat
              documents={documents}
              onCitation={openCitation}
              conversationId={conversationId}
              initialDocumentId={chatDocumentId}
              initialPrompt={chatSeed}
              onExploreMemory={openMemory}
              onConversationCreated={(id) => {
                setConversationId(id)
                setConversationRefresh((n) => n + 1)
              }}
              onConversationUpdated={() => setConversationRefresh((n) => n + 1)}
            />
          )}

          {active === 'call' && <Call />}

          {active === 'memory' && (
            <Memory
              initialQuery={memoryQuery}
              onAskChat={(q) => openChatWith(q)}
              onOpenSearch={(q) => openSearchPage(q)}
            />
          )}

          {active === 'search' && (
            <SearchPage
              initialQuery={searchQuery}
              onAskChat={openChatWith}
              onExploreMemory={openMemory}
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
                setChatSeed(null)
                setActive('chat')
              }}
              onSearchDocument={(doc) => {
                setSearchDocumentId(doc.document_id)
                setSearchDocumentLabel(doc.source)
                setModal('search')
              }}
            />
          )}

          {active === 'chats' && (
            <ChatsManager
              activeConversationId={conversationId}
              refreshToken={conversationRefresh}
              onOpenChat={(id) => {
                setConversationId(id)
                setChatDocumentId(null)
                setChatSeed(null)
                setActive('chat')
              }}
              onClearedActive={() => setConversationId(null)}
            />
          )}

          {active === 'activity' && (
            <Activity
              onOpenKnowledge={() => navigate('knowledge')}
              onExploreMemory={openMemory}
            />
          )}

          {active === 'settings' && <Settings apiOk={apiOk} />}
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
          onOpenFullSearch={(q) => openSearchPage(q)}
        />
      )}
    </main>
  )
}
