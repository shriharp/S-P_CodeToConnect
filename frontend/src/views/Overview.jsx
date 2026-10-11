import React, { useEffect, useState } from 'react'
import LineChart from '../components/LineChart.jsx'
import { getWeightHistory, getPrices, getLedger, getSignals } from '../api.js'

// Overview / Command Center: portfolio KPIs, the Weight Evolution Timeline,
// and a horizontal scrubber to step through rebalance events. Dragging the
// scrubber moves through time; the panel below shows ONLY the active step's
// justification (which signal moved which weight and why).
export default function Overview({ demoMode = false }) {
  const [history, setHistory] = useState([])
  const [prices, setPrices] = useState({})
  const [steps, setSteps] = useState([]) // ledger events + causes, oldest first
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(['AAPL'])
  const [weightSelected, setWeightSelected] = useState([])
  const [hoveredWeight, setHoveredWeight] = useState(null)
  const [activeIdx, setActiveIdx] = useState(0)

  const load = async () => {
    try {
      const [h, p, led, sigs] = await Promise.all([
        getWeightHistory(demoMode ? 'demo' : 'live'),
        getPrices(selected.join(',')),
        getLedger(500, demoMode ? 'demo' : 'live'),
        getSignals({ limit: 300, dashboard: demoMode ? 'demo' : 'live' }),
      ])
      const uniqueHistory = [...new Map(h.map((event) => [event.event_id, event])).values()]
      setHistory(uniqueHistory)
      setWeightSelected((current) => current.filter((ticker) => h[0]?.weights?.[ticker] != null))
      setPrices(p)

      // Join each ledger event's decisions to their source signals so we can
      // show "headline -> weight move" causality per step.
      const byId = new Map(sigs.map((s) => [s.signal_id, s]))
      const uniqueLedger = [...new Map(led.map((event) => [event.event_id, event])).values()]
      const chron = [...uniqueLedger].reverse() // oldest first
      setSteps(
        chron.map((ev) => ({
          ...ev,
          causes: ev.decisions
            .filter((d) => d.original_weight != null && d.final_weight != null)
            .map((d, decisionIndex) => {
              const s = byId.get(d.signal_id) || {}
              const delta = d.final_weight - d.original_weight
              return {
                key: `${ev.event_id}-${d.signal_id}-${decisionIndex}`,
                ticker: d.ticker,
                decision: d.decision,
                delta,
                original: d.original_weight,
                final: d.final_weight,
                sentiment: s.sentiment_score,
                headline: s.event_summary || s.evidence_excerpts?.[0]?.text || '',
              }
            })
            .filter((c) => Math.abs(c.delta) > 1e-9),
        }))
      )
      setActiveIdx(0)
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => { load() }, [selected, demoMode]) // eslint-disable-line react-hooks/exhaustive-deps

  const stepCount = history.length
  const idx = Math.min(activeIdx, Math.max(0, stepCount - 1))
  const activeHistory = history[idx] || null
  const activeStep = activeHistory
    ? steps.find((step) => step.event_id === activeHistory.event_id) || null
    : null

  // Full trajectory always shown; the scrubber just picks which step to inspect.
  const tickers = history.length ? Object.keys(history[0].weights) : []
  const labels = history.map((h) => h.timestamp.slice(5, 16).replace('T', ' '))
  const plottedTickers = weightSelected.length ? weightSelected : tickers
  const weightSeries = plottedTickers.map((t) => ({
    name: t,
    values: history.map((h) => (h.weights[t] ?? 0) * 100),
  }))

  // Price overlay: indexed to 100 at first point so it shares the weight axis.
  const priceDates = [...new Set(selected.flatMap((ticker) => Object.keys(prices[ticker] || {})))].sort()
  const priceSeries = selected.flatMap((ticker) => {
    const series = prices[ticker]
    if (!series || !priceDates.length) return []
    const first = Object.values(series)[0]
    if (!first) return []
    return [{
      name: `${ticker} price (idx)`,
      values: priceDates.map((date) => (series[date] == null ? null : (series[date] / first) * 100)),
    }]
  })

  const topWeights = activeHistory
    ? Object.entries(activeHistory.weights).sort((a, b) => b[1] - a[1]).slice(0, 3)
    : []

  return (
    <div>
      <div className="page-head">
        <h2>Overview</h2>
        <p>Portfolio weight evolution across rebalance events. Scrub through time to see what moved, and why.</p>
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h3>Weight Evolution Timeline</h3>
            <div className="sub">
              {stepCount} rebalance event(s) · proposed mock weights, not executed holdings
            </div>
          </div>
        </div>
        {error && <div className="error">{error}</div>}

        {stepCount === 0 && (
          <div className="empty">No rebalance events yet. Enable Demo mode to populate the timeline.</div>
        )}

        {stepCount > 0 && (
          <>
            <div className="kpis">
              {topWeights.map(([t, w]) => (
                <div className="kpi" key={t}>
                  <div className="kpi-label">{t}</div>
                  <div className="kpi-value">{(w * 100).toFixed(1)}%</div>
                </div>
              ))}
              <div className="kpi">
                <div className="kpi-label">Step</div>
                <div className="kpi-value">{idx + 1}<span className="faint">/{stepCount}</span></div>
              </div>
            </div>

            <div className="ticker-picker" aria-label="Weight timeline stocks">
              <span className="muted">Plot stocks</span>
              {tickers.map((ticker) => (
                <button
                  key={ticker}
                  className={`ticker-chip ${plottedTickers.includes(ticker) ? 'active' : ''}`}
                  onClick={() => setWeightSelected((current) => {
                    const active = current.length ? current : tickers
                    if (active.includes(ticker) && active.length === 1) return active
                    return active.includes(ticker)
                      ? active.filter((item) => item !== ticker)
                      : [...active, ticker]
                  })}
                >
                  {ticker}
                </button>
              ))}
            </div>
            <LineChart
              labels={labels}
              series={weightSeries}
              activeIndex={idx}
              hoveredName={hoveredWeight}
              onHover={setHoveredWeight}
              yFormat={(v) => `${v.toFixed(0)}%`}
            />

            {/* Horizontal scrubber through rebalance events. */}
            <div className="scrubber">
              <div className="scrubber-row">
                <div className="step-nav">
                  <button onClick={() => setActiveIdx(Math.max(0, idx - 1))} disabled={idx <= 0} aria-label="Previous step">‹</button>
                </div>
                <input
                  type="range"
                  min={0}
                  max={stepCount - 1}
                  value={idx}
                  onChange={(e) => setActiveIdx(Number(e.target.value))}
                  aria-label="Rebalance step"
                />
                <div className="step-nav">
                  <button onClick={() => setActiveIdx(Math.min(stepCount - 1, idx + 1))} disabled={idx >= stepCount - 1} aria-label="Next step">›</button>
                </div>
              </div>
              <div className="scrubber-ticks">
                <span className="scrubber-tick">{history[0].timestamp.slice(5, 10)}</span>
                <span className="scrubber-tick active">
                  {history[idx].timestamp.slice(0, 16).replace('T', ' ')}
                </span>
                <span className="scrubber-tick">{history[stepCount - 1].timestamp.slice(5, 10)}</span>
              </div>
            </div>

            {/* Show only the active step justification. */}
            <div className="step-detail">
              <div className="ts">Step {idx + 1} · {activeStep?.timestamp?.slice(0, 16).replace('T', ' ') || history[idx].timestamp.slice(0, 16).replace('T', ' ')}</div>
              {activeStep && activeStep.causes.length > 0 ? (
                activeStep.causes.filter((c) => c.decision !== 'skipped').map((c) => (
                  <div className="cause" key={c.key}>
                    <span className={c.delta > 0 ? 'pos' : 'neg'}>
                      {c.ticker} {(c.original * 100).toFixed(1)}% to {(c.final * 100).toFixed(1)}%
                    </span>
                    <span className={`dec dec-${c.decision}`}>{c.decision}</span>
                    {c.sentiment != null && (
                      <span className="muted">sent {c.sentiment > 0 ? '+' : ''}{c.sentiment.toFixed(2)}</span>
                    )}
                    {c.headline && <span className="cause-headline">"{c.headline}"</span>}
                  </div>
                ))
              ) : (
                <p className="muted" style={{ margin: 0 }}>
                  No weight change at this step. All signals were skipped by policy gates.
                </p>
              )}
            </div>
          </>
        )}
      </div>

      {stepCount > 0 && (
        <div className="panel">
          <div className="panel-head">
            <div>
              <h3>Price Overlay</h3>
              <div className="sub">
                Real yfinance close prices, indexed to 100. Context only. Weight changes are
                sentiment-driven targets, not market drift.
              </div>
            </div>
            <div className="ticker-picker" role="group" aria-label="Select price series">
              {tickers.map((ticker) => (
                <button
                  key={ticker}
                  className={`ticker-chip ${selected.includes(ticker) ? 'active' : ''}`}
                  onClick={() => setSelected((current) => current.includes(ticker)
                    ? (current.length === 1 ? current : current.filter((t) => t !== ticker))
                    : [...current, ticker])}
                >
                  {ticker}
                </button>
              ))}
            </div>
          </div>
          {priceSeries.length > 0 && (
            <LineChart
              labels={priceDates.map((d) => d.slice(5))}
              series={priceSeries}
              height={150}
            />
          )}
        </div>
      )}
    </div>
  )
}
