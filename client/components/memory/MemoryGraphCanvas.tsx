'use client'

import { useEffect, useMemo, useRef, type KeyboardEvent } from 'react'
import type { MemoryGraphEdge, MemoryGraphNode } from '@/lib/api'

export type RelationKind = 'updates' | 'extends' | 'derives' | 'related'

type Props = {
  nodes: MemoryGraphNode[]
  edges: MemoryGraphEdge[]
  selectedId: string | null
  onSelect: (id: string) => void
  loading?: boolean
}

const W = 720
const H = 420

function normalizeRelation(raw: string): RelationKind {
  const r = (raw || '').toLowerCase().trim()
  if (r.includes('update')) return 'updates'
  if (r.includes('extend')) return 'extends'
  if (r.includes('deriv')) return 'derives'
  return 'related'
}

function truncate(label: string, max = 26): string {
  const t = (label || '').trim()
  if (t.length <= max) return t
  return `${t.slice(0, max - 1)}…`
}

function shortenLine(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  padStart: number,
  padEnd: number,
) {
  const dx = x2 - x1
  const dy = y2 - y1
  const len = Math.hypot(dx, dy) || 1
  const ux = dx / len
  const uy = dy / len
  return {
    x1: x1 + ux * padStart,
    y1: y1 + uy * padStart,
    x2: x2 - ux * padEnd,
    y2: y2 - uy * padEnd,
  }
}

/** Dependency-free multi-ring layout: focus at center, neighbors on rings. */
function layoutNodes(
  nodes: MemoryGraphNode[],
  edges: MemoryGraphEdge[],
  selectedId: string | null,
) {
  const positions = new Map<string, { x: number; y: number }>()
  const cx = W / 2
  const cy = H / 2

  if (nodes.length === 0) return positions

  const byId = new Map(nodes.map((n) => [n.id, n]))
  const focusId =
    (selectedId && byId.has(selectedId) ? selectedId : null) ||
    [...nodes].sort((a, b) => (b.score || 0) - (a.score || 0))[0]?.id ||
    nodes[0].id

  positions.set(focusId, { x: cx, y: cy })

  const adjacency = new Map<string, Set<string>>()
  for (const n of nodes) adjacency.set(n.id, new Set())
  for (const e of edges) {
    adjacency.get(e.source)?.add(e.target)
    adjacency.get(e.target)?.add(e.source)
  }

  const neighbors = [...(adjacency.get(focusId) || [])].filter((id) =>
    byId.has(id),
  )
  const neighborSet = new Set(neighbors)
  const outer = nodes
    .map((n) => n.id)
    .filter((id) => id !== focusId && !neighborSet.has(id))

  const placeRing = (ids: string[], radius: number, angleOffset = 0) => {
    const count = ids.length
    if (count === 0) return
    ids.forEach((id, i) => {
      const angle =
        angleOffset + (i / count) * Math.PI * 2 - Math.PI / 2
      // Slight radial jitter by score rank so rings aren't perfectly flat.
      const jitter = ((i % 3) - 1) * 8
      positions.set(id, {
        x: cx + Math.cos(angle) * (radius + jitter),
        y: cy + Math.sin(angle) * (radius + jitter * 0.6),
      })
    })
  }

  if (neighbors.length > 0 && outer.length === 0) {
    placeRing(neighbors, Math.min(W, H) * 0.32)
  } else {
    placeRing(neighbors, Math.min(W, H) * 0.28, 0.12)
    // Split remaining into mid + outer ring by score.
    const ranked = outer
      .map((id) => byId.get(id)!)
      .sort((a, b) => (b.score || 0) - (a.score || 0))
    const midCount = Math.ceil(ranked.length / 2)
    const mid = ranked.slice(0, midCount).map((n) => n.id)
    const far = ranked.slice(midCount).map((n) => n.id)
    placeRing(mid, Math.min(W, H) * 0.38, 0.35)
    placeRing(far, Math.min(W, H) * 0.46, -0.2)
  }

  // Safety: any missing node
  nodes.forEach((n, i) => {
    if (positions.has(n.id)) return
    const angle = (i / nodes.length) * Math.PI * 2
    positions.set(n.id, {
      x: cx + Math.cos(angle) * 140,
      y: cy + Math.sin(angle) * 140,
    })
  })

  return positions
}

export function MemoryGraphCanvas({
  nodes,
  edges,
  selectedId,
  onSelect,
  loading = false,
}: Props) {
  const orderRef = useRef<string[]>([])

  const positions = useMemo(
    () => layoutNodes(nodes, edges, selectedId),
    [nodes, edges, selectedId],
  )

  useEffect(() => {
    orderRef.current = nodes.map((n) => n.id)
  }, [nodes])

  const onKeyDown = (e: KeyboardEvent<SVGSVGElement>) => {
    if (nodes.length === 0) return
    const ids = orderRef.current.length ? orderRef.current : nodes.map((n) => n.id)
    const current = selectedId && ids.includes(selectedId) ? selectedId : ids[0]
    const idx = Math.max(0, ids.indexOf(current))

    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault()
      onSelect(ids[(idx + 1) % ids.length])
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault()
      onSelect(ids[(idx - 1 + ids.length) % ids.length])
    } else if (e.key === 'Home') {
      e.preventDefault()
      onSelect(ids[0])
    } else if (e.key === 'End') {
      e.preventDefault()
      onSelect(ids[ids.length - 1])
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onSelect(current)
    }
  }

  if (loading) {
    return (
      <div className="graph-empty graph-loading" role="status" aria-live="polite">
        <div className="graph-spinner" aria-hidden />
        <p>Building memory graph…</p>
      </div>
    )
  }

  if (nodes.length === 0) {
    return (
      <div className="graph-empty">
        <p>No graph yet</p>
        <span className="muted">
          Explore a question or preset above. Edges show how facts{' '}
          <em>update</em>, <em>extend</em>, or <em>derive</em> from each other.
        </span>
      </div>
    )
  }

  const selectedLabel =
    nodes.find((n) => n.id === selectedId)?.label || 'memory graph'

  return (
    <div className="memory-graph-wrap">
      <svg
        className="memory-graph-svg"
        viewBox={`0 0 ${W} ${H}`}
        role="listbox"
        aria-label="Supermemory relationship graph"
        aria-activedescendant={selectedId ? `graph-node-${selectedId}` : undefined}
        tabIndex={0}
        onKeyDown={onKeyDown}
      >
        <defs>
          <marker
            id="arrow-updates"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" className="graph-arrow updates" />
          </marker>
          <marker
            id="arrow-extends"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" className="graph-arrow extends" />
          </marker>
          <marker
            id="arrow-derives"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" className="graph-arrow derives" />
          </marker>
          <marker
            id="arrow-related"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" className="graph-arrow related" />
          </marker>
        </defs>

        <title>{selectedLabel}</title>

        {edges.map((e) => {
          const a = positions.get(e.source)
          const b = positions.get(e.target)
          if (!a || !b) return null
          const rel = normalizeRelation(e.relation)
          const line = shortenLine(a.x, a.y, b.x, b.y, 18, 20)
          const mx = (line.x1 + line.x2) / 2
          const my = (line.y1 + line.y2) / 2
          return (
            <g key={e.id} className={`graph-edge-group rel-${rel}`}>
              <line
                x1={line.x1}
                y1={line.y1}
                x2={line.x2}
                y2={line.y2}
                className={`graph-edge rel-${rel}`}
                markerEnd={`url(#arrow-${rel})`}
              />
              <rect
                x={mx - 22}
                y={my - 9}
                width={44}
                height={14}
                rx={3}
                className="graph-edge-label-bg"
              />
              <text x={mx} y={my + 2} textAnchor="middle" className="graph-edge-label">
                {rel}
              </text>
            </g>
          )
        })}

        {nodes.map((node) => {
          const p = positions.get(node.id)
          if (!p) return null
          const active = node.id === selectedId
          const r = active ? 20 : node.kind === 'document' ? 13 : 15
          return (
            <g
              key={node.id}
              id={`graph-node-${node.id}`}
              role="option"
              aria-selected={active}
              tabIndex={-1}
              className={`graph-node ${node.kind} ${active ? 'active' : ''}`}
              onClick={() => onSelect(node.id)}
              onKeyDown={(ev) => {
                if (ev.key === 'Enter' || ev.key === ' ') {
                  ev.preventDefault()
                  onSelect(node.id)
                }
              }}
            >
              {active ? (
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={r + 6}
                  className="graph-node-halo"
                />
              ) : null}
              <circle cx={p.x} cy={p.y} r={r} />
              <title>{node.label}</title>
              <text x={p.x} y={p.y + r + 14} textAnchor="middle">
                {truncate(node.label)}
              </text>
            </g>
          )
        })}
      </svg>

      <div className="graph-legend" aria-hidden={false}>
        <span className="graph-legend-item updates">updates</span>
        <span className="graph-legend-item extends">extends</span>
        <span className="graph-legend-item derives">derives</span>
      </div>
      <p className="graph-a11y-hint muted">
        Focus the graph, then use arrow keys to move between memories.
      </p>
    </div>
  )
}

export function countRelations(edges: MemoryGraphEdge[]) {
  const counts = { updates: 0, extends: 0, derives: 0, related: 0 }
  for (const e of edges) {
    counts[normalizeRelation(e.relation)] += 1
  }
  return counts
}

export function normalizeRelationKind(raw: string): RelationKind {
  return normalizeRelation(raw)
}
