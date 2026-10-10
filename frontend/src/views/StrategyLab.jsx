import React, { useEffect, useState } from 'react'
import { getSectors, simulate, ingestItems, getBenchmark } from '../api.js'

function SentimentCell({ v }) {
  if (v === null || v === undefined) return <span className="muted">null</span>
  const cls = v < 0 ? 'neg' : v > 0 ? 'pos' : 'neu'
  return <span className={`sent ${cls}`}>{v.toFixed(2)}</span>
}

// Manual article analyzer: ad-hoc text in, real pipeline signals out. Lives here
// (not in the main feed) so the live feed stays purely source-driven.
function ArticleAnalyzer() {
  const [text, setText] = useState('')
  const [signals, setSignals] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const run = async () => {
    setLoading(true)
    setError(null)
    setSignals(null)
    try {
      const out = await ingestItems({
        source_type: 'news',
        items: [{ id: `ui-${Date.now()}`, text }],
        provenance: 'live',
        sentiment_backend: 'model',
      })
      setSignals(out)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <h3>Article Analyzer</h3>
          <div className="sub">Paste text to see how the real pipeline scores it — each resolved company becomes its own signal</div>
        </div>
        <button className="action" onClick={run} disabled={loading || !text.trim()}>
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="e.g. Apple cut revenue guidance while Microsoft won a cloud contract."
      />
      {error && <div className="error">{error}</div>}
      {signals && signals.length > 0 && (
        <table>
          <thead>
            <tr><th>Company</th><th>Sent.</th><th>Event</th><th>Impact</th></tr>
          </thead>
          <tbody>
            {signals.map((s) => (
              <tr key={s.signal_id}>
                <td>{s.company_name} ({s.ticker || 'unresolved'})</td>
                <td><SentimentCell v={s.sentiment_score} /></td>
                <td>{s.event_category}</td>
                <td>{s.impact_score ?? 'null'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {signals && signals.length === 0 && (
        <p className="muted">No signals produced.</p>
      )}
    </div>
  )
}

// Model vs Lexicon comparison: measured benchmark over the labeled dev fixtures.
// Shows accuracy, confusion matrix, per-class recall, and latency for each
// backend. All numbers are measured live — never hardcoded. Fixtures are
// synthetic dev labels, NOT a real-world accuracy claim.
function BenchmarkPanel() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = async (refresh = false) => {
    setLoading(true)
    setError(null)
    try {
      setData(await getBenchmark(refresh))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const CLASSES = ['-1', '0', '1']
  const LABEL = { '-1': 'neg', '0': 'neu', '1': 'pos' }

  const renderBackend = (name, b, reason) => (
    <div key={name} style={{ flex: 1, minWidth: 260 }}>
      <h4 style={{ margin: '0.4rem 0' }}>{name}</h4>
      {b ? (
        <>
          <table>
            <tbody>
              <tr><th>Accuracy</th><td>{b.accuracy != null ? `${(b.accuracy * 100).toFixed(1)}%` : '— (all abstained)'}</td></tr>
              <tr><th>Scored</th><td>{b.scored} / {b.total}</td></tr>
              <tr><th>Abstentions</th><td>{b.abstain}</td></tr>
              <tr><th>Latency</th><td>{b.latency_ms_per_item} ms/item</td></tr>
            </tbody>
          </table>
          <table>
            <thead>
              <tr><th>gold \\ pred</th>{CLASSES.map((c) => <th key={c}>{LABEL[c]}</th>)}</tr>
            </thead>
            <tbody>
              {CLASSES.map((g) => (
                <tr key={g}>
                  <th>{LABEL[g]}</th>
                  {CLASSES.map((p) => (
                    <td key={p} style={g === p && b.confusion[g][p] > 0 ? { color: '#059669', fontWeight: 600 } : {}}>
                      {b.confusion[g][p]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted">
            recall: {CLASSES.map((c) => `${LABEL[c]} ${b.per_class_recall[c] != null ? `${(b.per_class_recall[c] * 100).toFixed(0)}%` : 'n/a'}`).join(' · ')}
          </p>
        </>
      ) : (
        <p className="muted">{reason || 'unavailable'}</p>
      )}
    </div>
  )

  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <h3>Model vs Lexicon</h3>
          <div className="sub">Measured benchmark over labeled dev fixtures — accuracy, confusion matrix, latency</div>
        </div>
        <button className="ghost" onClick={() => load(true)} disabled={loading}>
          {loading ? 'Running…' : 'Re-run'}
        </button>
      </div>
      {error && <div className="error">{error}</div>}
      {!data && !error && <p className="muted">Loading benchmark…</p>}
      {data && (
        <>
          <p className="muted">
            {data.methodology} Sample: {data.sample_size} fixtures · {data.hardware}.
          </p>
          <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
            {renderBackend('lexicon', data.lexicon)}
            {renderBackend('model', data.model, data.model_unavailable_reason)}
          </div>
        </>
      )}
    </div>
  )
}

// Strategy Lab (Phase 3 shell): a non-persistent what-if simulator. It calls the
// real /rebalance endpoint (real policy logic, no frontend-only formula) but does
// not persist to the ledger, so experiments never mutate demo state.
export default function StrategyLab() {
  const [tickers, setTickers] = useState([])
  const [ticker, setTicker] = useState('AAPL')
  const [sentiment, setSentiment] = useState(-0.5)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [running, setRunning] = useState(false)

  useEffect(() => {
    getSectors().then((s) => setTickers(Object.keys(s))).catch(() => {})
  }, [])

  const runSimulation = async () => {
    setRunning(true)
    setError(null)
    try {
      setResult(
        await simulate({
          items: [
            { ticker, sentiment_score: Number(sentiment), text: 'what-if', source_item_id: `sim-${Date.now()}` },
          ],
        })
      )
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <>
    <div className="page-head">
      <h2>Strategy Lab</h2>
      <p>Experiment safely — ad-hoc text analysis, a read-only what-if simulator, and the model-vs-lexicon benchmark. Nothing here mutates the demo portfolio.</p>
    </div>

    <div className="panel">
      <div className="panel-head">
        <div>
          <h3>What-If Simulator</h3>
          <div className="sub">Real rebalancer logic, non-persistent — caps, gates, and renormalization all apply</div>
        </div>
        <button className="action" onClick={runSimulation} disabled={running}>
          {running ? 'Simulating…' : 'Simulate'}
        </button>
      </div>
      <div className="controls">
        <label>Ticker{' '}
          <select value={ticker} onChange={(e) => setTicker(e.target.value)}>
            {tickers.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        <label>Sentiment{' '}
          <input
            type="range" min="-1" max="1" step="0.05" value={sentiment}
            onChange={(e) => setSentiment(e.target.value)}
          />
          <span className="muted">{Number(sentiment).toFixed(2)}</span>
        </label>
      </div>
      {error && <div className="error">{error}</div>}
      {result && (
        <>
          <table>
            <thead><tr><th>Ticker</th><th className="num">Original</th><th className="num">Final</th><th className="num">Adjustment</th></tr></thead>
            <tbody>
              {Object.keys(result.proposed_weights).map((t) => (
                <tr key={t}>
                  <td>{t}</td>
                  <td className="num">{(result.original_weights[t] * 100).toFixed(2)}%</td>
                  <td className="num">{(result.proposed_weights[t] * 100).toFixed(2)}%</td>
                  <td className={`num ${result.adjustments[t] > 0 ? 'pos' : result.adjustments[t] < 0 ? 'neg' : 'muted'}`}>
                    {result.adjustments[t]
                      ? `${result.adjustments[t] > 0 ? '+' : ''}${(result.adjustments[t] * 100).toFixed(2)} pp`
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted" style={{ marginBottom: 0 }}>{result.disclaimer}</p>
        </>
      )}
    </div>
    <ArticleAnalyzer />
    <BenchmarkPanel />
    </>
  )
}
