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

export const analyzeText = (payload) => post('/analyze', payload)
export const rebalancePortfolio = (payload) => post('/rebalance', payload)
export const ingestItems = (payload) => post('/ingest', payload)
export const replayRecording = (payload) => post('/replay', payload)
