import React, { useEffect, useState } from 'react'
import { getLedger, getWeightHistory, getSectors, getPerformance } from '../api.js'
import LineChart from '../components/LineChart.jsx'
import Pagination, { usePagination } from '../components/Pagination.jsx'

const pct = (w) => `${(w * 100).toFixed(2)}%`
const LEDGER_PAGE_SIZE = 4

export default function Portfolio({ demoMode = false }) {
  const [ledger, setLedger] = useState([])
  const [history, setHistory] = useState([])
  const [sectors, setSectors] = useState({})
  const [perf, setPerf] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    ;(async () => {
      try {
        const [l, h, s, p] = await Promise.all([
          getLedger(200, demoMode ? 'demo' : 'live'),
          getWeightHistory(demoMode ? 'demo' : 'live'),
          getSectors(),
          getPerformance(demoMode ? 'demo' : 'live'),
        ])
        setLedger(l)
        setHistory(h)
        setSectors(s)
        setPerf(p)
      } catch (e) {
        setError(e.message)
      }
    })()
  }, [demoMode])

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
    // Keep a stable presentation order across live/demo scopes. Sorting by
    // current exposure made the table jump whenever the mode changed.
    .sort((a, b) => a.sector.localeCompare(b.sector))
  const maxDelta = Math.max(...sectorRows.map((r) => Math.abs(r.delta)), 0.01)

  // Paginate individual ticker decisions, not rebalance event headings.
  const decisions = ledger.flatMap((ev) => (ev.decisions || []).map((decision, index) => ({
    ...decision,
    eventId: ev.event_id,
    timestamp: ev.timestamp,
    decisionIndex: index,
  })))
  const { slice: decisionPage, page, setPage, total, pageSize } = usePagination(decisions, LEDGER_PAGE_SIZE)

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
              <div className="sub">Latest target allocation. Proposed mock weights, not executed.</div>
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
            <div className="empty">No rebalance events yet. Enable Demo mode from the right rail.</div>
          )}
        </div>

        <div className="panel">
          <div className="panel-head">
            <div>
              <h3>Sector Exposure</h3>
              <div className="sub">First to latest rebalance. Bar length is exposure; shading is concentration.</div>
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
                      <div className="diverging-bar" aria-label={`${r.sector} exposure change ${(r.delta * 100).toFixed(2)} percentage points`}>
                        <div className="diverging-zero" />
                        {r.delta < 0 && <div className="diverging-fill diverging-negative" style={{ width: `${(Math.abs(r.delta) / maxDelta) * 50}%` }} />}
                        {r.delta > 0 && <div className="diverging-fill diverging-positive" style={{ width: `${(r.delta / maxDelta) * 50}%` }} />}
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
                <div className="kpi"><div className="kpi-label">Avg turnover</div><div className="kpi-value">{perf.metrics.turnover_pct ?? 'n/a'}%</div></div>
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
            <div className="sub">Auditable record of every rebalance. Decision, reason, and before to after weight.</div>
          </div>
        </div>
        {decisions.length ? (
          <table>
            <thead>
              <tr>
                <th>Event</th><th>Ticker</th><th>Decision</th><th>Reason</th>
                <th className="num">Before</th><th className="num">After</th><th className="num">Δ</th>
              </tr>
            </thead>
            <tbody>
              {decisionPage.map((d) => {
                const delta = d.original_weight != null && d.final_weight != null
                  ? d.final_weight - d.original_weight
                  : null
                return (
                  <tr key={`${d.eventId}-${d.decisionIndex}`}>
                    <td className="mono">{d.eventId}</td>
                    <td>{d.ticker || 'n/a'}</td>
                    <td><span className={`dec dec-${d.decision}`}>{d.decision}</span></td>
                    <td className="muted">{d.reason || 'n/a'}</td>
                    <td className="num">{d.original_weight == null ? 'n/a' : pct(d.original_weight)}</td>
                    <td className="num">{d.final_weight == null ? 'n/a' : pct(d.final_weight)}</td>
                    <td className={`num ${delta > 1e-9 ? 'pos' : delta < -1e-9 ? 'neg' : 'muted'}`}>
                      {delta == null ? 'n/a' : `${delta > 0 ? '+' : ''}${(delta * 100).toFixed(2)} pp`}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : (
          <div className="empty">Ledger empty.</div>
        )}
        <Pagination page={page} pageSize={pageSize} total={total} onChange={setPage} />
      </div>
    </div>
  )
}
