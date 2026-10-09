"""Labeled evaluation fixtures for sentiment benchmarking.

Each case: financial text + gold company-specific sentiment in {-1, 0, 1}.
Gold labels are human-assigned for development benchmarking only; per
docs/model-evaluation.md these synthetic fixtures do NOT establish real-world
accuracy and are not used for final accuracy claims.
"""

# (text, gold) where gold: -1 unfavorable, 0 neutral, 1 favorable
EVAL_CASES: list[tuple[str, int]] = [
    # favorable
    ("Apple reported record profit and beat earnings estimates.", 1),
    ("Microsoft won a major cloud contract with a large retailer.", 1),
    ("Pfizer shares surged after the drug approval was confirmed.", 1),
    ("Walmart raised full-year guidance on strong same-store sales.", 1),
    ("Chevron posted a gain after announcing a new oil discovery.", 1),
    # unfavorable
    ("Apple cut revenue guidance after a factory shutdown.", -1),
    ("Pfizer faces a lawsuit over allegedly false marketing.", -1),
    ("JPMorgan was downgraded on concerns about credit losses.", -1),
    ("Exxon Mobil saw revenue fall 8 percent amid weak demand.", -1),
    ("A data outage disrupted Coca-Cola ordering systems for hours.", -1),
    # neutral
    ("Johnson & Johnson held its quarterly dividend steady.", 0),
    ("Procter & Gamble scheduled its earnings call for next month.", 0),
    ("Walmart named a new head of its grocery division.", 0),
    ("Chevron confirmed the previously announced management change.", 0),
    ("Microsoft disclosed the date of its annual shareholder meeting.", 0),
]
