import React, { useEffect, useState } from 'react'
import { getSignals, livePoll } from '../api.js'

function SentimentCell({ v }) {
  if (v === null || v === undefined) return <span className="muted">null</span>
  const cls = v < 0 ? 'neg' : v > 0 ? 'pos' : 'neu'
  return <span className={`sent ${cls}`}>{v.toFixed(2)}</span>
}

function ProvenanceBadge({ p }) {
  return <span className={`prov prov-${p}`}>{p}</span>
}

// HOT score: blend recency decay with |sentiment| and impact so high-signal
// items surface, not just the newest (which are often null/neutral).
function hotScore(s, nowMs) {
  const t = Date.parse(s.analyzed_at || s.published_at || 0)
  const ageHours = Math.max(0, (nowMs - t) / 36e5)
  const recency = Math.exp(-ageHours / 12) // half-ish life ~8h
  const magnitude = Math.abs(s.sentiment_score ?? 0)
  const impact = (s.impact_score ?? 0) / 10
  return recency * (0.6 * magnitude + 0.4 * impact)
}

// Drill-down: evidence, classifications, and the signal's own fields exactly as
// the backend produced them (never fabricated).
function SignalDetail({ signal }) {
  return (
    <div className="detail">
      <h3 style={{ marginTop: 0 }}>{signal.company_name} ({signal.ticker || 'unresolved'})</h3>
      <table>
        <tbody>
          <tr><th>Event</th><td>{signal.event_category}</td></tr>
          <tr><th>Sentiment</th><td><SentimentCell v={signal.sentiment_score} /></td></tr>
          <tr><th>Impact</th><td>{signal.impact_score ?? 'null'} / 10</td></tr>
          <tr><th>Impact explanation</th><td>{signal.impact_explanation || '—'}</td></tr>
          <tr><th>Status</th><td>{signal.analysis_status}</td></tr>
          <tr><th>Source</th><td>{signal.source_type} · {signal.source_provider}</td></tr>
          <tr><th>Provenance</th><td><ProvenanceBadge p={signal.provenance} /></td></tr>
          <tr><th>Published</th><td>{signal.published_at || 'null'}</td></tr>
          <tr><th>Method</th><td>{signal.analysis_method_version}</td></tr>
        </tbody>
      </table>
      <div>
        <strong>Quality flags:</strong>{' '}
        {signal.quality_flags.length === 0
          ? <span className="muted">none</span>
          : signal.quality_flags.map((f) => <span className="flag" key={f}>{f}</span>)}
      </div>
      <div>
        <strong>Evidence excerpts:</strong>
        {signal.evidence_excerpts.length === 0 && <p className="muted">none extracted</p>}
        {signal.evidence_excerpts.map((e, i) => (
          <div className="excerpt" key={i}>
            [{[...e.supports].join(', ')}] “{e.text}”
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Signals() {
  const [signals, setSignals] = useState([])
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState(null)
  const [polling, setPolling] = useState(false)
  const [pollResult, setPollResult] = useState(null)
  const [sort, setSort] = useState('hot') // 'hot' | 'newest'

  const load = async () => {
    try {
      setSignals(await getSignals({ limit: 100 }))
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 5000) // poll for new signals
    return () => clearInterval(t)
  }, [])

  const poll = async () => {
    setPolling(true)
    setError(null)
    setPollResult(null)
    try {
      const out = await livePoll()
      setPollResult(out)
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setPolling(false)
    }
  }

  const nowMs = Date.now()
  const ordered = [...signals].sort((a, b) =>
    sort === 'hot' ? hotScore(b, nowMs) - hotScore(a, nowMs) : 0
  )
  const errKeys = pollResult ? Object.keys(pollResult.source_errors || {}) : []

  return (
    <div>
      <div className="panel">
        <h2 style={{ marginTop: 0, fontSize: '1.05rem' }}>Live Ingestion</h2>
        <p className="muted">
          Pulls live news (GDELT), social (StockTwits), and prices (yfinance) — all free sources —
          and runs them through the engine (provenance: live). Use the manual text analyzer in
          Strategy Lab for ad-hoc input.
        </p>
        <button className="action" onClick={poll} disabled={polling} style={{ marginTop: 0 }}>
          {polling ? 'Polling live sources…' : 'Poll live sources now'}
        </button>
        {pollResult && (
          <p className="muted">
            {pollResult.signals.length} new signal(s) · {pollResult.decision_event.consumed_signal_ids.length} consumed
            {errKeys.length > 0 && (
              <> · degraded: {errKeys.join(', ')}</>
            )}
          </p>
        )}
        {error && <div className="error">{error}</div>}
      </div>

      <div className="panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0, fontSize: '1.05rem' }}>Signal Feed</h2>
          <div className="tabs" style={{ margin: 0 }}>
            <button className={sort === 'hot' ? 'active' : ''} onClick={() => setSort('hot')}>Hot</button>
            <button className={sort === 'newest' ? 'active' : ''} onClick={() => setSort('newest')}>Newest</button>
          </div>
        </div>
        <p className="muted">
          {sort === 'hot'
            ? 'Ranked by impact × recency — high-signal items first, not just the newest.'
            : 'Chronological, newest first.'} Polls every 5s.
        </p>
        <table>
          <thead>
            <tr>
              <th>Company</th><th>Sent.</th><th>Impact</th><th>Event</th>
              <th>Provenance</th><th>Flags</th>
            </tr>
          </thead>
          <tbody>
            {ordered.map((s) => (
              <tr key={s.signal_id} className="clickable" onClick={() => setSelected(s)}>
                <td>{s.company_name}</td>
                <td><SentimentCell v={s.sentiment_score} /></td>
                <td>{s.impact_score ?? 'null'}</td>
                <td>{s.event_category}</td>
                <td><ProvenanceBadge p={s.provenance} /></td>
                <td>{s.quality_flags.length ? s.quality_flags.join(', ') : '—'}</td>
              </tr>
            ))}
            {ordered.length === 0 && (
              <tr><td colSpan={6} className="muted">No signals yet — poll live sources or run a replay.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="panel">
          <SignalDetail signal={selected} />
        </div>
      )}
    </div>
  )
}
