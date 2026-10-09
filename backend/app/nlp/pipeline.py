"""Analysis pipeline: text -> company-specific RiskSignal.

Orchestrates NLP interpretation (sentiment, event) and deterministic impact
scoring, then assembles a contract-validated signal.
"""

from datetime import datetime, timezone

from app.core.signal_contract import (
    AnalysisStatus,
    EvidenceSupports,
    Provenance,
    QualityFlag,
    RiskSignal,
    SourceType,
    validate_evidence_membership,
)
from app.impact import rubric
from app.nlp.events import classify_event
from app.nlp.excerpts import sentence_excerpts
from app.nlp.sentiment import score_sentiment


def analyze(text: str, source_item_id: str, provider: str, provenance: str) -> RiskSignal:
    """Return a RiskSignal for one detected company mention.

    MVP scope: single-company text. Multi-company splitting lands with ingestion.
    """
    now = datetime.now(timezone.utc)
    event_category, event_excerpts = classify_event(text)
    senti_score, senti_excerpts = score_sentiment(text)

    factors = rubric.extract_factors(text)
    impact_score = rubric.score(factors)
    impact_explanation = rubric.explain(factors, impact_score) if impact_score else None
    impact_excerpts = sentence_excerpts(text, factors.evidence, EvidenceSupports.impact)

    excerpts = event_excerpts + senti_excerpts + impact_excerpts
    flags: set[QualityFlag] = {QualityFlag.unresolved_company}
    if senti_score is None or impact_score is None:
        flags.add(QualityFlag.insufficient_evidence)
    signal = RiskSignal(
        signal_id=f"{source_item_id}-s0",
        source_item_id=source_item_id,
        source_provider=provider,
        source_type=SourceType.news,
        published_at=now,
        ingested_at=now,
        provenance=Provenance(provenance),
        company_id="unresolved-mvp",
        company_name="unresolved-mvp",
        ticker=None,
        event_category=event_category,
        event_summary=text[:200],
        sentiment_score=senti_score,
        impact_score=impact_score,
        impact_explanation=impact_explanation,
        evidence_excerpts=excerpts,
        analysis_status=(
            AnalysisStatus.abstained
            if senti_score is None and impact_score is None
            else AnalysisStatus.complete
        ),
        quality_flags=flags,
        analyzed_at=now,
        analysis_method_version="lexicon-0.1",
    )
    validate_evidence_membership(signal, text)
    return signal
