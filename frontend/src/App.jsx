import React, { useState } from 'react'
import Overview from './views/Overview.jsx'
import Signals from './views/Signals.jsx'
import Portfolio from './views/Portfolio.jsx'
import StrategyLab from './views/StrategyLab.jsx'
import System from './views/System.jsx'

const TABS = [
  { id: 'overview', label: 'Overview', C: Overview },
  { id: 'signals', label: 'Signals', C: Signals },
  { id: 'portfolio', label: 'Portfolio', C: Portfolio },
  { id: 'lab', label: 'Strategy Lab', C: StrategyLab },
  { id: 'system', label: 'System', C: System },
]

export default function App() {
  const [tab, setTab] = useState('overview')
  const Active = TABS.find((t) => t.id === tab).C
  return (
    <div className="app">
      <header>
        <h1>Risk Engine Dashboard</h1>
        <p className="muted">
          NLP risk signals → mock portfolio rebalancing. Mock allocations for demonstration
          only — not investment advice or predictions.
        </p>
      </header>
      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? 'active' : ''}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <Active />
    </div>
  )
}
