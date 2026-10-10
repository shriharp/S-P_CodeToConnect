import React, { useEffect, useState } from 'react'
import { getSectors, rebalancePortfolio } from '../api.js'

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
        await rebalancePortfolio({
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
  )
}
