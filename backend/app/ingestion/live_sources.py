"""Live data sources: SEC EDGAR, GDELT, StockTwits, Reddit, and yfinance.

All free, keyless (AGENTS.md "Data Influx"). Uses stdlib urllib to avoid new
dependencies; yfinance is already a dependency. Each fetcher returns normalized
RawSourceItem objects (news/social) or raw price quotes, ready for the pipeline.

GDELT enforces >=1 request / 5s; we throttle client-side with a module lock so
concurrent pollers cannot trip the rate limit.
"""

import json
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
import re
from datetime import datetime, timezone

from app.core.entities import COMPANIES
from app.core.signal_contract import SourceType
from app.ingestion.adapters import RawSourceItem
from app.ingestion.retry import request_with_backoff

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
RSS_FEEDS = {
    "apple": "https://www.apple.com/newsroom/rss-feed.rss",
    "microsoft": "https://news.microsoft.com/feed/",
    "exxon": "https://corporate.exxonmobil.com/news/news-releases/rss",
    "pfizer": "https://www.pfizer.com/news/rss.xml",
}
STOCKTWITS_URL = "https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
REDDIT_RSS_URL = "https://www.reddit.com/r/stocks/search.rss"
GDELT_MIN_INTERVAL = 6.0  # seconds between requests (GDELT asks for >=5s; be safe)
USER_AGENT = "risk-engine-hackathon/0.1 (educational demo)"
SEC_CIKS = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "JPM": "0000019617",
    "XOM": "0000034088",
    "PG": "0000080424",
    "KO": "0000021344",
    "JNJ": "0000200406",
    "WMT": "0000104169",
    "CVX": "0000093410",
    "PFE": "0000078003",
}

_gdelt_lock = threading.Lock()
_gdelt_last = 0.0

_TIMEOUT = 15


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    response = request_with_backoff(
        lambda timeout: urllib.request.urlopen(req, timeout=timeout),
        timeout=_TIMEOUT,
    )
    with response as resp:
        return json.loads(resp.read().decode("utf-8"))


def _throttle_gdelt() -> None:
    global _gdelt_last
    with _gdelt_lock:
        wait = GDELT_MIN_INTERVAL - (time.time() - _gdelt_last)
        if wait > 0:
            time.sleep(wait)
        _gdelt_last = time.time()


def fetch_gdelt_news(query: str, max_records: int = 10) -> list[RawSourceItem]:
    """Live news headlines from GDELT DOC 2.0 (free, no key).

    Returns normalized news RawSourceItems. Raises on network/parse failure so
    callers can degrade gracefully (never silently fabricate).
    """
    _throttle_gdelt()
    params = urllib.parse.urlencode(
        {
            "query": query,
            "mode": "artlist",
            "maxrecords": max_records,
            "format": "json",
            "sort": "datedesc",
        }
    )
    data = _get_json(f"{GDELT_URL}?{params}")
    articles = data.get("articles", [])
    items: list[RawSourceItem] = []
    for i, a in enumerate(articles):
        title = (a.get("title") or "").strip()
        if not title:
            continue
        # GDELT seendate is YYYYMMDDTHHMMSSZ
        published = _parse_gdelt_date(a.get("seendate"))
        items.append(
            RawSourceItem(
                provider="gdelt",
                source_type=SourceType.news,
                external_id=a.get("url") or f"gdelt-{i}-{title[:24]}",
                text=title,
                url=a.get("url"),
                published_at=published,
            )
        )
    return items


def fetch_sec_filings(
    ticker: str,
    max_records: int = 5,
    forms: tuple[str, ...] = ("8-K", "10-Q", "10-K"),
) -> list[RawSourceItem]:
    """Fetch recent company filings from SEC EDGAR submissions.

    The submissions JSON is public and keyless. Only filing metadata and the
    SEC-provided filing URL are retained; the filing body is not redistributed.
    """
    cik = SEC_CIKS.get(ticker.upper())
    if cik is None:
        raise ValueError(f"unsupported SEC ticker: {ticker}")
    data = _get_json(SEC_SUBMISSIONS_URL.format(cik=cik))
    recent = (data.get("filings") or {}).get("recent") or {}
    rows: list[RawSourceItem] = []
    for index, form in enumerate(recent.get("form") or []):
        if form not in forms:
            continue
        accession = (recent.get("accessionNumber") or [])[index]
        primary_document = (recent.get("primaryDocument") or [])[index]
        filing_date = (recent.get("filingDate") or [])[index]
        accession_path = accession.replace("-", "")
        url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            f"{accession_path}/{primary_document}"
        )
        company_name = data.get("name") or ticker.upper()
        text = f"{company_name} filed {form} with the SEC on {filing_date}."
        rows.append(
            RawSourceItem(
                provider="sec:edgar",
                source_type=SourceType.news,
                external_id=f"sec:{cik}:{accession}",
                text=text,
                url=url,
                published_at=_parse_date(filing_date),
            )
        )
        if len(rows) >= max_records:
            break
    return rows


def fetch_public_rss(provider: str, url: str, limit: int = 10) -> list[RawSourceItem]:
    """Fetch an explicitly allowlisted public RSS or Atom feed.

    Feed content is retained only as the normalized headline/title needed by
    the signal pipeline. Arbitrary URL fetching is intentionally unsupported.
    """
    if provider not in RSS_FEEDS or RSS_FEEDS[provider] != url:
        raise ValueError(f"RSS provider is not allowlisted: {provider}")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml"},
    )
    response = request_with_backoff(
        lambda timeout: urllib.request.urlopen(request, timeout=timeout),
        timeout=_TIMEOUT,
    )
    with response as resp:
        root = ET.fromstring(resp.read())
    items: list[RawSourceItem] = []
    atom_ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall(".//item") or root.findall("atom:entry", atom_ns)
    for index, entry in enumerate(entries[:limit]):
        title = (
            entry.findtext("title", default="")
            or entry.findtext("atom:title", default="", namespaces=atom_ns)
        ).strip()
        if not title:
            continue
        link_node = entry.find("link")
        atom_link = entry.find("atom:link", atom_ns)
        link = (
            link_node.text.strip() if link_node is not None and link_node.text else None
        ) or (atom_link.attrib.get("href") if atom_link is not None else None)
        published_raw = (
            entry.findtext("pubDate")
            or entry.findtext("published")
            or entry.findtext("updated")
            or entry.findtext("atom:published", namespaces=atom_ns)
            or entry.findtext("atom:updated", namespaces=atom_ns)
        )
        published = _parse_iso(published_raw) or _parse_rfc2822(published_raw)
        external_id = (
            entry.findtext("guid")
            or entry.findtext("atom:id", namespaces=atom_ns)
            or link
            or f"{provider}:{index}:{title}"
        )
        items.append(
            RawSourceItem(
                provider=f"rss:{provider}",
                source_type=SourceType.news,
                external_id=external_id.strip(),
                text=title,
                url=link,
                published_at=published,
            )
        )
    return items


def _parse_gdelt_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def fetch_stocktwits(symbol: str, limit: int = 20, labeled_only: bool = False) -> list[RawSourceItem]:
    """Live social posts for a symbol from StockTwits (free, no key).

    Each post carries its own Bullish/Bearish/None label; we keep the label on
    the item so downstream can cross-check NLP sentiment against the crowd label.

    labeled_only: when True, keep only posts StockTwits itself labeled
    Bullish/Bearish. Raw StockTwits is mostly ticker-spam ("$AAPL 🚀") with no
    directional signal; filtering to self-labeled posts sharply cuts the noise
    feeding the rebalancer.
    """
    data = _get_json(STOCKTWITS_URL.format(symbol=urllib.parse.quote(symbol)))
    messages = data.get("messages", [])
    items: list[RawSourceItem] = []
    for m in messages[:limit]:
        body = (m.get("body") or "").strip()
        if not body:
            continue
        sentiment = (m.get("entities") or {}).get("sentiment") or {}
        crowd_label = sentiment.get("basic")
        if labeled_only and crowd_label not in ("Bullish", "Bearish"):
            continue
        items.append(
            RawSourceItem(
                provider=f"stocktwits:{m.get('user', {}).get('username', 'anon')}",
                source_type=SourceType.social,
                external_id=str(m.get("id")),
                text=body,
                url=f"https://stocktwits.com/message/{m.get('id')}",
                published_at=_parse_iso(m.get("created_at")),
            )
        )
        # stash crowd label on the pydantic model's private notes
        items[-1].__dict__["crowd_sentiment"] = crowd_label
    return items


def fetch_reddit_rss(query: str, limit: int = 20) -> list[RawSourceItem]:
    """Fetch public r/stocks search posts through Reddit's RSS endpoint.

    Reddit's JSON API requires an application identity in many environments.
    RSS is public and keyless, but it carries no authoritative sentiment label;
    the NLP pipeline must infer sentiment from the retained title/body.
    """
    params = urllib.parse.urlencode({
        "q": query,
        "restrict_sr": "1",
        "sort": "new",
        "t": "day",
    })
    req = urllib.request.Request(
        f"{REDDIT_RSS_URL}?{params}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/atom+xml"},
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        root = ET.fromstring(resp.read())
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items: list[RawSourceItem] = []
    for entry in root.findall("atom:entry", ns)[:limit]:
        title = unescape(entry.findtext("atom:title", default="", namespaces=ns)).strip()
        if not title:
            continue
        title = re.sub(r"\s+", " ", title)
        link = entry.find("atom:link", ns)
        href = link.attrib.get("href") if link is not None else None
        published = _parse_iso(entry.findtext("atom:published", namespaces=ns))
        external_id = entry.findtext("atom:id", namespaces=ns) or href or title
        items.append(
            RawSourceItem(
                provider="reddit:r/stocks",
                source_type=SourceType.social,
                external_id=external_id,
                text=title,
                url=href,
                published_at=published,
            )
        )
    return items


def _parse_iso(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_rfc2822(raw: str | None) -> datetime | None:
    if not raw:
        return None
    from email.utils import parsedate_to_datetime

    try:
        parsed = parsedate_to_datetime(raw)
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, IndexError):
        return None


def fetch_index_symbols() -> list[str]:
    """The mock-index tickers we track live."""
    return [c.ticker for c in COMPANIES]


def fetch_live_quotes(tickers: list[str] | None = None) -> dict[str, dict]:
    """Live/near-real-time quotes via yfinance (free, no key).

    Returns {ticker: {price, previous_close, change_pct, currency, as_of}}.
    Missing tickers are omitted (never fabricated).
    """
    import yfinance as yf

    tickers = tickers or fetch_index_symbols()
    out: dict[str, dict] = {}
    for t in tickers:
        try:
            fi = yf.Ticker(t).fast_info
            price = fi.last_price
            prev = fi.previous_close
            if price is None:
                continue
            out[t] = {
                "price": float(price),
                "previous_close": float(prev) if prev is not None else None,
                "change_pct": (
                    round((float(price) - float(prev)) / float(prev) * 100, 3)
                    if prev
                    else None
                ),
                "currency": fi.currency,
                "as_of": datetime.now(timezone.utc).isoformat(),
            }
        except Exception:
            continue  # degrade gracefully; omit rather than fabricate
    return out
