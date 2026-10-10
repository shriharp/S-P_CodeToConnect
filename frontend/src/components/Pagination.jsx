import React from 'react'

// Shared pagination control. Pure presentational: parent owns the page state.
// Shows "X–Y of Z" plus numbered pages with prev/next, collapsing long runs.
export default function Pagination({ page, pageSize, total, onChange }) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  const current = Math.min(page, pageCount)
  const from = total === 0 ? 0 : (current - 1) * pageSize + 1
  const to = Math.min(current * pageSize, total)

  // Build a compact page list with ellipses: 1 … 4 5 6 … 20
  const pages = []
  const push = (p) => pages.push(p)
  if (pageCount <= 7) {
    for (let i = 1; i <= pageCount; i++) push(i)
  } else {
    push(1)
    if (current > 3) push('…')
    for (let i = Math.max(2, current - 1); i <= Math.min(pageCount - 1, current + 1); i++) push(i)
    if (current < pageCount - 2) push('…')
    push(pageCount)
  }

  if (total === 0) return null

  return (
    <div className="pager">
      <span className="pager-info">
        {from}–{to} of {total}
      </span>
      <div className="pager-controls">
        <button onClick={() => onChange(current - 1)} disabled={current <= 1} aria-label="Previous page">
          ‹
        </button>
        {pages.map((p, i) =>
          p === '…' ? (
            <span className="ellipsis" key={`e${i}`}>…</span>
          ) : (
            <button
              key={p}
              className={p === current ? 'active' : ''}
              onClick={() => onChange(p)}
            >
              {p}
            </button>
          )
        )}
        <button onClick={() => onChange(current + 1)} disabled={current >= pageCount} aria-label="Next page">
          ›
        </button>
      </div>
    </div>
  )
}

// Hook that pairs with Pagination: returns a slice + pager props.
export function usePagination(items, pageSize) {
  const [page, setPage] = React.useState(1)
  const total = items.length
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  const current = Math.min(page, pageCount)
  const slice = items.slice((current - 1) * pageSize, current * pageSize)
  React.useEffect(() => {
    if (page > pageCount) setPage(pageCount)
  }, [page, pageCount])
  return { slice, page: current, setPage, total, pageSize }
}
