"""Labeled impact-scoring evaluation fixtures.

Each case: (headline, expected_low, expected_high) or (headline, None, None)
for abstention. Expected values are inclusive bands from the impact rubric.
Gold labels are human-assigned for development benchmarking only; per
docs/model-evaluation.md these synthetic fixtures do NOT establish real-world
accuracy and are not used for final accuracy claims.

Deliberately diverse: qualitative magnitude (no percentage), quantified bands,
negation, neutral/abstention, continuity threats, scope and persistence
modifiers — to measure whether the extractor generalizes beyond clean cases.
"""

# (text, expected_low, expected_high)  -- (text, None, None) = should abstain
IMPACT_EVAL_CASES: list[tuple[str, int | None, int | None]] = [
    # --- Continuity / solvency (transformative) ---
    ("The company faces bankruptcy after defaulting on debt.", 9, 10),
    ("Insolvency fears mounted as the firm could not pay creditors.", 9, 10),
    ("The retailer filed for bankruptcy protection amid losses.", 9, 10),
    # --- Quantified magnitude bands (aligned to rubric band table) ---
    ("Profit surged 40% this quarter.", 5, 6),
    ("Revenue dropped 25% year over year.", 5, 6),
    ("Operating income fell 8 percent in the period.", 3, 4),
    ("Shares slipped about 2% in early trading.", 1, 2),
    ("The company cut costs by 60%, gutting operations.", 7, 8),
    # --- Qualitative high magnitude (no percentage) ---
    ("Apple sales boom in past quarter.", 7, 8),
    ("Apple shares soared to a record high.", 7, 8),
    ("Profits tumbled amid collapsing demand.", 7, 8),
    ("The stock plunged to an all-time low.", 7, 8),
    ("Revenue cratered as the market collapsed.", 7, 8),
    # --- Qualitative moderate magnitude ---
    ("Apple revenue fell sharply.", 5, 6),
    ("The stock jumped on the announcement.", 5, 6),
    ("Profits rebounded strongly last quarter.", 5, 6),
    ("Shares slid amid weak guidance.", 5, 6),
    # --- Qualitative low magnitude ---
    ("The stock edged up slightly.", 3, 4),
    ("Shares dipped before recovering.", 3, 4),
    ("The stock ticked down in early trade.", 3, 4),
    # --- Scope / persistence modifiers ---
    ("A outage hit the entire company, shutting all plants.", 5, 8),
    ("Production halted permanently at the firm's only plant.", 5, 8),
    ("A brief outage at one facility disrupted a single shift.", 3, 4),
    # --- Negation (should NOT count as magnitude) ---
    ("Apple avoided any significant decline this quarter.", None, None),
    ("The company prevented a major loss through hedging.", None, None),
    ("There was no material impact on operations.", None, None),
    ("Shares did not fall despite the warning.", None, None),
    # --- Neutral / no impact (should abstain) ---
    ("The company is expected to report next month.", None, None),
    ("The board scheduled its annual meeting for June.", None, None),
    ("Management reaffirmed its previously issued guidance.", None, None),
    ("The firm named a new head of its European division.", None, None),
    ("Investors watched the index trade flat.", None, None),
    # --- Mixed / contradictory: rubric rule 7 says ABSTAIN when evidence
    #     permits materially different bands, so these correctly return None ---
    ("A modest dip in one segment offset by strength elsewhere.", None, None),
    ("The merger boosted the stock but hurt the acquirer.", None, None),
    ("Currency swings dented profits but volume held firm.", None, None),
    ("A small recall affected a limited batch of products.", 3, 4),
    ("The outage disrupted shipping routes across the region.", None, None),
]
