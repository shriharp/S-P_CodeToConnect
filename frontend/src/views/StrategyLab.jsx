import React, { useEffect, useState } from 'react'
import { getSectors, simulate, ingestItems } from '../api.js'

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
      <h2 style={{ marginTop: 0, fontSize: '1.05rem' }}>Article Analyzer</h2>
      <p className="muted">
        Paste a headline or paragraph to see how the real pipeline scores it. Each resolved
        company becomes its own signal. This is a manual sandbox — the main Signals feed is
        fed by live source polling instead.
      </p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="e.g. Apple cut revenue guidance while Microsoft won a cloud contract."
      />
      <button className="action" onClick={run} disabled={loading || !text.trim()}>
        {loading ? 'Analyzing…' : 'Analyze'}
      </button>
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

  const simulate = async () => {
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
    <div className="panel">
      <h2 style={{ marginTop: 0, fontSize: '1.05rem' }}>What-If Simulator</h2>
      <p className="muted">
        Inject a hypothetical signal and watch the real rebalancer respond. Non-persistent:
        this never mutates the demo portfolio. Impact is display-only — adjustments are sized
        by sentiment, capped, and renormalized to 100%.
      </p>
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
        <button className="action" onClick={simulate} disabled={running} style={{ marginTop: 0 }}>
          {running ? 'Simulating…' : 'Simulate'}
        </button>
      </div>
      {error && <div className="error">{error}</div>}
      {result && (
        <>
          <table>
            <thead><tr><th>Ticker</th><th>Original</th><th>Final</th><th>Adjustment</th></tr></thead>
            <tbody>
              {Object.keys(result.proposed_weights).map((t) => (
                <tr key={t}>
                  <td>{t}</td>
                  <td>{(result.original_weights[t] * 100).toFixed(2)}%</td>
                  <td>{(result.proposed_weights[t] * 100).toFixed(2)}%</td>
                  <td className={result.adjustments[t] > 0 ? 'pos' : result.adjustments[t] < 0 ? 'neg' : 'muted'}>
                    {result.adjustments[t]
                      ? `${result.adjustments[t] > 0 ? '+' : ''}${(result.adjustments[t] * 100).toFixed(2)} pp`
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted">{result.disclaimer}</p>
        </>
      )}
    </div>
    <ArticleAnalyzer />
    </>
  )
}
