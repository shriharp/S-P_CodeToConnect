
# Signal Contract

## Unit of Analysis
One source item + one affected company + one primary relevant event.

One article can produce multiple company-specific signals.
A company mention alone does not prove that the company is affected.

## Required Contract Fields
- schema_version
- signal_id
- source_item_id
- source_provider
- source_type: news | social
- source_url (when available)
- published_at
- ingested_at
- provenance: live | replay | synthetic
- company_id
- company_name
- ticker (when resolved)
- event_category
- event_summary
- sentiment_score
- impact_score
- impact_explanation
- evidence_excerpts
- analysis_status
- quality_flags
- analyzed_at
- analysis_method_version

These are conceptual field names. Verify exact names, types, enums, and optionality against the existing Pydantic schema before changing it.

## Semantics

### Sentiment
Company-specific favorable/unfavorable implications.
Zero means neutral, never unknown.
Missing or indeterminable sentiment = null.

### Impact
Magnitude of company-relative potential financial consequences, independent of direction.

Not a stock prediction, probability, confidence score, or synonym for negativity.
Missing evidence = null, not a minimum score.

### Credibility
Represent unverified or conflicting claims using quality flags.
Do not silently reduce impact because credibility is uncertain.

### Freshness
Keep publication time separate from impact.
Downstream policies determine whether a signal is too old.

### Duplication
Duplicate coverage must not repeatedly adjust portfolio weights.
Signal-ID deduplication alone is insufficient for repeated reporting of the same event.

## Event Taxonomy
- Geopolitical
- Macroeconomic
- Credit event
- Merger or acquisition
- Product launch
- Earnings
- Operational disruption
- Commercial agreement
- Regulatory or legal
- Other
- Unknown

Other = identifiable but outside taxonomy.
Unknown = cannot determine event.

## Quality Flags
- Unresolved company
- Missing publication time
- Insufficient evidence
- Unverified claim
- Conflicting claims
- Multiple events
- Analysis error

## Evidence
- Store exact excerpts from retained source text.
- Associate excerpts with the fields they support.
- Verify excerpt membership.
- Do not fabricate excerpts.
- Evidence supports interpretation, not source truth or numerical-score accuracy.

## Validation
Validate:
- Schema and field types.
- Score bounds.
- Null versus neutral.
- Evidence membership.
- Timestamp handling.
- Quality-state consistency.
- Independent company-specific results.

The Pydantic implementation is the source of truth for exact serialized contracts.
