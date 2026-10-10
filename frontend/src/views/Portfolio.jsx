import React, { useEffect, useState } from 'react'
import { getLedger, getWeightHistory, getSectors, getPerformance } from '../api.js'
import LineChart from '../components/LineChart.jsx'
import Pagination, { usePagination } from '../components/Pagination.jsx'

const pct = (w) => `${(w * 100).toFixed(2)}%`
const LEDGER_PAGE_SIZE = 4

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
          getLedger(200), getWeightHistory(), getSectors(), getPerformance(),
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

  // Ledger is newest-first; paginate it.
  const { slice: ledgerPage, page, setPage, total, pageSize } = usePagination(ledger, LEDGER_PAGE_SIZE)

  return (
    <div>
      <div className="page-head">
        <h2>Portfolio</h2>
        <p>Current mock allocation, sector exposure, descriptive performance, and the auditable decision ledger.</p>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="grid-2">
        <div className="panel">
          <div className="panel-head">
            <div>
              <h3>Current Holdings</h3>
              <div className="sub">Latest target allocation — proposed mock weights, not executed</div>
            </div>
          </div>
          {latest ? (
            <table>
              <thead><tr><th>Ticker</th><th className="num">Weight</th><th className="num">Since start</th></tr></thead>
              <tbody>
                {Object.entries(latest.weights).sort((a, b) => b[1] - a[1]).map(([t, w]) => {
                  const delta = initial ? w - initial.weights[t] : 0
                  return (
                    <tr key={t}>
                      <td>{t}</td>
                      <td className="num">{pct(w)}</td>
                      <td className={`num ${delta > 1e-6 ? 'pos' : delta < -1e-6 ? 'neg' : 'muted'}`}>
                        {delta > 1e-6 ? '+' : ''}{(delta * 100).toFixed(2)} pp
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          ) : (
            <div className="empty">No rebalance events yet — run the demo replay from Overview.</div>
          )}
        </div>

        <div className="panel">
          <div className="panel-head">
            <div>
              <h3>Sector Exposure</h3>
              <div className="sub">First → latest rebalance. Bar length = exposure, shading = concentration. Target allocations.</div>
            </div>
          </div>
          {sectorRows.length ? (
            <table>
              <thead><tr><th>Sector</th><th className="num">Start</th><th className="num">Now</th><th className="num">Δ</th><th></th></tr></thead>
              <tbody>
                {sectorRows.map((r) => (
                  <tr key={r.sector}>
                    <td>{r.sector}</td>
                    <td className="num muted">{pct(r.start)}</td>
                    <td className="num">{pct(r.now)}</td>
                    <td className={`num ${r.delta > 1e-6 ? 'pos' : r.delta < -1e-6 ? 'neg' : 'muted'}`}>
                      {r.delta > 1e-6 ? '+' : ''}{(r.delta * 100).toFixed(2)} pp
                    </td>
                    <td style={{ width: '35%' }}>
                      <div className="bar">
                        <div style={{ width: `${(r.now / maxNow) * 100}%`, opacity: 0.45 + 0.55 * (r.now / maxNow) }} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty">No allocation yet.</div>
          )}
        </div>
      </div>

      {perf && (
        <div className="panel">
          <div className="panel-head">
            <div>
              <h3>Performance &amp; Benchmarking</h3>
              <div className="sub">{perf.note}</div>
            </div>
          </div>
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
                  ...(perf.baselines.equal_weight ? [{ name: 'equal-weight', values: perf.baselines.equal_weight }] : []),
                  ...(perf.baselines.buy_and_hold ? [{ name: 'buy-and-hold', values: perf.baselines.buy_and_hold }] : []),
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
        <div className="panel-head">
          <div>
            <h3>Decision Ledger</h3>
            <div className="sub">Auditable record of every rebalance — decision, reason, and before → after weight</div>
          </div>
        </div>
        {ledger.length ? (
          ledgerPage.map((ev) => (
            <div key={ev.event_id} className="ledger-event">
              <div className="ledger-head">
                <strong className="mono">{ev.event_id}</strong>
                <span className="muted">{ev.timestamp?.slice(0, 16).replace('T', ' ')}</span>
                <span className="faint">policy {ev.policy_version}</span>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>Ticker</th><th>Decision</th><th>Reason</th>
                    <th className="num">Before</th><th className="num">After</th><th className="num">Δ</th>
                  </tr>
                </thead>
                <tbody>
                  {ev.decisions.map((d, i) => {
                    const before = d.original_weight
                    const after = d.final_weight
                    const delta = before != null && after != null ? after - before : null
                    return (
                      <tr key={i}>
                        <td>{d.ticker || '—'}</td>
                        <td><span className={`dec dec-${d.decision}`}>{d.decision}</span></td>
                        <td className="muted">{d.reason || '—'}</td>
                        <td className="num">{before == null ? '—' : pct(before)}</td>
                        <td className="num">{after == null ? '—' : pct(after)}</td>
                        <td className={`num ${delta > 1e-9 ? 'pos' : delta < -1e-9 ? 'neg' : 'muted'}`}>
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
          <div className="empty">Ledger empty.</div>
        )}
        <Pagination page={page} pageSize={pageSize} total={total} onChange={setPage} />
      </div>
    </div>
  )
}
