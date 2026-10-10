import React, { useEffect, useState } from 'react'
import { getLedger, getWeightHistory, getSectors, getPerformance } from '../api.js'
import LineChart from '../components/LineChart.jsx'

const pct = (w) => `${(w * 100).toFixed(2)}%`

export default function Portfolio() {
  const [ledger, setLedger] = useState([])
  const [history, setHistory] = useState([])
  const [sectors, setSectors] = useState({})
  const [perf, setPerf] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    ;(async () => {
      try {
        const [l, h, s, p] = await Promise.all([
          getLedger(50), getWeightHistory(), getSectors(), getPerformance(),
        ])
        setLedger(l)
        setHistory(h)
        setSectors(s)
        setPerf(p)
      } catch (e) {
        setError(e.message)
      }
    })()
  }, [])

  const latest = history.length ? history[history.length - 1] : null
  const initial = history.length ? history[0] : null

  // Aggregate a weights map by sector.
  const bySector = (weights) => {
    if (!weights) return {}
    const acc = {}
    for (const [t, w] of Object.entries(weights)) {
      const sec = sectors[t]?.sector || 'Unknown'
      acc[sec] = (acc[sec] || 0) + w
    }
    return acc
  }

  const sectorStart = bySector(initial?.weights)
  const sectorNow = bySector(latest?.weights)
  const sectorRows = Object.keys(sectorNow)
    .map((sec) => ({
      sector: sec,
      start: sectorStart[sec] || 0,
      now: sectorNow[sec] || 0,
      delta: (sectorNow[sec] || 0) - (sectorStart[sec] || 0),
    }))
    .sort((a, b) => b.now - a.now)
  const maxNow = Math.max(...sectorRows.map((r) => r.now), 0.01)

  return (
    <div>
      {error && <div className="panel error">{error}</div>}

      <div className="panel">
        <h2 style={{ marginTop: 0, fontSize: '1.05rem' }}>Current Holdings</h2>
        <p className="muted">Latest target allocation (proposed mock weights, not executed).</p>
        {latest ? (
          <table>
            <thead>
              <tr><th>Ticker</th><th>Weight</th><th>Since start</th></tr>
            </thead>
            <tbody>
              {Object.entries(latest.weights).sort((a, b) => b[1] - a[1]).map(([t, w]) => {
                const delta = initial ? w - initial.weights[t] : 0
                return (
                  <tr key={t}>
                    <td>{t}</td>
                    <td>{pct(w)}</td>
                    <td className={delta > 1e-6 ? 'pos' : delta < -1e-6 ? 'neg' : 'muted'}>
                      {delta > 1e-6 ? '+' : ''}{(delta * 100).toFixed(2)} pp
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : (
          <p className="muted">No rebalance events yet — run the demo replay from Overview.</p>
        )}
      </div>

      <div className="panel">
        <h2 style={{ marginTop: 0, fontSize: '1.05rem' }}>Sector Exposure Heatmap</h2>
        <p className="muted">
          Aggregated sector weights from the first to the latest rebalance. Bar length =
          current exposure; shading intensifies with concentration. These are target
          allocations, not executed holdings.
        </p>
        {sectorRows.length ? (
          <table>
            <thead>
              <tr><th>Sector</th><th>Start</th><th>Now</th><th>Δ</th><th>Concentration</th></tr>
            </thead>
            <tbody>
              {sectorRows.map((r) => (
                <tr key={r.sector}>
                  <td>{r.sector}</td>
                  <td className="muted">{pct(r.start)}</td>
                  <td>{pct(r.now)}</td>
                  <td className={r.delta > 1e-6 ? 'pos' : r.delta < -1e-6 ? 'neg' : 'muted'}>
                    {r.delta > 1e-6 ? '+' : ''}{(r.delta * 100).toFixed(2)} pp
                  </td>
                  <td style={{ width: '40%' }}>
                    <div className="bar">
                      <div
                        style={{
                          width: `${(r.now / maxNow) * 100}%`,
                          opacity: 0.45 + 0.55 * (r.now / maxNow),
                        }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">No allocation yet.</p>
        )}
      </div>

      {perf && (
        <div className="panel">
          <h2 style={{ marginTop: 0, fontSize: '1.05rem' }}>Performance &amp; Benchmarking</h2>
          <p className="muted">{perf.note}</p>
          {perf.status === 'ok' ? (
            <>
              <div className="kpis">
                <div className="kpi"><div className="kpi-label">Window</div><div className="kpi-value">{perf.metrics.window_days}d</div></div>
                <div className="kpi"><div className="kpi-label">Final index</div><div className="kpi-value">{perf.metrics.final_index}</div></div>
                <div className="kpi"><div className="kpi-label">Max drawdown</div><div className="kpi-value">{perf.metrics.max_drawdown_pct}%</div></div>
                <div className="kpi"><div className="kpi-label">Avg turnover</div><div className="kpi-value">{perf.metrics.turnover_pct ?? '—'}%</div></div>
              </div>
              <LineChart
                labels={perf.baselines.dates.map((d) => d.slice(5))}
                series={[
                  { name: 'strategy', values: perf.baselines.strategy },
                  ...(perf.baselines.equal_weight
                    ? [{ name: 'equal-weight', values: perf.baselines.equal_weight }]
                    : []),
                  ...(perf.baselines.buy_and_hold
                    ? [{ name: 'buy-and-hold', values: perf.baselines.buy_and_hold }]
                    : []),
                ]}
                height={200}
              />
            </>
          ) : (
            <p className="muted">{perf.note}</p>
          )}
        </div>
      )}

      <div className="panel">
        <h2 style={{ marginTop: 0, fontSize: '1.05rem' }}>Decision Ledger</h2>
        <p className="muted">
          Auditable record of every rebalance: per-signal decision, reason, and final weight.
        </p>
        {ledger.length ? (
          ledger.map((ev) => (
            <div key={ev.event_id} className="ledger-event">
              <div className="ledger-head">
                <strong>{ev.event_id}</strong>
                <span className="muted">{ev.timestamp}</span>
                <span className="muted">policy {ev.policy_version}</span>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>Ticker</th><th>Decision</th><th>Reason</th>
                    <th>Before</th><th>After</th><th>Δ</th>
                  </tr>
                </thead>
                <tbody>
                  {ev.decisions.map((d, i) => {
                    const before = d.original_weight
                    const after = d.final_weight
                    const delta =
                      before != null && after != null ? after - before : null
                    return (
                      <tr key={i}>
                        <td>{d.ticker || '—'}</td>
                        <td><span className={`dec dec-${d.decision}`}>{d.decision}</span></td>
                        <td className="muted">{d.reason || '—'}</td>
                        <td>{before == null ? '—' : pct(before)}</td>
                        <td>{after == null ? '—' : pct(after)}</td>
                        <td className={delta > 1e-9 ? 'pos' : delta < -1e-9 ? 'neg' : 'muted'}>
                          {delta == null ? '—' : `${delta > 0 ? '+' : ''}${(delta * 100).toFixed(2)} pp`}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ))
        ) : (
          <p className="muted">Ledger empty.</p>
        )}
      </div>
    </div>
  )
}
