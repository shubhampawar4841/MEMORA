'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  BarVisualizer,
  ControlBar,
  RoomAudioRenderer,
  SessionProvider,
  useAgent,
  useSession,
} from '@livekit/components-react'
import '@livekit/components-styles'
import { TokenSource } from 'livekit-client'
import { Phone, Radio, Sparkles } from 'lucide-react'
import { getVoiceStatus } from '@/lib/api'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const AGENT_NAME = 'Shubham_Assistent'

const tokenSource = TokenSource.endpoint(`${API_URL}/voice/token`)

function AgentStage() {
  const agent = useAgent()

  const statusLabel = useMemo(() => {
    switch (agent.state) {
      case 'listening':
        return 'Listening'
      case 'thinking':
        return 'Thinking'
      case 'speaking':
        return 'Speaking'
      case 'connecting':
      case 'initializing':
      case 'pre-connect-buffering':
        return 'Agent joining…'
      case 'failed':
        return 'Agent failed to join'
      case 'disconnected':
        return 'Disconnected'
      default:
        return 'On call'
    }
  }, [agent.state])

  const orbClass =
    agent.state === 'speaking'
      ? 'call-orb speaking'
      : agent.state === 'listening'
        ? 'call-orb listening'
        : agent.state === 'thinking'
          ? 'call-orb thinking'
          : agent.state === 'failed'
            ? 'call-orb'
            : 'call-orb'

  return (
    <div className="call-stage">
      <div className={orbClass}>
        <Sparkles size={28} />
      </div>
      <p className="call-status">{statusLabel}</p>
      <p className="call-room muted">Live with Nerva · {AGENT_NAME}</p>

      {agent.canListen && agent.microphoneTrack && (
        <div className="call-visualizer" style={{ height: 80, width: 'min(320px, 90%)' }}>
          <BarVisualizer
            track={agent.microphoneTrack}
            state={agent.state}
            barCount={5}
          />
        </div>
      )}

      {agent.state === 'failed' && (
        <p className="form-error">
          Agent did not join. Make sure the worker is running with{' '}
          <code className="inline-code">lk agent dev</code> from backend/.
        </p>
      )}
    </div>
  )
}

function ActiveCall({ onEnded }: { onEnded: () => void }) {
  const session = useSession(tokenSource, { agentName: AGENT_NAME })
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void session
      .start({
        tracks: {
          microphone: { enabled: true },
          camera: { enabled: false },
          screenShare: { enabled: false },
        },
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Could not start session')
      })

    return () => {
      cancelled = true
      void session.end()
    }
    // Start once per mount of ActiveCall
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <SessionProvider session={session}>
      <div className="call-room-wrap" data-lk-theme="default">
        {error && <p className="form-error">{error}</p>}
        <AgentStage />
        <div className="call-control-bar">
          <ControlBar
            controls={{ microphone: true, camera: false, screenShare: false, leave: true }}
            onDeviceError={(e) => setError(e.error.message)}
          />
        </div>
        <RoomAudioRenderer />
        <button
          type="button"
          className="call-end-link muted"
          onClick={() => {
            void session.end().finally(onEnded)
          }}
        >
          End & back
        </button>
      </div>
    </SessionProvider>
  )
}

export function Call() {
  const [live, setLive] = useState(false)
  const [configured, setConfigured] = useState<boolean | null>(null)
  const [backendOk, setBackendOk] = useState<boolean | null>(null)
  const [agentName, setAgentName] = useState(AGENT_NAME)

  const refreshStatus = useCallback(() => {
    void getVoiceStatus()
      .then((s) => {
        setBackendOk(true)
        setConfigured(s.configured)
        if (s.agent_name) setAgentName(s.agent_name)
      })
      .catch(() => {
        setBackendOk(false)
        setConfigured(false)
      })
  }, [])

  useEffect(() => {
    refreshStatus()
  }, [refreshStatus])

  const canStart =
    backendOk !== false && configured !== false

  return (
    <section className="content-page call-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">VOICE</span>
          <h1>Call Nerva</h1>
          <p>
            Talk with your personal assistant. Answers come from SuperMemory —
            documents, connectors, and remembered facts.
          </p>
        </div>
        <div className="health">
          <Radio size={14} />
          {backendOk === false
            ? 'Backend offline'
            : configured === null
              ? 'Checking LiveKit…'
              : configured
                ? `Ready · ${agentName}`
                : 'LiveKit not configured'}
        </div>
      </div>

      {!live ? (
        <div className="call-idle">
          <div className="call-orb idle">
            <Phone size={28} />
          </div>
          <h2>Ready when you are</h2>
          <p className="muted">
            Start a call and {agentName} will join. Allow microphone access when
            prompted.
          </p>
          <button
            type="button"
            className="primary-btn call-start"
            disabled={!canStart}
            onClick={() => setLive(true)}
          >
            <Phone size={16} />
            Start call
          </button>
          {backendOk === false && (
            <p className="muted call-hint">
              Backend is not reachable at {API_URL}. Check NEXT_PUBLIC_API_URL
              and that the API is running, then refresh.
            </p>
          )}
          {backendOk && configured === false && (
            <p className="muted call-hint">
              Set LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET in
              backend/.env.local, restart the API, then try again.
            </p>
          )}
        </div>
      ) : (
        <ActiveCall
          onEnded={() => {
            setLive(false)
            refreshStatus()
          }}
        />
      )}
    </section>
  )
}
