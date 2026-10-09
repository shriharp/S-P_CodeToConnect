import React, { useState } from 'react'
import { analyzeText, rebalancePortfolio, ingestItems, replayRecording } from './api.js'

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

const DEMO_INGEST = [
  'Acme cut revenue by 8 percent after a factory shutdown at its plant in Ohio.',
  'Globex announced a new product launch with strong guidance.',
].join('\n')

function IngestView() {
  const [sourceType, setSourceType] = useState('news')
  const [lines, setLines] = useState(DEMO_INGEST)
  const [record, setRecord] = useState(false)
  const [signals, setSignals] = useState(null)
  const [replayFile, setReplayFile] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const run = async () => {
    setLoading(true)
    setError(null)
    setSignals(null)
    try {
      const items = lines
        .split('\n')
        .map((t) => t.trim())
        .filter(Boolean)
        .map((text, i) => ({ id: `ui-${Date.now()}-${i}`, text }))
      setSignals(await ingestItems({ source_type: sourceType, items, provenance: 'live', record }))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const doReplay = async () => {
    setLoading(true)
    setError(null)
    setSignals(null)
    try {
      setSignals(await replayRecording({ file: replayFile }))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel">
      <p className="muted">
        Batch-ingest news or social text (one item per line). Each line becomes an
        independent company-specific signal. Recording writes outputs for later
        no-inference replay.
      </p>
      <select value={sourceType} onChange={(e) => setSourceType(e.target.value)}>
        <option value="news">news</option>
        <option value="social">social</option>
      </select>{' '}
      <label className="muted">
        <input type="checkbox" checked={record} onChange={(e) => setRecord(e.target.checked)} />{' '}
        record outputs for replay
      </label>
      <textarea
        value={lines}
        onChange={(e) => setLines(e.target.value)}
        style={{ marginTop: '0.75rem' }}
      />
      <button className="action" onClick={run} disabled={loading || !lines.trim()}>
        {loading ? 'Ingesting...' : 'Ingest batch'}
      </button>
      <div style={{ marginTop: '1rem' }}>
        <input
          value={replayFile}
          onChange={(e) => setReplayFile(e.target.value)}
          placeholder="recording filename (e.g. ingest-20261009T120000Z.jsonl)"
        />{' '}
        <button className="action" onClick={doReplay} disabled={loading || !replayFile.trim()}>
          Replay recording
        </button>
      </div>
      {error && <div className="error">{error}</div>}
      {signals && (
        <table>
          <thead>
            <tr><th>Source</th><th>Event</th><th>Sentiment</th><th>Impact</th><th>Status</th><th>Flags</th></tr>
          </thead>
          <tbody>
            {signals.map((s) => (
              <tr key={s.signal_id}>
                <td>{s.source_type} ({s.provenance})</td>
                <td>{s.event_category}</td>
                <td>{s.sentiment_score ?? 'null'}</td>
                <td>{s.impact_score ?? 'null'}</td>
                <td>{s.analysis_status}</td>
                <td>{s.quality_flags.join(', ') || 'none'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
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
        <button className={tab === 'ingest' ? 'active' : ''} onClick={() => setTab('ingest')}>
          Ingest &amp; replay
        </button>
      </div>
      {tab === 'signals' && <SignalView />}
      {tab === 'rebalance' && <RebalanceView />}
      {tab === 'ingest' && <IngestView />}
    </div>
  )
}
