import React, { useEffect, useState } from 'react'
import LineChart from '../components/LineChart.jsx'
import { getWeightHistory, getPrices, runDemoReplay, getSectors } from '../api.js'

// Overview / Command Center: portfolio KPIs, Weight Evolution Timeline with
// real price overlay, and a one-click deterministic demo replay. This is the
// primary demo screen.
export default function Overview() {
  const [history, setHistory] = useState([])
  const [prices, setPrices] = useState({})
  const [error, setError] = useState(null)
  const [running, setRunning] = useState(false)
  const [selected, setSelected] = useState('AAPL')

  const load = async () => {
    try {
      const [h, p] = await Promise.all([getWeightHistory(), getPrices(selected)])
      setHistory(h)
      setPrices(p)
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected])

  const runReplay = async () => {
    setRunning(true)
    setError(null)
    try {
      await runDemoReplay()
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  // Weight series: one line per ticker across rebalance events.
  const tickers = history.length ? Object.keys(history[0].weights) : []
  const labels = history.map((h) => h.timestamp.slice(5, 16).replace('T', ' '))
  const weightSeries = tickers.map((t) => ({
    name: t,
    values: history.map((h) => (h.weights[t] ?? 0) * 100),
  }))

  // Price overlay: indexed to 100 at first point so it shares the weight axis.
  const priceSeries = (() => {
    const series = prices[selected]
    if (!series) return []
    const dates = Object.keys(series).sort()
    const base = series[dates[0]]
    return [
      {
        name: `${selected} price (idx)`,
        values: dates.map((d) => (series[d] / base) * 100),
      },
    ]
  })()

  const latest = history.length ? history[history.length - 1] : null
  const kpis = latest
    ? Object.entries(latest.weights).sort((a, b) => b[1] - a[1]).slice(0, 3)
    : []

  return (
    <div>
      <div className="panel">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0, fontSize: '1.05rem' }}>Weight Evolution Timeline</h2>
          <button className="action" onClick={runReplay} disabled={running} style={{ marginTop: 0 }}>
            {running ? 'Replaying…' : 'Run deterministic demo replay'}
          </button>
        </div>
        <p className="muted">
          Target allocation decisions across rebalance events. These are proposed mock weights,
          not executed holdings. {history.length} rebalance event(s) recorded.
        </p>
        {error && <div className="error">{error}</div>}

        <div className="kpis">
          {kpis.map(([t, w]) => (
            <div className="kpi" key={t}>
              <div className="kpi-label">{t}</div>
              <div className="kpi-value">{(w * 100).toFixed(1)}%</div>
            </div>
          ))}
          <div className="kpi">
            <div className="kpi-label">Events</div>
            <div className="kpi-value">{history.length}</div>
          </div>
        </div>

        {history.length > 0 && (
          <LineChart labels={labels} series={weightSeries} yFormat={(v) => `${v.toFixed(0)}%`} />
        )}

        <div style={{ marginTop: '1rem' }}>
          <label className="muted">
            Price overlay (indexed to 100):{' '}
            <select value={selected} onChange={(e) => setSelected(e.target.value)}>
              {tickers.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>
          <p className="muted">
            Real yfinance close prices (committed /data), indexed to 100. Shown for context —
            weight changes are sentiment-driven target decisions, not market drift.
          </p>
          {priceSeries.length > 0 && (
            <LineChart
              labels={Object.keys(prices[selected] || {}).sort().map((d) => d.slice(5))}
              series={priceSeries}
              height={160}
            />
          )}
        </div>
      </div>
    </div>
  )
}
