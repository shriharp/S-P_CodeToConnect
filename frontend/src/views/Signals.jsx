import React, { useEffect, useState } from 'react'
import { getSignals, livePoll, getSignalsOverview, runDemoReplay } from '../api.js'
import { CategoryCell, FlagList } from '../components/display.jsx'
import Pagination, { usePagination } from '../components/Pagination.jsx'

const PAGE_SIZE = 12

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
function SignalDetail({ signal, onClose }) {
  return (
    <div className="panel detail">
      <div className="panel-head">
        <div>
          <h3>{signal.company_name} ({signal.ticker || 'unresolved'})</h3>
          <div className="sub">
            <ProvenanceBadge p={signal.provenance} /> | {signal.source_type} | {signal.source_provider}
          </div>
        </div>
        <button className="ghost" onClick={onClose}>Close</button>
      </div>
      <div className="grid-2">
        <table>
          <tbody>
            <tr><th>Event</th><td><CategoryCell signal={signal} /></td></tr>
            <tr><th>Sentiment</th><td><SentimentCell v={signal.sentiment_score} /></td></tr>
            <tr><th>Impact</th><td>{signal.impact_score ?? 'null'} / 10</td></tr>
            <tr><th>Status</th><td>{signal.analysis_status}</td></tr>
            <tr><th>Published</th><td>{signal.published_at || 'null'}</td></tr>
            <tr><th>Method</th><td className="mono">{signal.analysis_method_version}</td></tr>
          </tbody>
        </table>
        <div>
          <div style={{ marginBottom: '0.6rem' }}>
            <strong style={{ fontSize: '0.8rem' }}>Quality flags</strong>
            <div style={{ marginTop: '0.25rem' }}><FlagList flags={signal.quality_flags} /></div>
          </div>
          <div>
            <strong style={{ fontSize: '0.8rem' }}>Source link</strong>
            <div style={{ marginTop: '0.25rem' }}>
              {signal.source_url
                ? <a href={signal.source_url} target="_blank" rel="noreferrer">Open original</a>
                : <span className="muted">none</span>}
            </div>
          </div>
        </div>
      </div>
      {signal.impact_explanation && (
        <p className="muted" style={{ marginTop: '0.75rem' }}>
          <strong>Impact:</strong> {signal.impact_explanation}
        </p>
      )}
      <div style={{ marginTop: '0.6rem' }}>
        <strong style={{ fontSize: '0.8rem' }}>Evidence excerpts</strong>
        {signal.evidence_excerpts.length === 0 && <p className="muted">none extracted</p>}
        {signal.evidence_excerpts.map((e, i) => (
          <div className="excerpt" key={i}>
            <span className="sup">{[...e.supports].join(', ')}</span>"{e.text}"
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Signals({ demoMode = false }) {
  const [signals, setSignals] = useState([])
  const [overview, setOverview] = useState(null)
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState(null)
  const [polling, setPolling] = useState(false)
  const [pollResult, setPollResult] = useState(null)
  const [sort, setSort] = useState('hot') // 'hot' | 'newest'

  const load = async () => {
    try {
      const [sigs, ov] = await Promise.all([
        getSignals({ limit: 200, dashboard: demoMode ? 'demo' : 'live' }),
        getSignalsOverview(demoMode ? 'demo' : 'live'),
      ])
      setSignals(sigs)
      setOverview(ov)
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
    if (demoMode) {
      loadDemo()
    }
    const t = setInterval(load, 10000) // poll for new signals
    const liveRefresh = demoMode ? null : setInterval(poll, 90000)
    let events
    if (!demoMode) {
      events = new EventSource('/api/live/events')
      events.addEventListener('poll', (event) => {
        try {
          const update = JSON.parse(event.data)
          setPollResult(update)
          load()
        } catch {
          setError('Received an invalid live-ingestion update.')
        }
      })
      events.onerror = () => {
        // EventSource reconnects automatically; REST refresh remains the fallback.
      }
    }
    return () => {
      clearInterval(t)
      if (liveRefresh) clearInterval(liveRefresh)
      if (events) events.close()
    }
  }, [demoMode])

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

  const loadDemo = async () => {
    setError(null)
    try {
      await runDemoReplay()
      await load()
    } catch (e) {
      setError(e.message)
    }
  }

  const nowMs = Date.now()
  const ordered = [...signals].sort((a, b) =>
    sort === 'hot' ? hotScore(b, nowMs) - hotScore(a, nowMs) : 0
  )
  const { slice, page, setPage, total, pageSize } = usePagination(ordered, PAGE_SIZE)
  const errKeys = pollResult ? Object.keys(pollResult.source_errors || {}) : []

  return (
    <div>
      <div className="page-head">
        <h2>Signals</h2>
        <p>Live-ingested news and social signals, analyzed and scored. Click a row to inspect its evidence.</p>
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h3>Live Ingestion</h3>
            <div className="sub">{demoMode ? 'Curated 40-item replay corpus with complete timestamps and evidence' : 'GDELT news, StockTwits social, Reddit RSS, and yfinance prices'}</div>
          </div>
          <button className="action" onClick={demoMode ? loadDemo : poll} disabled={polling}>
            {demoMode ? 'Load demo corpus' : (polling ? 'Polling...' : 'Poll live sources')}
          </button>
        </div>
        {polling && (
          <div className="ingestion-progress" role="status" aria-live="polite">
            <div className="progress-track"><div className="progress-indeterminate" /></div>
            <span>Fetching news, social posts, Reddit RSS, and market prices. This can take up to a minute because providers enforce rate limits.</span>
          </div>
        )}
        {pollResult && (
          <div className="ingestion-summary">
            <strong>Latest live poll</strong>
            <span>{pollResult.signals.length} new signals analyzed</span>
            <span>{pollResult.decision_event.consumed_signal_ids.length} signals used for allocation</span>
            {pollResult.source_counts?.fetched?.reddit != null && (
              <span>Reddit RSS: {pollResult.source_counts.fetched.reddit} fetched, {pollResult.source_counts.analyzed.reddit} analyzed, {pollResult.skipped_seen} already seen</span>
            )}
            {errKeys.length > 0 && <span className="ingestion-warning">Unavailable or rate-limited: {errKeys.join(', ')}</span>}
          </div>
        )}
        {error && <div className="error">{error}</div>}
      </div>

      {overview && overview.total > 0 && (
        <div className="panel">
          <div className="panel-head">
            <div>
              <h3>Market Risk Overview</h3>
              <div className="sub">Descriptive distributions over {overview.total} stored signals. Nulls counted, never imputed.</div>
            </div>
          </div>
          <div className="kpis">
            <div className="kpi"><div className="kpi-label">Signals</div><div className="kpi-value">{overview.total}</div></div>
            <div className="kpi"><div className="kpi-label">Mean sentiment</div><div className="kpi-value">{overview.sentiment.mean ?? 'n/a'}</div></div>
            <div className="kpi"><div className="kpi-label">Mean impact</div><div className="kpi-value">{overview.impact.mean ?? 'n/a'}</div></div>
            <div className="kpi"><div className="kpi-label">Sentiment null</div><div className="kpi-value">{overview.sentiment.null}</div></div>
            <div className="kpi"><div className="kpi-label">Impact null</div><div className="kpi-value">{overview.impact.null}</div></div>
          </div>
          <table>
            <thead><tr><th>Event category</th><th className="num">Count</th><th></th></tr></thead>
            <tbody>
              {Object.entries(overview.event_counts).map(([cat, n]) => (
                <tr key={cat}>
                  <td>{cat}</td>
                  <td className="num">{n}</td>
                  <td style={{ width: '45%' }}>
                    <div className="bar"><div style={{ width: `${(n / overview.total) * 100}%` }} /></div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted" style={{ marginBottom: 0 }}>
            Sentiment split: {overview.sentiment.positive} positive · {overview.sentiment.neutral} neutral ·{' '}
            {overview.sentiment.negative} negative (of {overview.sentiment.scored} scored).
          </p>
        </div>
      )}

      <div className="panel">
        <div className="panel-head">
          <div>
            <h3>Signal Feed</h3>
            <div className="sub">
              {sort === 'hot'
                ? 'Ranked by impact and recency. High-signal items first.'
                : 'Chronological, newest first.'} Polls every 10s.
            </div>
          </div>
          <div className="seg">
            <button className={sort === 'hot' ? 'active' : ''} onClick={() => { setSort('hot'); setPage(1) }}>Hot</button>
            <button className={sort === 'newest' ? 'active' : ''} onClick={() => { setSort('newest'); setPage(1) }}>Newest</button>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Company</th><th className="num">Sent.</th><th className="num">Impact</th>
              <th>Event</th><th>Provenance</th><th>Flags</th>
            </tr>
          </thead>
          <tbody>
            {slice.map((s) => (
              <tr key={s.signal_id} className="clickable" onClick={() => setSelected(s)}>
                <td>{s.company_name}</td>
                <td className="num"><SentimentCell v={s.sentiment_score} /></td>
                <td className="num">{s.impact_score ?? 'n/a'}</td>
                <td><CategoryCell signal={s} /></td>
                <td><ProvenanceBadge p={s.provenance} /></td>
                <td><FlagList flags={s.quality_flags} /></td>
              </tr>
            ))}
            {ordered.length === 0 && (
              <tr><td colSpan={6}><div className="empty">No signals yet. Poll live sources or load the demo corpus.</div></td></tr>
            )}
          </tbody>
        </table>
        <Pagination page={page} pageSize={pageSize} total={total} onChange={setPage} />
      </div>

      {selected && <SignalDetail signal={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
