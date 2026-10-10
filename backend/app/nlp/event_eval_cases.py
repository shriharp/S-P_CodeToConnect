"""Labeled evaluation fixtures for event-classification benchmarking.

Each case: financial text + gold event category key (matching EventCategory
member names, or "unknown"). Gold labels are human-assigned for development
benchmarking only; per docs/model-evaluation.md these synthetic fixtures do NOT
establish real-world accuracy and are not used for final accuracy claims.

Deliberately includes paraphrases and cases the keyword table is known to miss,
so the benchmark shows where the zero-shot model genuinely improves.
"""

# (text, gold_category_key)
EVENT_EVAL_CASES: list[tuple[str, str]] = [
    # earnings
    ("Acme Corp reported quarterly earnings that beat estimates.", "earnings"),
    ("The company raised its full-year revenue guidance after a strong quarter.", "earnings"),
    ("Profit fell short of analyst expectations this quarter.", "earnings"),
    ("Apple posted record quarterly revenue driven by services.", "earnings"),
    # operational disruption
    ("A factory shutdown disrupted production for three weeks.", "operational_disruption"),
    ("A major outage took the company's platform offline for hours.", "operational_disruption"),
    ("A recall affected thousands of vehicles after a defect was found.", "operational_disruption"),
    ("Production halted at the plant following an equipment failure.", "operational_disruption"),
    # merger / acquisition
    ("The firm agreed to acquire a smaller rival in a cash deal.", "merger_or_acquisition"),
    ("Shareholders approved the merger between the two companies.", "merger_or_acquisition"),
    ("A takeover bid valued the target company at $4 billion.", "merger_or_acquisition"),
    ("The two banks confirmed plans to combine their operations.", "merger_or_acquisition"),
    # regulatory / legal
    ("The regulator fined the bank for compliance failures.", "regulatory_or_legal"),
    ("A lawsuit alleges the company misled investors.", "regulatory_or_legal"),
    ("Antitrust investigators opened a probe into the merger.", "regulatory_or_legal"),
    ("The firm settled fraud charges with the authorities.", "regulatory_or_legal"),
    # credit event
    ("The company defaulted on its outstanding debt obligations.", "credit_event"),
    ("Credit rating agencies downgraded the sovereign's debt.", "credit_event"),
    ("The retailer filed for bankruptcy protection amid losses.", "credit_event"),
    ("Insolvency fears pushed the bond yield sharply higher.", "credit_event"),
    # product launch
    ("The company unveiled its new smartphone at an event.", "product_launch"),
    ("A new software release adds AI features to the platform.", "product_launch"),
    ("The drugmaker launched its latest treatment after approval.", "product_launch"),
    ("The automaker introduced its first electric vehicle.", "product_launch"),
    # commercial agreement
    ("The companies signed a partnership to build chip plants.", "commercial_agreement"),
    ("A multi-year supply deal was agreed between the two firms.", "commercial_agreement"),
    ("The joint venture will develop new battery technology.", "commercial_agreement"),
    ("The supplier won a major contract with the retailer.", "commercial_agreement"),
    # geopolitical
    ("New tariffs on imported steel rattled markets.", "geopolitical"),
    ("Escalating conflict disrupted shipping routes.", "geopolitical"),
    ("The export ban targets the country's semiconductor industry.", "geopolitical"),
    ("Geopolitical tensions pushed oil prices higher.", "geopolitical"),
    # macroeconomic
    ("The central bank raised interest rates to cool inflation.", "macroeconomic"),
    ("Recession fears grew after weak GDP figures.", "macroeconomic"),
    ("The finance minister announced new fiscal stimulus.", "macroeconomic"),
    ("Higher-for-longer rate expectations pressured equities.", "macroeconomic"),
    # unknown / chatter (should abstain)
    ("To the moon 🚀🚀", "unknown"),
    ("$AAPL $SPY $QQQ", "unknown"),
    ("I think it will touch 327", "unknown"),
    ("Love this company, great team", "unknown"),
]
