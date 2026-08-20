'use client'

import { useEffect, useState } from 'react'
import { ExternalLink, Settings as SettingsIcon } from 'lucide-react'
import { getConnectDefaults, getHome } from '@/lib/api'

type Props = {
  apiOk: boolean | null
}

export function Settings({ apiOk }: Props) {
  const [userId, setUserId] = useState<string>('—')
  const [containerTag, setContainerTag] = useState<string>('—')
  const [planNotes, setPlanNotes] = useState<Record<string, string>>({})
  const [apiMessage, setApiMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void getConnectDefaults()
      .then((res) => {
        setUserId(res.user_id)
        setContainerTag(res.container_tag)
        setPlanNotes(res.plan_notes || {})
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load settings')
      })
    void getHome()
      .then((res) => setApiMessage(res.message))
      .catch(() => setApiMessage(null))
  }, [])

  return (
    <section className="content-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">WORKSPACE</span>
          <h1>Settings</h1>
          <p>Read-only workspace identity and connector plan notes.</p>
        </div>
      </div>

      {error ? <p className="form-error">{error}</p> : null}

      <div className="settings-grid">
        <div className="settings-card">
          <span className="eyebrow">API</span>
          <p>
            Status:{' '}
            <strong>
              {apiOk == null ? 'Checking…' : apiOk ? 'Healthy' : 'Offline'}
            </strong>
          </p>
          {apiMessage ? <p className="muted">{apiMessage}</p> : null}
        </div>

        <div className="settings-card">
          <span className="eyebrow">SUPERMEMORY SCOPE</span>
          <p>
            User id: <code className="inline-code">{userId}</code>
          </p>
          <p>
            Container: <code className="inline-code">{containerTag}</code>
          </p>
          <p className="muted">
            Uploads, Gmail, GitHub, and search all share this container tag.
          </p>
        </div>

        <div className="settings-card">
          <span className="eyebrow">CONNECTOR PLANS</span>
          <p>{planNotes.gmail || 'Gmail requires Scale or Enterprise.'}</p>
          <p>{planNotes.github || 'GitHub requires Scale or Enterprise.'}</p>
          <a
            className="settings-link"
            href="https://console.supermemory.ai"
            target="_blank"
            rel="noreferrer"
          >
            Open Supermemory Console
            <ExternalLink size={14} />
          </a>
        </div>
      </div>

      <div className="empty-panel compact" style={{ marginTop: 20 }}>
        <SettingsIcon size={18} />
        <p>
          Change <code>NERVA_USER_ID</code> /{' '}
          <code>SUPERMEMORY_CONTAINER_TAG</code> in backend <code>.env</code>,
          then restart the API.
        </p>
      </div>
    </section>
  )
}
