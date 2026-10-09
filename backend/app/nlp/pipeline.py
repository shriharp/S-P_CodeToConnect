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
from app.ingestion.adapters import RawSourceItem
from app.nlp.events import classify_event
from app.nlp.excerpts import sentence_excerpts
from app.nlp.sentiment import score_sentiment


def analyze_item(item: RawSourceItem, provenance: str, source_item_id: str | None = None) -> RiskSignal:
    """Return a RiskSignal for one normalized source item.

    MVP scope: single-company text. Multi-company splitting lands with ingestion.
    """
    item_id = source_item_id or item.external_id
    ingested_at = datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)
    event_category, event_excerpts = classify_event(item.text)
    senti_score, senti_excerpts = score_sentiment(item.text)

    factors = rubric.extract_factors(item.text)
    impact_score = rubric.score(factors)
    impact_explanation = rubric.explain(factors, impact_score) if impact_score else None
    impact_excerpts = sentence_excerpts(item.text, factors.evidence, EvidenceSupports.impact)

    excerpts = event_excerpts + senti_excerpts + impact_excerpts
    flags: set[QualityFlag] = {QualityFlag.unresolved_company}
    if item.published_at is None:
        flags.add(QualityFlag.missing_publication_time)
    if senti_score is None or impact_score is None:
        flags.add(QualityFlag.insufficient_evidence)
    signal = RiskSignal(
        signal_id=f"{item_id}-s0",
        source_item_id=item_id,
        source_provider=item.provider,
        source_type=item.source_type,
        source_url=item.url,
        published_at=item.published_at,
        ingested_at=ingested_at,
        provenance=Provenance(provenance),
        company_id="unresolved-mvp",
        company_name="unresolved-mvp",
        ticker=None,
        event_category=event_category,
        event_summary=item.text[:200],
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
    validate_evidence_membership(signal, item.text)
    return signal


def analyze(text: str, source_item_id: str, provider: str, provenance: str) -> RiskSignal:
    """Convenience wrapper: raw text -> RiskSignal (news, no URL/timestamps)."""
    item = RawSourceItem(
        provider=provider,
        source_type=SourceType.news,
        external_id=source_item_id,
        text=text,
    )
    return analyze_item(item, provenance=provenance, source_item_id=source_item_id)
