import React, { useState } from 'react'
import { analyzeText, rebalancePortfolio } from './api.js'

function SignalView() {
  const [text, setText] = useState('')
  const [signal, setSignal] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const run = async () => {
    setLoading(true)
    setError(null)
    setSignal(null)
    try {
      setSignal(
        await analyzeText({
          text,
          source_item_id: `ui-${Date.now()}`,
          source_provider: 'dashboard',
          provenance: 'live',
        })
      )
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste a financial news headline or paragraph..."
      />
      <button className="action" onClick={run} disabled={loading || !text.trim()}>
        {loading ? 'Analyzing...' : 'Analyze'}
      </button>
      {error && <div className="error">{error}</div>}
      {signal && <SignalCard signal={signal} />}
    </div>
  )
}

function SignalCard({ signal }) {
  const fmt = (v) => (v === null || v === undefined ? 'null (unknown)' : v)
  return (
    <div>
      <table>
        <tbody>
          <tr><th>Event</th><td>{signal.event_category}</td></tr>
          <tr><th>Sentiment</th><td>{fmt(signal.sentiment_score)}</td></tr>
          <tr><th>Impact</th><td>{fmt(signal.impact_score)} / 10</td></tr>
          <tr><th>Explanation</th><td>{signal.impact_explanation || '—'}</td></tr>
          <tr><th>Status</th><td>{signal.analysis_status}</td></tr>
          <tr><th>Provenance</th><td>{signal.provenance}</td></tr>
          <tr>
            <th>Quality flags</th>
            <td>
              {signal.quality_flags.length === 0
                ? 'none'
                : signal.quality_flags.map((f) => (
                    <span className="flag" key={f}>{f}</span>
                  ))}
            </td>
          </tr>
        </tbody>
      </table>
      {signal.evidence_excerpts.map((e, i) => (
        <div className="excerpt" key={i}>
          [{[...e.supports].join(', ')}] “{e.text}”
        </div>
      ))}
      <p className="muted">signal_id: {signal.signal_id} · method: {signal.analysis_method_version}</p>
    </div>
  )
}

const DEMO_ITEMS = [
  { ticker: 'AAPL', sentiment_score: -0.8, text: 'Apple faces antitrust lawsuit.', source_item_id: 'demo-1' },
  { ticker: 'MSFT', sentiment_score: 0.6, text: 'Microsoft wins major cloud contract.', source_item_id: 'demo-2' },
  { ticker: 'JPM', sentiment_score: -0.4, text: 'JPMorgan downgraded by analyst.', source_item_id: 'demo-3' },
]

function RebalanceView() {
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const run = async () => {
    setLoading(true)
    setError(null)
    try {
      setResult(await rebalancePortfolio({ items: DEMO_ITEMS }))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel">
      <p className="muted">
        Runs the mock index through three clearly-labeled synthetic signals
        (provenance: synthetic).
      </p>
      <button className="action" onClick={run} disabled={loading}>
        {loading ? 'Rebalancing...' : 'Run demo rebalance'}
      </button>
      {error && <div className="error">{error}</div>}
      {result && <RebalanceCard result={result} />}
    </div>
  )
}

function RebalanceCard({ result }) {
  const pct = (w) => `${(w * 100).toFixed(2)}%`
  return (
    <div>
      <table>
        <thead>
          <tr><th>Ticker</th><th>Proposed weight</th><th>Adjustment</th></tr>
        </thead>
        <tbody>
          {Object.entries(result.proposed_weights).map(([t, w]) => (
            <tr key={t}>
              <td>{t}</td>
              <td>{pct(w)}</td>
              <td>
                {result.adjustments[t] === undefined
                  ? '—'
                  : `${result.adjustments[t] >= 0 ? '+' : ''}${(result.adjustments[t] * 100).toFixed(2)}%`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="muted">
        consumed {result.consumed_signal_ids.length} signal(s)
        {result.skipped.length > 0 && ` · skipped ${result.skipped.length}`}
      </p>
      {result.skipped.map((s) => (
        <p className="muted" key={s.signal_id}>
          skipped {s.signal_id}: {s.reason}
        </p>
      ))}
      <p className="muted">{result.disclaimer}</p>
    </div>
  )
}

export default function App() {
  const [tab, setTab] = useState('signals')
  return (
    <div>
      <h1>Risk Engine Dashboard</h1>
      <div className="tabs">
        <button className={tab === 'signals' ? 'active' : ''} onClick={() => setTab('signals')}>
          Signal analyzer
        </button>
        <button className={tab === 'rebalance' ? 'active' : ''} onClick={() => setTab('rebalance')}>
          Mock rebalance
        </button>
      </div>
      {tab === 'signals' ? <SignalView /> : <RebalanceView />}
    </div>
  )
}
