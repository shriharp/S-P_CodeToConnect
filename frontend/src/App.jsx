import React, { useState } from 'react'
import Overview from './views/Overview.jsx'
import Signals from './views/Signals.jsx'
import Portfolio from './views/Portfolio.jsx'
import StrategyLab from './views/StrategyLab.jsx'
import System from './views/System.jsx'

const TABS = [
  { id: 'overview', label: 'Overview', ico: '◧', C: Overview },
  { id: 'signals', label: 'Signals', ico: '⚡', C: Signals },
  { id: 'portfolio', label: 'Portfolio', ico: '▤', C: Portfolio },
  { id: 'lab', label: 'Strategy Lab', ico: '⚗', C: StrategyLab },
  { id: 'system', label: 'System', ico: '⚙', C: System },
]

export default function App() {
  const [tab, setTab] = useState('overview')
  const Active = TABS.find((t) => t.id === tab).C
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <h1>Risk Engine</h1>
          <div className="tag">NLP signals · mock rebalancing</div>
        </div>
        <nav className="nav">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`nav-item ${tab === t.id ? 'active' : ''}`}
              onClick={() => setTab(t.id)}
            >
              <span className="ico">{t.ico}</span>
              {t.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          Mock allocations for demonstration only — not investment advice or predictions.
        </div>
      </aside>
      <main className="content">
        <Active />
      </main>
    </div>
  )
}
