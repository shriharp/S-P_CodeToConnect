"""Live data sources: GDELT (news), StockTwits (social), yfinance (prices).

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

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
STOCKTWITS_URL = "https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
REDDIT_RSS_URL = "https://www.reddit.com/r/stocks/search.rss"
GDELT_MIN_INTERVAL = 6.0  # seconds between requests (GDELT asks for >=5s; be safe)
USER_AGENT = "risk-engine-hackathon/0.1 (educational demo)"

_gdelt_lock = threading.Lock()
_gdelt_last = 0.0

_TIMEOUT = 15


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
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
    params = urllib.parse.urlencode({"q": query, "restrict_sr": "1", "sort": "new"})
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
