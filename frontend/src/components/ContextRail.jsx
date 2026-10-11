import React, { useEffect, useState } from 'react'
import { getLiveHealth } from '../api.js'

export default function ContextRail({ demoMode, setDemoMode, overview, tab, setTab }) {
  const [liveHealth, setLiveHealth] = useState(null)
  const total = overview?.total ?? 0
  const nullSentiment = overview?.sentiment?.null ?? 0
  const nullImpact = overview?.impact?.null ?? 0
  const qualityRate = total
    ? Math.round(((2 * total - nullSentiment - nullImpact) / (2 * total)) * 100)
    : null

  useEffect(() => {
    let active = true
    const load = () => getLiveHealth().then((health) => {
      if (active) setLiveHealth(health)
    }).catch(() => {})
    load()
    const timer = setInterval(load, 15000)
    return () => {
      active = false
      clearInterval(timer)
    }
  }, [])

  return (
    <aside className="context-rail" aria-label="Context panel">
      <section className="rail-card">
        <div className="rail-label">Data mode</div>
        <div className="rail-mode">{demoMode ? 'Curated demo corpus' : 'Live sources'}</div>
        <p className="muted">
          {demoMode
            ? 'Evidence-rich replay data for a stable walkthrough.'
            : 'News, social posts, and prices are fetched on demand.'}
        </p>
        <label className="toggle-row">
          <span>Demo mode</span>
          <input
            type="checkbox"
            checked={demoMode}
            onChange={(event) => setDemoMode(event.target.checked)}
          />
          <span className="toggle" aria-hidden="true" />
        </label>
      </section>

      <section className="rail-card">
        <div className="rail-label">Ingestion runtime</div>
        <div className={`rail-mode ${liveHealth?.scheduler_enabled ? 'pos' : 'muted'}`}>
          {liveHealth?.scheduler_enabled ? 'Background scheduler running' : 'Manual polling'}
        </div>
        <p className="muted">
          {liveHealth?.scheduler_enabled
            ? 'The backend continues polling independently of this browser tab.'
            : 'Enable INGESTION_SCHEDULER_ENABLED=true to poll in the backend.'}
        </p>
        {liveHealth?.providers && (
          <p className="muted" style={{ marginBottom: 0 }}>
            {liveHealth.providers.filter((provider) => provider.last_success_at).length}/{liveHealth.providers.length} providers have succeeded.
            {liveHealth.queue ? ` Queue: ${liveHealth.queue.pending ?? 0} pending.` : ''}
          </p>
        )}
      </section>

      <section className="rail-card">
        <div className="rail-label">Signal quality</div>
        <div className="rail-stat">{qualityRate == null ? 'No data' : `${qualityRate}% field completeness`}</div>
        <p className="muted">
          {total ? `${total} stored signals. This measures usable scores, not model accuracy.` : 'Poll live sources or load the demo corpus.'}
        </p>
      </section>

      <section className="rail-card">
        <div className="rail-label">Suggested next step</div>
        <p className="rail-copy">
          {tab === 'overview'
            ? 'Inspect the signal feed to review evidence and quality flags.'
            : tab === 'signals'
              ? 'Use Strategy Lab to test a new article without persisting it.'
              : 'Compare the allocation changes with the decision ledger.'}
        </p>
        <button className="rail-link" onClick={() => setTab(tab === 'signals' ? 'lab' : 'signals')}>
          {tab === 'signals' ? 'Open Strategy Lab' : 'Review signals'}
        </button>
      </section>
    </aside>
  )
}
