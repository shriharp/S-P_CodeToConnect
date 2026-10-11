const localTimestamp = new Intl.DateTimeFormat(undefined, {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

export const formatLocalTimestamp = (value) => {
  if (!value) return 'n/a'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'n/a' : localTimestamp.format(date)
}

export const formatLocalShortTimestamp = (value) => {
  if (!value) return 'n/a'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'n/a'
  return new Intl.DateTimeFormat(undefined, {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}
