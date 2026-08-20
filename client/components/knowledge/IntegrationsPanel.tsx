'use client'

import { useCallback, useEffect, useState } from 'react'
import { GitBranch, Mail, Unplug } from 'lucide-react'
import {
  deleteConnection,
  getConnectDefaults,
  listConnections,
  startConnect,
  type ConnectionItem,
} from '@/lib/api'

type Props = {
  onStatus?: (message: string | null) => void
}

export function IntegrationsPanel({ onStatus }: Props) {
  const [userId, setUserId] = useState('shubham')
  const [containerTag, setContainerTag] = useState('user_shubham')
  const [connections, setConnections] = useState<ConnectionItem[]>([])
  const [planNotes, setPlanNotes] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const defaults = await getConnectDefaults()
      setUserId(defaults.user_id)
      setContainerTag(defaults.container_tag)
      setPlanNotes(defaults.plan_notes || {})
      const listed = await listConnections(defaults.user_id)
      setConnections(listed.connections || [])
      if (listed.error) setError(listed.error)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load connectors')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const connect = async (provider: 'gmail' | 'github') => {
    setBusy(provider)
    setError(null)
    onStatus?.(null)
    try {
      const res = await startConnect(provider, { userId })
      if (!res.auth_link) {
        throw new Error('No auth link returned from Supermemory')
      }
      onStatus?.(
        `Opening ${provider} OAuth… after approval, data syncs into ${res.container_tag}.`,
      )
      window.location.href = res.auth_link
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connect failed')
    } finally {
      setBusy(null)
    }
  }

  const disconnect = async (id: string) => {
    if (!window.confirm('Disconnect this integration? Synced docs are kept.')) {
      return
    }
    setBusy(id)
    try {
      await deleteConnection(id, false)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Disconnect failed')
    } finally {
      setBusy(null)
    }
  }

  const has = (provider: string) =>
    connections.some(
      (c) => String(c.provider || '').toLowerCase() === provider,
    )

  return (
    <div
      style={{
        marginBottom: 18,
        padding: '16px 18px',
        border: '1px solid #242844',
        borderRadius: 10,
        background: '#0f1324',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          gap: 12,
          flexWrap: 'wrap',
          alignItems: 'flex-start',
        }}
      >
        <div>
          <span className="eyebrow">SUPERMEMORY CONNECTORS</span>
          <h2 style={{ margin: '6px 0 4px', fontSize: 16 }}>
            Gmail &amp; GitHub
          </h2>
          <p style={{ margin: 0, color: '#737b94', maxWidth: 560 }}>
            OAuth via Supermemory into{' '}
            <code style={{ color: '#c4b5fd' }}>{containerTag}</code>
            {' '}(same tag as uploads). Scale/Enterprise required for Gmail &amp;
            GitHub.
          </p>
        </div>
        <button className="filter-btn" type="button" onClick={() => void refresh()}>
          Refresh status
        </button>
      </div>

      <div
        style={{
          display: 'flex',
          gap: 8,
          flexWrap: 'wrap',
          marginTop: 14,
        }}
      >
        <button
          className="primary-btn"
          type="button"
          disabled={busy !== null}
          onClick={() => void connect('gmail')}
        >
          <Mail size={16} />
          {busy === 'gmail'
            ? 'Starting…'
            : has('gmail')
              ? 'Reconnect Gmail'
              : 'Connect Gmail'}
        </button>
        <button
          className="primary-btn"
          type="button"
          disabled={busy !== null}
          onClick={() => void connect('github')}
          style={{ background: '#1f2937' }}
        >
          <GitBranch size={16} />
          {busy === 'github'
            ? 'Starting…'
            : has('github')
              ? 'Reconnect GitHub'
              : 'Connect GitHub'}
        </button>
      </div>

      <div style={{ margin: '10px 0 0', fontSize: 12, color: '#737b94' }}>
        <details className="integrations-notes">
          <summary>Plan &amp; sync notes</summary>
          <p>
            {planNotes.gmail ||
              'Gmail requires Supermemory Scale or Enterprise. OAuth is handled by Supermemory — no Google API credentials are required in Nerva.'}
          </p>
          <p>
            {planNotes.github ||
              'GitHub requires Supermemory Scale or Enterprise. OAuth is handled by Supermemory — no GitHub API credentials are required in Nerva.'}
          </p>
          <p>
            GitHub sync defaults to documentation/text files (.md, .txt, …);
            source code (.js, .py, .go, …) is excluded by default.
          </p>
        </details>
      </div>

      {error ? (
        <p style={{ margin: '10px 0 0', color: '#f87171' }}>{error}</p>
      ) : null}

      {loading ? (
        <p style={{ margin: '12px 0 0', color: '#737b94' }}>Loading…</p>
      ) : connections.length === 0 ? (
        <p style={{ margin: '12px 0 0', color: '#737b94' }}>
          No connectors yet for user <strong>{userId}</strong>.
        </p>
      ) : (
        <ul style={{ margin: '12px 0 0', padding: 0, listStyle: 'none' }}>
          {connections.map((c) => {
            const id = String(c.id || '')
            return (
              <li
                key={id || String(c.provider)}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 8,
                  alignItems: 'center',
                  padding: '8px 0',
                  borderTop: '1px solid #1c2238',
                }}
              >
                <span>
                  <strong style={{ textTransform: 'capitalize' }}>
                    {String(c.provider || 'unknown')}
                  </strong>
                  {c.email ? (
                    <span style={{ color: '#737b94' }}> · {String(c.email)}</span>
                  ) : null}
                </span>
                {id ? (
                  <button
                    className="filter-btn"
                    type="button"
                    disabled={busy === id}
                    onClick={() => void disconnect(id)}
                  >
                    <Unplug size={14} />
                    Disconnect
                  </button>
                ) : null}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
