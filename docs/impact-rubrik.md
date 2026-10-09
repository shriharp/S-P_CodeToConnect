
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
This is a qualitative rubric, not yet a fully specified numerical algorithm.

Before claiming reproducible scoring:
- Define measurable extracted factors.
- Specify decision boundaries.
- Implement deterministic calculations.
- Test representative cases and abstention.
- Document ambiguity and limitations.

## Representative Cases
- Minor product improvement: potentially low impact.
- Small-site short disruption: potentially contained.
- Significant earnings revision: potentially material.
- Loss of a major revenue customer: potentially major.
- Default threatening continuity: potentially transformative.

These examples illustrate bands; they do not override company-specific evidence.
