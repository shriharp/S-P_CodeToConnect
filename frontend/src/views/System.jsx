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

  const provenanceCounts = ledger.reduce((acc, ev) => {
    ev.decisions.forEach((d) => {
      acc[d.decision] = (acc[d.decision] || 0) + 1
    })
    return acc
  }, {})

  return (
    <div>
      <div className="panel">
        <h2 style={{ marginTop: 0, fontSize: '1.05rem' }}>System Status</h2>
        <table>
          <tbody>
            <tr><th>Backend</th><td className={status === 'ok' ? 'pos' : 'neg'}>{status}</td></tr>
            <tr><th>Signals persisted</th><td>{count ?? '—'}</td></tr>
            <tr><th>Rebalance events</th><td>{ledger.length}</td></tr>
            <tr><th>Weight-history points</th><td>{history.length}</td></tr>
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h2 style={{ marginTop: 0, fontSize: '1.05rem' }}>Decision Breakdown</h2>
        <p className="muted">Aggregate of every recorded decision in the ledger.</p>
        <table>
          <tbody>
            {Object.entries(provenanceCounts).map(([k, v]) => (
              <tr key={k}><td><span className={`dec dec-${k}`}>{k}</span></td><td>{v}</td></tr>
            ))}
            {Object.keys(provenanceCounts).length === 0 && (
              <tr><td className="muted">No decisions recorded yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <h2 style={{ marginTop: 0, fontSize: '1.05rem' }}>Provenance &amp; Reproducibility</h2>
        <ul className="muted">
          <li><strong>live</strong> — real inference on text submitted via /analyze or /ingest.</li>
          <li><strong>replay</strong> — committed historical dataset re-run through the pipeline (deterministic, offline).</li>
          <li><strong>synthetic</strong> — hand-authored fixtures for the rebalance demo.</li>
        </ul>
        <p className="muted">
          The demo replay (data/demo_news.jsonl) is deterministic and requires no network, so a
          live demo does not depend on current news. Market prices are committed CSVs.
        </p>
      </div>
    </div>
  )
}
