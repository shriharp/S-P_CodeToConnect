"""Analysis pipeline: text -> company-specific RiskSignal.

Orchestrates NLP interpretation (sentiment, event) and deterministic impact
scoring, then assembles a contract-validated signal.
"""

from datetime import datetime, timezone

from app.core.entities import resolve
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
from app.nlp.excerpts import merge_excerpts, sentence_excerpts
from app.nlp.sentiment import NEGATIVE_CUES, POSITIVE_CUES, score_sentiment


def _all_cues() -> list[str]:
    return list(NEGATIVE_CUES) + list(POSITIVE_CUES)


def analyze_item(
    item: RawSourceItem,
    provenance: str,
    source_item_id: str | None = None,
    sentiment_backend: str = "lexicon",
    ingested_at: datetime | None = None,
) -> list[RiskSignal]:
    """Return one RiskSignal per resolved company in the source item.

    Contract unit: one source item + one affected company + one primary event.
    When no company resolves, a single unresolved signal is returned with
    quality flags (never a fabricated identity).

    sentiment_backend: "lexicon" (default, no model download) or "model"
    (DistilRoBERTa financial checkpoint; see docs/model-evaluation.md).
    The model overrides the score only; evidence excerpts remain exact
    source substrings drawn from the lexicon cue layer.

    ingested_at: overrides the ingestion timestamp. Replay passes the item's
    published time so the freshness gate evaluates against event time, not
    wall-clock; live callers leave it None (defaults to now).
    """
    item_id = source_item_id or item.external_id
    ingested_at = ingested_at or datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)
    event_category, event_excerpts = classify_event(item.text)
    senti_score, senti_excerpts = score_sentiment(item.text)
    if sentiment_backend == "model":
        from app.nlp.sentiment_model import score_sentiment_model

        model_score = score_sentiment_model(item.text)
        if model_score is not None:
            senti_score = model_score
            senti_excerpts = sentence_excerpts(
                item.text, _all_cues(), EvidenceSupports.sentiment
            )
        method_version = "distilroberta-fin-0.1"
    else:
        method_version = "lexicon-0.1+entities-0.1"

    factors = rubric.extract_factors(item.text)
    impact_score = rubric.score(factors)
    impact_explanation = rubric.explain(factors, impact_score) if impact_score else None
    impact_excerpts = sentence_excerpts(item.text, factors.evidence, EvidenceSupports.impact)

    excerpts = merge_excerpts(event_excerpts + senti_excerpts + impact_excerpts)
    resolutions = resolve(item.text)

    flags: set[QualityFlag] = set()
    if item.published_at is None:
        flags.add(QualityFlag.missing_publication_time)
    if senti_score is None or impact_score is None:
        flags.add(QualityFlag.insufficient_evidence)

    if not resolutions:
        resolutions = [None]

    signals: list[RiskSignal] = []
    for idx, resolution in enumerate(resolutions):
        company_flags = set(flags)
        if resolution is None:
            company_flags.add(QualityFlag.unresolved_company)
            company_id, company_name, ticker = "unresolved", "unresolved", None
        else:
            company_id = resolution.company.company_id
            company_name = resolution.company.name
            ticker = resolution.company.ticker
        signal = RiskSignal(
            signal_id=f"{item_id}-s{idx}",
            source_item_id=item_id,
            source_provider=item.provider,
            source_type=item.source_type,
            source_url=item.url,
            published_at=item.published_at,
            ingested_at=ingested_at,
            provenance=Provenance(provenance),
            company_id=company_id,
            company_name=company_name,
            ticker=ticker,
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
            quality_flags=company_flags,
            analyzed_at=now,
            analysis_method_version=method_version,
        )
        validate_evidence_membership(signal, item.text)
        signals.append(signal)
    return signals


def analyze(text: str, source_item_id: str, provider: str, provenance: str) -> RiskSignal:
    """Convenience wrapper: raw text -> first signal (news, no URL/timestamps)."""
    item = RawSourceItem(
        provider=provider,
        source_type=SourceType.news,
        external_id=source_item_id,
        text=text,
    )
    return analyze_item(item, provenance=provenance, source_item_id=source_item_id)[0]
