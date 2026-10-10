"""Analysis pipeline: text -> company-specific RiskSignal.

Orchestrates NLP interpretation (sentiment, event) and deterministic impact
scoring, then assembles a contract-validated signal.
"""

from datetime import datetime, timezone
import re

from app.core.entities import resolve
from app.core.signal_contract import (
    AnalysisStatus,
    EventCategory,
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
    event_backend: str = "hybrid",
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

    event_backend: "hybrid" (default — keyword table for clear cues, zero-shot
    NLI model to catch paraphrases and break ambiguous ties; measurably best on
    the eval set), "keyword" (regex table only, no model), or "model" (zero-shot
    NLI only). The chosen backend picks the category; evidence excerpts always
    come from the retained source text (never fabricated).

    ingested_at: overrides the ingestion timestamp. Replay passes the item's
    published time so the freshness gate evaluates against event time, not
    wall-clock; live callers leave it None (defaults to now).
    """
    item_id = source_item_id or item.external_id
    ingested_at = ingested_at or datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)
    if event_backend == "model":
        from app.nlp.event_model import classify_event_model
        from app.nlp.events import EVENT_PATTERNS

        event_key, _conf = classify_event_model(item.text)
        try:
            event_category = EventCategory[event_key]
        except KeyError:
            event_category = EventCategory.unknown
        # Evidence still from the retained source text, never fabricated.
        kw = [
            p
            for p in EVENT_PATTERNS.get(event_category, ())
            if re.search(p, item.text.lower())
        ]
        event_excerpts = sentence_excerpts(item.text, kw, EvidenceSupports.event)
        method_version_event = "zero-shot-nli-0.1"
    elif event_backend == "hybrid":
        from app.nlp.events import classify_event_hybrid

        event_category, event_excerpts = classify_event_hybrid(item.text)
        method_version_event = "hybrid-kw+nli-0.1"
    else:
        event_category, event_excerpts = classify_event(item.text)
        method_version_event = None
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
    if method_version_event:
        method_version = f"{method_version}+{method_version_event}"

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
