import React from 'react'

// Hand-rolled SVG multi-series line chart. No chart dependency (CPU-first,
// minimal-deps rule). Pure presentational: takes series + an x label list.
const PALETTE = [
  '#d6002a', '#0d0d0d', '#0a7d55', '#d97706', '#7c3aed',
  '#0891b2', '#8a6100', '#65a30d', '#9333ea', '#565656',
]

export default function LineChart({ labels, series, height = 260, yFormat = (v) => v, activeIndex = null }) {
  if (!labels || labels.length === 0 || !series || series.length === 0) {
    return <p className="muted">No data yet.</p>
  }
  const width = 720
  const pad = { top: 12, right: 120, bottom: 24, left: 44 }
  const iw = width - pad.left - pad.right
  const ih = height - pad.top - pad.bottom

  const allVals = series.flatMap((s) => s.values).filter((v) => v != null)
  const maxV = Math.max(...allVals)
  const minV = Math.min(...allVals, 0)
  const span = maxV - minV || 1

  const x = (i) => pad.left + (labels.length === 1 ? iw / 2 : (i / (labels.length - 1)) * iw)
  const y = (v) => pad.top + ih - ((v - minV) / span) * ih

  const ticks = [minV, minV + span / 2, maxV]

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      style={{ width: '100%', height: 'auto', maxWidth: width }}
      role="img"
    >
      {/* y gridlines + labels */}
      {ticks.map((t, i) => (
        <g key={i}>
          <line x1={pad.left} x2={width - pad.right} y1={y(t)} y2={y(t)} stroke="#e1e4e8" />
          <text x={pad.left - 6} y={y(t) + 3} fontSize="9" textAnchor="end" fill="#6b7280">
            {yFormat(t)}
          </text>
        </g>
      ))}
      {/* x labels (first, middle, last) */}
      {[0, Math.floor(labels.length / 2), labels.length - 1].map((i) => (
        <text key={i} x={x(i)} y={height - 8} fontSize="9" textAnchor="middle" fill="#6b7280">
          {labels[i]}
        </text>
      ))}
      {/* series polylines */}
      {series.map((s, si) => {
        const pts = s.values
          .map((v, i) => (v == null ? null : `${x(i)},${y(v)}`))
          .filter(Boolean)
          .join(' ')
        const color = PALETTE[si % PALETTE.length]
        return <polyline key={s.name} points={pts} fill="none" stroke={color} strokeWidth="1.5" />
      })}
      {activeIndex != null && activeIndex >= 0 && activeIndex < labels.length && (
        <line
          x1={x(activeIndex)} x2={x(activeIndex)}
          y1={pad.top} y2={pad.top + ih}
          stroke="#d6002a" strokeDasharray="3 3"
        />
      )}
      {/* legend */}
      {series.map((s, si) => (
        <g key={s.name} transform={`translate(${width - pad.right + 6}, ${pad.top + si * 14})`}>
          <rect width="10" height="3" y="7" fill={PALETTE[si % PALETTE.length]} />
          <text x="14" y="10" fontSize="10" fill="#374151">{s.name}</text>
        </g>
      ))}
    </svg>
  )
}
