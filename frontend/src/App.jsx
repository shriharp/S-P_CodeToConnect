import React, { useEffect, useState } from 'react'
import { getSignalsOverview } from './api.js'
import ContextRail from './components/ContextRail.jsx'
import Overview from './views/Overview.jsx'
import Signals from './views/Signals.jsx'
import Portfolio from './views/Portfolio.jsx'
import StrategyLab from './views/StrategyLab.jsx'
import System from './views/System.jsx'

const TABS = [
  { id: 'overview', label: 'Overview', C: Overview },
  { id: 'signals', label: 'Signal Feed', C: Signals },
  { id: 'portfolio', label: 'Portfolio', C: Portfolio },
  { id: 'lab', label: 'Strategy Lab', C: StrategyLab },
  { id: 'system', label: 'Observability', C: System },
]

export default function App() {
  const [tab, setTab] = useState('overview')
  const [demoMode, setDemoMode] = useState(false)
  const [overview, setOverview] = useState(null)
  const Active = TABS.find((t) => t.id === tab).C
  useEffect(() => {
    getSignalsOverview(demoMode ? 'demo' : 'live').then(setOverview).catch(() => setOverview(null))
  }, [tab, demoMode])
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <img className="brand-logo" src="/brand/kairos-logo.svg" alt="KAIROS logo" />
          <div className="brand-copy">
            <div className="brand-name">KAIROS</div>
            <div className="brand-tagline">Signal Over Noise</div>
          </div>
          <div className="tag">AI/NLP risk intelligence · mock rebalancing</div>
        </div>
        <nav className="nav">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`nav-item ${tab === t.id ? 'active' : ''}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          Mock allocations for demonstration only - not investment advice or predictions.
        </div>
      </aside>
      <div className="workspace">
        <main className="content">
          <Active demoMode={demoMode} key={`${tab}-${demoMode}`} />
        </main>
        <ContextRail demoMode={demoMode} setDemoMode={setDemoMode} overview={overview} tab={tab} setTab={setTab} />
      </div>
    </div>
  )
}
