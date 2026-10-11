import React, { useEffect, useState } from 'react'
import { getSignalsCount, getLedger, getWeightHistory, getBenchmark, getLiveHealth } from '../api.js'

// System / Observability (lightweight): ingestion counts, provenance breakdown,
// replay + reproducibility info, backend status. No heavy monitoring infra.
export default function System() {
  const [count, setCount] = useState(null)
  const [ledger, setLedger] = useState([])
  const [history, setHistory] = useState([])
  const [status, setStatus] = useState('checking')
  const [liveHealth, setLiveHealth] = useState(null)

  useEffect(() => {
    const loadHealth = async () => {
      try {
        const [c, l, h, health] = await Promise.all([
          getSignalsCount(),
          getLedger(200),
          getWeightHistory(),
          getLiveHealth(),
        ])
        setCount(c.count)
        setLedger(l)
        setHistory(h)
        setLiveHealth(health)
        setStatus('ok')
      } catch {
        setStatus('unreachable')
      }
    }
    loadHealth()
    const timer = setInterval(loadHealth, 15000)
    return () => clearInterval(timer)
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
            <div className="kpi"><div className="kpi-label">Signals</div><div className="kpi-value">{count ?? 'n/a'}</div></div>
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
              <td className="muted">Committed historical dataset re-run through the pipeline. Deterministic and offline.</td>
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

      <BenchmarkPanel />
      <div className="panel">
        <div className="panel-head">
          <div>
            <h3>Live source health</h3>
            <div className="sub">Durable fetch, queue, cursor, and analysis state from the backend</div>
          </div>
          <span className={`prov ${liveHealth?.scheduler_enabled ? 'prov-live' : 'prov-replay'}`}>
            {liveHealth?.scheduler_enabled ? 'scheduler on' : 'manual mode'}
          </span>
        </div>
        {liveHealth?.providers?.length ? (
          <table>
            <thead><tr><th>Provider</th><th>Schedule</th><th>Last success</th><th>Newest source</th><th>Cursor</th><th className="num">Fetched</th><th className="num">Analyzed</th><th className="num">Skipped</th><th className="num">Errors</th></tr></thead>
            <tbody>{liveHealth.providers.map((p) => (
              <tr key={p.provider}>
                <td>{p.provider}</td>
                <td className="muted">{p.interval_seconds}s</td>
                <td className="muted">{p.last_success_at ? new Date(p.last_success_at).toLocaleString() : 'No successful fetch yet'}</td>
                <td className="muted">{p.newest_source_at ? new Date(p.newest_source_at).toLocaleString() : 'n/a'}</td>
                <td className="mono" title={p.cursor || ''}>{p.cursor ? `${p.cursor.slice(0, 18)}…` : 'n/a'}</td>
                <td className="num">{p.fetched_count}</td>
                <td className="num">{p.analyzed_count}</td>
                <td className="num">{p.skipped_count}</td>
                <td className="num">{p.error_count}</td>
              </tr>
            ))}</tbody>
          </table>
        ) : <p className="muted">No provider health data yet.</p>}
        {liveHealth?.queue && (
          <div className="kpis" style={{ marginTop: '1rem' }}>
            <div className="kpi"><div className="kpi-label">Queued</div><div className="kpi-value">{liveHealth.queue.pending ?? 0}</div></div>
            <div className="kpi"><div className="kpi-label">Processing</div><div className="kpi-value">{liveHealth.queue.processing ?? 0}</div></div>
            <div className="kpi"><div className="kpi-label">Completed</div><div className="kpi-value">{liveHealth.queue.complete ?? 0}</div></div>
          </div>
        )}
        {liveHealth?.providers?.some((p) => p.last_error) && (
          <div className="error" style={{ marginTop: '1rem' }}>
            {liveHealth.providers.filter((p) => p.last_error).map((p) => (
              <div key={p.provider}><strong>{p.provider}:</strong> {p.last_error}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function BenchmarkPanel() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = async (refresh = false) => {
    setLoading(true)
    setError(null)
    try {
      setData(await getBenchmark(refresh))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])
  const classes = ['-1', '0', '1']
  const labels = { '-1': 'neg', '0': 'neu', '1': 'pos' }

  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <h3>Model Evaluation</h3>
          <div className="sub">Operational benchmark, kept with observability rather than strategy controls.</div>
        </div>
        <button className="ghost" onClick={() => load(true)} disabled={loading}>{loading ? 'Running…' : 'Re-run'}</button>
      </div>
      {error && <div className="error">{error}</div>}
      {!data && !error && <p className="muted">Loading benchmark…</p>}
      {data && (
        <>
          <p className="muted">{data.methodology} Sample: {data.sample_size} fixtures · {data.hardware}.</p>
          <div className="grid-2">
            {['lexicon', 'model'].map((name) => {
              const backend = data[name]
              return (
                <div key={name}>
                  <h4>{name}</h4>
                  {backend ? (
                    <table>
                      <tbody>
                        <tr><th>Accuracy</th><td>{backend.accuracy == null ? 'n/a' : `${(backend.accuracy * 100).toFixed(1)}%`}</td></tr>
                        <tr><th>Scored</th><td>{backend.scored} / {backend.total}</td></tr>
                        <tr><th>Abstentions</th><td>{backend.abstain}</td></tr>
                        <tr><th>Latency</th><td>{backend.latency_ms_per_item} ms/item</td></tr>
                      </tbody>
                    </table>
                  ) : <p className="muted">{data.model_unavailable_reason || 'unavailable'}</p>}
                  {backend && <p className="muted">Recall: {classes.map((key) => `${labels[key]} ${backend.per_class_recall[key] == null ? 'n/a' : `${(backend.per_class_recall[key] * 100).toFixed(0)}%`}`).join(' · ')}</p>}
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
