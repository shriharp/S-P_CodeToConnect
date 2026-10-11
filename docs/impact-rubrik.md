
# Financial Impact Rubric

## Definition
Impact measures the magnitude of potential financial consequences relative to the affected company, regardless of sentiment direction.

Scale: 1-10.
Unknown/insufficient evidence: null.

## Scoring Bands

| Score | Band | Interpretation |
|---|---|---|
| 1-2 | Limited | Routine or immaterial consequences |
| 3-4 | Contained | Bounded impact on minor operations or exposure |
| 5-6 | Material | Meaningful financial/operating consequences without threatening overall continuity |
| 7-8 | Major | Large company-wide exposure or prolonged core-business disruption |
| 9-10 | Transformative | Credible continuity/solvency risk or fundamental change in company scale |

## Scoring Procedure
1. Extract explicitly supported impact facts.
2. Consider company-relative magnitude, exposure, breadth, and duration.
3. Choose the evidence-supported band.
4. Default to the lower score within the band.
5. Use the upper score only when evidence clearly strengthens magnitude, breadth, or persistence.
6. Avoid double-counting overlapping factors.
7. Return null if missing information permits materially different scoring bands.

## Constraints
- Do not assign fixed scores by event category.
- Do not derive impact directly from sentiment.
- Do not equate impact with claim credibility.
- Do not invent exposure, revenue, duration, or probabilities.
- A generative model must not choose the final impact score.
- Preserve the evidence and explanation behind the assigned score.

## Implementation Status
Deterministic scoring with modular factor extraction (2026-10-10).

Architecture is split so the extractor can be swapped for a better
financial-domain model later without touching scoring:
- `app/impact/factors.py` — `ImpactFactors` contract + `FactorExtractor` ABC.
- `app/impact/deterministic.py` — current extractor impl.
- `app/impact/rubric.py` — deterministic `score()`/`explain()` only.

The extractor reads BOTH quantified cues (percentages) AND qualitative
magnitude phrases ("surge", "collapse", "record high"), with negation handling
("avoided a decline" abstains), contrast/offset detection ("dip offset by
strength" abstains), and optional event-category context. This fixes the old
quant-only behavior where purely qualitative headlines ("sales boom") scored
null. Scoring bands and abstention rules below are unchanged.

### Measured on a diverse dev eval set (2026-10-10)
`app/impact/eval_cases.py` (37 synthetic fixtures: qualitative, quantified,
negation, neutral, continuity, scope, mixed). Reproduce:
`cd backend && .venv/bin/python -m pytest tests/test_impact_eval.py -q`.
- Scored band-accuracy: 21/24 = 0.875
- Abstention-correct (neutral/negated/mixed): 13/13
Synthetic fixtures only — NOT a real-world accuracy claim.

### Remaining gaps (known limitations)
- Operational-halt phrasing ("production halted permanently at one plant") can
  still abstain — no magnitude phrase and no percentage anchors it.
- Qualitative magnitude is keyword-tiered, not model-read; a finance-tuned
  magnitude model (via the FactorExtractor seam) is the intended upgrade path.

## Representative Cases
- Minor product improvement: potentially low impact.
- Small-site short disruption: potentially contained.
- Significant earnings revision: potentially material.
- Loss of a major revenue customer: potentially major.
- Default threatening continuity: potentially transformative.

These examples illustrate bands; they do not override company-specific evidence.
