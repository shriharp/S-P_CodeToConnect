import React, { useEffect, useState } from 'react'
import { getLedger, getWeightHistory, getSectors } from '../api.js'

const pct = (w) => `${(w * 100).toFixed(2)}%`

export default function Portfolio() {
  const [ledger, setLedger] = useState([])
  const [history, setHistory] = useState([])
  const [sectors, setSectors] = useState({})
  const [error, setError] = useState(null)

  useEffect(() => {
    ;(async () => {
      try {
        const [l, h, s] = await Promise.all([getLedger(50), getWeightHistory(), getSectors()])
        setLedger(l)
        setHistory(h)
        setSectors(s)
      } catch (e) {
        setError(e.message)
      }
    })()
  }, [])

  const latest = history.length ? history[history.length - 1] : null
  const initial = history.length ? history[0] : null

  // Sector exposure: aggregate latest weights by sector.
  const sectorExposure = (() => {
    if (!latest) return {}
    const acc = {}
    for (const [t, w] of Object.entries(latest.weights)) {
      const sec = sectors[t]?.sector || 'Unknown'
      acc[sec] = (acc[sec] || 0) + w
    }
    return acc
  })()

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
        <h2 style={{ marginTop: 0, fontSize: '1.05rem' }}>Sector Exposure</h2>
        <p className="muted">Latest weights aggregated by sector (real sector metadata).</p>
        {Object.keys(sectorExposure).length ? (
          <table>
            <thead><tr><th>Sector</th><th>Exposure</th><th></th></tr></thead>
            <tbody>
              {Object.entries(sectorExposure).sort((a, b) => b[1] - a[1]).map(([sec, w]) => (
                <tr key={sec}>
                  <td>{sec}</td>
                  <td>{pct(w)}</td>
                  <td style={{ width: '40%' }}>
                    <div className="bar"><div style={{ width: `${w * 100}%` }} /></div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">No allocation yet.</p>
        )}
      </div>

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
                  <tr><th>Ticker</th><th>Decision</th><th>Reason</th><th>Final weight</th></tr>
                </thead>
                <tbody>
                  {ev.decisions.map((d, i) => (
                    <tr key={i}>
                      <td>{d.ticker || '—'}</td>
                      <td><span className={`dec dec-${d.decision}`}>{d.decision}</span></td>
                      <td className="muted">{d.reason || '—'}</td>
                      <td>{d.final_weight == null ? '—' : pct(d.final_weight)}</td>
                    </tr>
                  ))}
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
