import React, { useEffect, useState } from 'react'
import { getSectors, simulateText } from '../api.js'
import { ModeBadge } from '../components/display.jsx'

const pct = (value) => `${(value * 100).toFixed(2)}%`

function SentimentCell({ value }) {
  if (value === null || value === undefined) return <span className="muted">unknown</span>
  const cls = value < 0 ? 'neg' : value > 0 ? 'pos' : 'neu'
  return <span className={`sent ${cls}`}>{value.toFixed(2)}</span>
}

export default function StrategyLab() {
  const [tickers, setTickers] = useState([])
  const [text, setText] = useState('')
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [running, setRunning] = useState(false)
  const examples = [
    ['Apple guidance cut', 'Apple cuts revenue guidance after weaker-than-expected demand.'],
    ['Multi-company scenario', 'Apple cuts revenue guidance while Microsoft wins a major cloud contract.'],
    ['Energy disruption', 'ExxonMobil faces a supply disruption that could reduce quarterly production.'],
  ]

  useEffect(() => {
    getSectors().then((sectors) => setTickers(Object.keys(sectors))).catch(() => {})
  }, [])

  const runSimulation = async () => {
    setRunning(true)
    setError(null)
    try {
      setData(await simulateText({
        text,
        source_item_id: `strategy-${Date.now()}`,
        source_type: 'news',
        provenance: 'live',
      }))
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  const result = data?.result
  return (
    <>
      <div className="page-head">
        <div className="title-row"><h2>Strategy Lab</h2><span className="mode-badge mode-readonly">READ-ONLY COUNTERFACTUAL</span></div>
        <p>Turn a news scenario into company-specific signals and a read-only portfolio counterfactual. Nothing here mutates the live feed or decision ledger.</p>
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h3>What-If Simulator</h3>
            <div className="sub">One workflow: analyze text, resolve every affected company, then apply the real Module A policy to the combined scenario.</div>
          </div>
          <button className="action" onClick={runSimulation} disabled={running || !text.trim()}>
            {running ? 'Analyzing…' : 'Run what-if'}
          </button>
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Example: Apple cut revenue guidance while Microsoft won a cloud contract."
          aria-label="What-if scenario text"
        />
        <div className="example-row">
          <span className="muted">Load example:</span>
          {examples.map(([label, value]) => <button className="ghost" key={label} onClick={() => setText(value)}>{label}</button>)}
        </div>
        <div className="pipeline-steps">
          <span>1. Interpret text</span><span>2. Resolve companies and signals</span><span>3. Apply allocation policy</span>
        </div>
        <p className="muted">Use real or hypothetical text. Results are a mock allocation, not an investment prediction.</p>
        {error && <div className="error">{error}</div>}

        {data && (
          <>
            <h4>Interpreted signals</h4>
            {data.signals.length ? (
              <table>
                <thead><tr><th>Company</th><th>Sentiment</th><th>Event</th><th>Impact</th><th>Quality</th></tr></thead>
                <tbody>
                  {data.signals.map((signal) => (
                    <tr key={signal.signal_id}>
                      <td>{signal.company_name} <span className="muted">{signal.ticker || 'unresolved'}</span></td>
                      <td><SentimentCell value={signal.sentiment_score} /></td>
                      <td>{signal.event_category}</td>
                      <td>{signal.impact_score ?? 'unknown'}</td>
                      <td>{signal.quality_flags?.length ? signal.quality_flags.join(', ') : 'clear'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p className="muted">No company-specific signals were resolved.</p>}

            <h4>Counterfactual allocation</h4>
            {result && (
              <table>
                <thead><tr><th>Ticker</th><th className="num">Original</th><th className="num">Scenario</th><th className="num">Adjustment</th></tr></thead>
                <tbody>
                  {tickers.map((ticker) => {
                    const delta = result.adjustments[ticker] || 0
                    return (
                      <tr key={ticker}>
                        <td>{ticker}</td>
                        <td className="num">{pct(result.original_weights[ticker])}</td>
                        <td className="num">{pct(result.proposed_weights[ticker])}</td>
                        <td className={`num ${delta > 0 ? 'pos' : delta < 0 ? 'neg' : 'muted'}`}>
                          {delta ? `${delta > 0 ? '+' : ''}${pct(delta)} pp` : 'n/a'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
            {result && <p className="muted" style={{ marginBottom: 0 }}>{result.disclaimer}</p>}
          </>
        )}
      </div>
    </>
  )
}
