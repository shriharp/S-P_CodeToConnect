const BASE = '/api'

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail ? JSON.stringify(detail.detail) : `HTTP ${res.status}`)
  }
  return res.json()
}

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail ? JSON.stringify(detail.detail) : `HTTP ${res.status}`)
  }
  return res.json()
}

export const analyzeText = (payload) => post('/analyze', payload)
export const rebalancePortfolio = (payload) => post('/rebalance', payload)
export const simulate = (payload) => post('/simulate', payload)
export const simulateText = (payload) => post('/simulate-text', payload)
export const ingestItems = (payload) => post('/ingest', payload)
export const replayRecording = (payload) => post('/replay', payload)

// Dashboard (Phase 2)
export const getSignals = (params = {}) => {
  const q = new URLSearchParams(params).toString()
  return get(`/signals${q ? `?${q}` : ''}`)
}
export const getSignalsCount = () => get('/signals/count')
export const getSignalsOverview = (dashboard = 'all') => get(`/signals/overview?dashboard=${dashboard}`)
export const getLedger = (limit = 100, dashboard = 'all') => get(`/ledger?limit=${limit}&dashboard=${dashboard}`)
export const getWeightHistory = (dashboard = 'all') => get(`/portfolio/weight-history?dashboard=${dashboard}`)
export const getPerformance = (dashboard = 'all') => get(`/portfolio/performance?dashboard=${dashboard}`)
export const getBenchmark = (refresh) => get(`/benchmark/sentiment${refresh ? '?refresh=true' : ''}`)
export const getPrices = (tickers) =>
  get(`/market/prices${tickers ? `?tickers=${tickers}` : ''}`)
export const getSectors = () => get('/market/sectors')
export const runDemoReplay = () => post('/demo/replay', {})
export const livePoll = (newsQuery) =>
  post(`/live/poll${newsQuery ? `?news_query=${encodeURIComponent(newsQuery)}` : ''}`, {})
export const getLiveHealth = () => get('/live/health')
export const getLiveProviderItems = (provider, params = {}) => {
  const q = new URLSearchParams(params).toString()
  return get(`/live/providers/${encodeURIComponent(provider)}/items${q ? `?${q}` : ''}`)
}
