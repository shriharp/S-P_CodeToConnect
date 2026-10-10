import React, { useEffect, useState } from 'react'
import { getSignalsCount, getLedger, getWeightHistory } from '../api.js'

// System / Observability (lightweight): ingestion counts, provenance breakdown,
// replay + reproducibility info, backend status. No heavy monitoring infra.
export default function System() {
  const [count, setCount] = useState(null)
  const [ledger, setLedger] = useState([])
  const [history, setHistory] = useState([])
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    ;(async () => {
      try {
        const [c, l, h] = await Promise.all([
          getSignalsCount(),
          getLedger(200),
          getWeightHistory(),
        ])
        setCount(c.count)
        setLedger(l)
        setHistory(h)
        setStatus('ok')
      } catch {
        setStatus('unreachable')
      }
    })()
  }, [])

  const decisionCounts = ledger.reduce((acc, ev) => {
    ev.decisions.forEach((d) => {
      acc[d.decision] = (acc[d.decision] || 0) + 1
    })
    return acc
  }, {})
  const totalDecisions = Object.values(decisionCounts).reduce((a, b) => a + b, 0)

  return (
    <div>
      <div className="page-head">
        <h2>System</h2>
        <p>Backend status, ingestion counts, and how the three provenance modes work.</p>
      </div>

      <div className="grid-2">
        <div className="panel">
          <div className="panel-head">
            <div>
              <h3>System Status</h3>
              <div className="sub">Live backend health and persisted data counts</div>
            </div>
          </div>
          <div className="kpis">
            <div className="kpi">
              <div className="kpi-label">Backend</div>
              <div className="kpi-value" style={{ fontSize: '1rem', color: status === 'ok' ? 'var(--pos)' : 'var(--neg)' }}>
                {status}
              </div>
            </div>
            <div className="kpi"><div className="kpi-label">Signals</div><div className="kpi-value">{count ?? '—'}</div></div>
            <div className="kpi"><div className="kpi-label">Rebalance events</div><div className="kpi-value">{ledger.length}</div></div>
            <div className="kpi"><div className="kpi-label">Weight points</div><div className="kpi-value">{history.length}</div></div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <div>
              <h3>Decision Breakdown</h3>
              <div className="sub">Aggregate of every recorded decision in the ledger</div>
            </div>
          </div>
          {totalDecisions > 0 ? (
            <table>
              <thead><tr><th>Decision</th><th className="num">Count</th><th></th></tr></thead>
              <tbody>
                {Object.entries(decisionCounts).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
                  <tr key={k}>
                    <td><span className={`dec dec-${k}`}>{k}</span></td>
                    <td className="num">{v}</td>
                    <td style={{ width: '50%' }}>
                      <div className="bar"><div style={{ width: `${(v / totalDecisions) * 100}%` }} /></div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty">No decisions recorded yet.</div>
          )}
        </div>
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h3>Provenance &amp; Reproducibility</h3>
            <div className="sub">Every signal is labeled with how it was produced</div>
          </div>
        </div>
        <table>
          <tbody>
            <tr>
              <td><span className="prov prov-live">live</span></td>
              <td className="muted">Real inference on text submitted via /analyze, /ingest, or a live source poll.</td>
            </tr>
            <tr>
              <td><span className="prov prov-replay">replay</span></td>
              <td className="muted">Committed historical dataset re-run through the pipeline — deterministic, offline.</td>
            </tr>
            <tr>
              <td><span className="prov prov-synthetic">synthetic</span></td>
              <td className="muted">Hand-authored fixtures for the rebalance demo and what-if simulator.</td>
            </tr>
          </tbody>
        </table>
        <p className="muted" style={{ marginBottom: 0 }}>
          The demo replay (data/demo_news.jsonl) is deterministic and needs no network, so a live
          demo doesn't depend on current news. Market prices are committed CSVs fetched from yfinance.
        </p>
      </div>
    </div>
  )
}
