import React from 'react'

export default function ContextRail({ demoMode, setDemoMode, overview, tab, setTab }) {
  const total = overview?.total ?? 0
  const nullSentiment = overview?.sentiment?.null ?? 0
  const nullImpact = overview?.impact?.null ?? 0
  const qualityRate = total
    ? Math.max(0, Math.round(((total - nullSentiment - nullImpact) / (total * 2)) * 100))
    : null

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
        <div className="rail-label">Signal quality</div>
        <div className="rail-stat">{qualityRate == null ? 'No data' : `${qualityRate}% scored fields`}</div>
        <p className="muted">
          {total ? `${total} stored signals. Null values remain null.` : 'Poll live sources or load the demo corpus.'}
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
