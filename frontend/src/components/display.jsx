import React from 'react'

// Display-only helpers: these map backend fields to friendlier end-user labels.
// They never change the underlying data. The contract's event_category stays
// "Unknown"; we just present it better.

export const FLAG_MEANINGS = {
  unresolved_company: 'No known company matched this text, so it cannot map to a holding.',
  missing_publication_time: 'The source did not provide a publish timestamp.',
  insufficient_evidence: 'Not enough quantified evidence to score impact (or sentiment).',
  unverified_claim: 'The claim could not be corroborated by a second source.',
  conflicting_claims: 'Sources disagree about this event.',
  multiple_events: 'The text covers more than one event; only the primary was scored.',
  analysis_error: 'The analysis pipeline errored on this item.',
}

// Social chatter: high-sentiment social posts that carry no distinct event.
// Shown as its own category so "Unknown" doesn't read as broken.
export function displayCategory(signal) {
  if (
    signal.source_type === 'social' &&
    signal.event_category === 'Unknown' &&
    signal.sentiment_score !== null &&
    signal.sentiment_score !== undefined
  ) {
    return 'Social chatter'
  }
  return signal.event_category
}

export function CategoryCell({ signal }) {
  const label = displayCategory(signal)
  if (label === 'Social chatter') {
    return <span className="muted" title="Sentiment-only social post; no distinct financial event.">{label}</span>
  }

  return <>{label}</>
}

export function ProviderLabel({ provider }) {
  if (!provider || provider === 'unknown') return <span className="muted" title="The upstream record did not identify its provider.">Provider not identified</span>
  return <span>{provider}</span>
}

export function FlagList({ flags }) {
  if (!flags || flags.length === 0) return <span className="muted">none</span>
  return (
    <>
      {flags.map((f) => (
        <span className="flag" key={f} title={FLAG_MEANINGS[f] || ''}>{f}</span>
      ))}
    </>
  )
}

export function ModeBadge({ demoMode }) {
  return (
    <span className={`mode-badge ${demoMode ? 'mode-replay' : 'mode-live'}`}>
      {demoMode ? 'DEMO REPLAY' : 'LIVE MODE'}
    </span>
  )
}
