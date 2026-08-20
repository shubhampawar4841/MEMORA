'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Network, RefreshCw, Search, Sparkles } from 'lucide-react'
import {
  getMemoryGraph,
  getMemoryProfile,
  type MemoryGraphEdge,
  type MemoryGraphNode,
  type MemoryHit,
  type MemoryProfile,
} from '@/lib/api'
import {
  MemoryGraphCanvas,
  countRelations,
  normalizeRelationKind,
} from '@/components/memory/MemoryGraphCanvas'

type Props = {
  initialQuery?: string | null
  onAskChat?: (query: string) => void
  onOpenSearch?: (query: string) => void
}

type FactChip = { kind: 'static' | 'dynamic'; text: string }

type ConnectedNeighbor = {
  id: string
  label: string
  relation: string
  direction: 'out' | 'in'
}

const PRESETS: { id: string; label: string; query: string }[] = [
  {
    id: 'skills',
    label: 'Skills',
    query: 'What skills, technologies, and strengths does this person have?',
  },
  {
    id: 'work',
    label: 'Work',
    query: 'What work experience, roles, and companies are known?',
  },
  {
    id: 'projects',
    label: 'Projects',
    query: 'What projects, products, and repositories has this person worked on?',
  },
  {
    id: 'people',
    label: 'People',
    query: 'Which people, teammates, and collaborators are mentioned?',
  },
  {
    id: 'recent',
    label: 'Recent',
    query: 'What are the most recent activities, updates, and events?',
  },
]

function resolveNodeId(
  candidateId: string,
  nodes: MemoryGraphNode[],
  hit?: MemoryHit,
): string | null {
  if (nodes.some((n) => n.id === candidateId)) return candidateId

  if (hit) {
    const byExactLabel = nodes.find(
      (n) => n.label.trim() === hit.text.trim(),
    )
    if (byExactLabel) return byExactLabel.id

    const snippet = hit.text.trim().slice(0, 48).toLowerCase()
    if (snippet) {
      const byPrefix = nodes.find((n) =>
        n.label.toLowerCase().includes(snippet),
      )
      if (byPrefix) return byPrefix.id
    }
  }

  const fuzzy = nodes.find(
    (n) =>
      n.id.includes(candidateId) ||
      candidateId.includes(n.id) ||
      n.label.toLowerCase().includes(candidateId.toLowerCase()),
  )
  return fuzzy?.id ?? null
}

export function Memory({
  initialQuery = null,
  onAskChat,
  onOpenSearch,
}: Props) {
  const [profile, setProfile] = useState<MemoryProfile | null>(null)
  const [query, setQuery] = useState(initialQuery || '')
  const [activePreset, setActivePreset] = useState<string | null>(null)
  const [nodes, setNodes] = useState<MemoryGraphNode[]>([])
  const [edges, setEdges] = useState<MemoryGraphEdge[]>([])
  const [results, setResults] = useState<MemoryHit[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [loadingProfile, setLoadingProfile] = useState(true)
  const [loadingGraph, setLoadingGraph] = useState(false)
  const [hasExplored, setHasExplored] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadProfile = useCallback(async () => {
    setLoadingProfile(true)
    try {
      const res = await getMemoryProfile()
      setProfile(res)
      if (res.error && !res.ok) setError(res.error)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load profile')
    } finally {
      setLoadingProfile(false)
    }
  }, [])

  const explore = useCallback(async (q: string, presetId?: string | null) => {
    const trimmed = q.trim()
    if (!trimmed) return
    setLoadingGraph(true)
    setError(null)
    setHasExplored(true)
    setActivePreset(presetId ?? null)
    try {
      const res = await getMemoryGraph({ q: trimmed, limit: 16 })
      if (res.error && !res.ok) setError(res.error)
      const nextNodes = res.nodes || []
      const nextEdges = res.edges || []
      const nextResults = res.results || []
      setNodes(nextNodes)
      setEdges(nextEdges)
      setResults(nextResults)

      const top =
        [...nextNodes].sort((a, b) => (b.score || 0) - (a.score || 0))[0]
          ?.id ?? null
      setSelectedId(top)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Graph explore failed')
      setNodes([])
      setEdges([])
      setResults([])
      setSelectedId(null)
    } finally {
      setLoadingGraph(false)
    }
  }, [])

  useEffect(() => {
    void loadProfile()
  }, [loadProfile])

  useEffect(() => {
    if (initialQuery?.trim()) {
      setQuery(initialQuery)
      void explore(initialQuery)
    }
  }, [initialQuery, explore])

  const selected = useMemo(
    () => nodes.find((n) => n.id === selectedId) || null,
    [nodes, selectedId],
  )

  const neighbors = useMemo((): ConnectedNeighbor[] => {
    if (!selectedId) return []
    const out: ConnectedNeighbor[] = []
    for (const e of edges) {
      if (e.source === selectedId) {
        const target = nodes.find((n) => n.id === e.target)
        out.push({
          id: e.target,
          label: target?.label || e.target,
          relation: normalizeRelationKind(e.relation),
          direction: 'out',
        })
      } else if (e.target === selectedId) {
        const source = nodes.find((n) => n.id === e.source)
        out.push({
          id: e.source,
          label: source?.label || e.source,
          relation: normalizeRelationKind(e.relation),
          direction: 'in',
        })
      }
    }
    return out
  }, [edges, nodes, selectedId])

  const relationCounts = useMemo(() => countRelations(edges), [edges])

  const facts: FactChip[] = [
    ...(profile?.static || [])
      .slice(0, 8)
      .map((t) => ({ kind: 'static' as const, text: t })),
    ...(profile?.dynamic || [])
      .slice(0, 6)
      .map((t) => ({ kind: 'dynamic' as const, text: t })),
  ]

  const selectFromHit = (hit: MemoryHit) => {
    const resolved = resolveNodeId(hit.id, nodes, hit)
    if (resolved) {
      setSelectedId(resolved)
      return
    }
    // Fallback: synthesize focus from hit text if graph has no matching id.
    setSelectedId(nodes[0]?.id ?? null)
  }

  return (
    <section className="content-page memory-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">SUPERMEMORY GRAPH</span>
          <h1>Memory</h1>
          <p>
            Living facts connected by updates, extensions, and derived insights
            in{' '}
            <code className="inline-code">
              {profile?.container_tag || 'user_*'}
            </code>
            .
          </p>
        </div>
        <button
          className="filter-btn"
          type="button"
          onClick={() => void loadProfile()}
          disabled={loadingProfile}
        >
          <RefreshCw size={14} />
          Refresh profile
        </button>
      </div>

      <div className="memory-profile-strip">
        <div className="memory-section-head">
          <h2>What Nerva knows about you</h2>
          <span className="muted">
            {loadingProfile
              ? 'Loading…'
              : `${facts.length} fact${facts.length === 1 ? '' : 's'}`}
          </span>
        </div>

        {loadingProfile ? (
          <p className="muted">Loading profile…</p>
        ) : facts.length === 0 ? (
          <div className="empty-panel compact">
            <Sparkles size={18} />
            <p>
              No extracted facts yet. Upload docs or connect Gmail/GitHub —
              memories appear after Supermemory indexes and dreams.
            </p>
          </div>
        ) : (
          <div className="fact-chips">
            {facts.map((f, i) => (
              <button
                key={`${f.kind}-${i}`}
                type="button"
                className={`fact-chip ${f.kind}`}
                title={f.text}
                onClick={() => {
                  setQuery(f.text.slice(0, 120))
                  void explore(f.text.slice(0, 160))
                }}
              >
                <span>{f.kind === 'static' ? 'Stable' : 'Recent'}</span>
                {f.text.length > 72 ? `${f.text.slice(0, 71)}…` : f.text}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="memory-presets" role="group" aria-label="Quick explore">
        {PRESETS.map((p) => (
          <button
            key={p.id}
            type="button"
            className={`filter-btn ${activePreset === p.id ? 'active' : ''}`}
            disabled={loadingGraph}
            onClick={() => {
              setQuery(p.query)
              void explore(p.query, p.id)
            }}
          >
            {p.label}
          </button>
        ))}
      </div>

      <form
        className="memory-explore"
        onSubmit={(e) => {
          e.preventDefault()
          void explore(query)
        }}
      >
        <div className="field memory-field">
          <Search size={16} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="What does Nerva know about…?"
            aria-label="Explore memory graph query"
          />
        </div>
        <button
          className="primary-btn"
          type="submit"
          disabled={loadingGraph || !query.trim()}
        >
          <Network size={16} />
          {loadingGraph ? 'Exploring…' : 'Explore graph'}
        </button>
      </form>

      {error ? <p className="form-error">{error}</p> : null}

      {(hasExplored || nodes.length > 0) && (
        <div className="memory-stats" aria-live="polite">
          <div>
            <strong>{nodes.length}</strong>
            <span>graph memories</span>
          </div>
          <div>
            <strong>{results.length}</strong>
            <span>search hits</span>
          </div>
          <div>
            <strong>{relationCounts.updates}</strong>
            <span>updates</span>
          </div>
          <div>
            <strong>{relationCounts.extends}</strong>
            <span>extensions</span>
          </div>
          <div>
            <strong>{relationCounts.derives}</strong>
            <span>derived</span>
          </div>
        </div>
      )}

      <div className="memory-layout">
        <div className="memory-graph-panel">
          <MemoryGraphCanvas
            nodes={nodes}
            edges={edges}
            selectedId={selectedId}
            onSelect={setSelectedId}
            loading={loadingGraph}
          />
        </div>

        <aside className="memory-side">
          {selected ? (
            <>
              <span className="eyebrow">SELECTED MEMORY</span>
              <div className="memory-side-meta">
                <span className={`kind-pill ${selected.kind}`}>
                  {selected.kind}
                </span>
                <span className="muted">
                  score {selected.score.toFixed(3)}
                </span>
              </div>
              <p className="memory-side-label">{selected.label}</p>
              <p className="muted">
                {neighbors.length} connection
                {neighbors.length === 1 ? '' : 's'}
              </p>

              {neighbors.length > 0 ? (
                <div className="memory-connections">
                  <span className="eyebrow">CONNECTED MEMORIES</span>
                  <ul>
                    {neighbors.map((n) => (
                      <li key={`${n.id}-${n.relation}-${n.direction}`}>
                        <button
                          type="button"
                          className="memory-connection"
                          onClick={() => setSelectedId(n.id)}
                        >
                          <span className={`rel-pill ${n.relation}`}>
                            {n.relation}
                            {n.direction === 'in' ? ' ←' : ' →'}
                          </span>
                          <strong>
                            {n.label.length > 90
                              ? `${n.label.slice(0, 89)}…`
                              : n.label}
                          </strong>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="muted" style={{ marginTop: 12 }}>
                  No related edges returned for this node yet.
                </p>
              )}

              <div className="row-actions" style={{ marginTop: 14 }}>
                {onAskChat ? (
                  <button
                    className="filter-btn"
                    type="button"
                    onClick={() => onAskChat(selected.label.slice(0, 160))}
                  >
                    Ask in Chat
                  </button>
                ) : null}
                {onOpenSearch ? (
                  <button
                    className="filter-btn"
                    type="button"
                    onClick={() => onOpenSearch(selected.label.slice(0, 120))}
                  >
                    Open Search
                  </button>
                ) : null}
              </div>
            </>
          ) : (
            <div className="memory-side-empty">
              <Network size={18} />
              <p className="muted">
                {hasExplored
                  ? 'Select a node in the graph or a hit below.'
                  : 'Run a preset or query to inspect related memories.'}
              </p>
            </div>
          )}
        </aside>
      </div>

      {results.length > 0 && (
        <div className="memory-results">
          <div className="recent-head">
            <h2>Hits</h2>
            <span className="muted">{results.length}</span>
          </div>
          <ul className="hit-list">
            {results.map((r) => {
              const resolved = resolveNodeId(r.id, nodes, r)
              const active =
                selectedId != null &&
                (selectedId === r.id || selectedId === resolved)
              return (
                <li key={r.id}>
                  <button
                    type="button"
                    className={active ? 'active' : ''}
                    onClick={() => selectFromHit(r)}
                  >
                    <span className={`kind-pill ${r.kind}`}>{r.kind}</span>
                    <strong>
                      {r.text.slice(0, 140)}
                      {r.text.length > 140 ? '…' : ''}
                    </strong>
                    <em>{r.score.toFixed(2)}</em>
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </section>
  )
}
