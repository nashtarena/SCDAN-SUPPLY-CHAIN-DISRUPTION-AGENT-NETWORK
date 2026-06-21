from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.schemas.disruption import DisruptionSignal
from app.utils.cache import cache_get_json, cache_set_json

NEWSAPI_URL = "https://newsapi.org/v2/everything"
CACHE_KEY = "scdan:cache:news_agent:signals"

MAX_SIGNALS = 50
MAX_ARTICLE_AGE_HOURS = 48

DISRUPTION_KEYWORDS = [
    "supply chain",
    "port strike",
    "dock strike",
    "shipping delay",
    "port closure",
    "factory fire",
    "factory shutdown",
    "embargo",
    "logistics disruption",
    "container shortage",
    "semiconductor shortage",
    "rail strike",
    "flood",
    "cyclone",
    "hurricane",
    "earthquake",
    "wildfire",
]

SEVERITY_KEYWORDS = {
    "critical": [
        "embargo",
        "explosion",
        "shutdown",
        "earthquake",
        "hurricane",
        "cyclone",
    ],
    "high": [
        "strike",
        "fire",
        "blockade",
        "closure",
        "wildfire",
        "flood",
    ],
    "medium": [
        "delay",
        "congestion",
        "shortage",
        "disruption",
    ],
}


def _guess_severity(text: str) -> str:
    """Deterministic keyword-based severity guess. No LLM involved here."""
    text_lower = text.lower()
    for severity, words in SEVERITY_KEYWORDS.items():
        if any(w in text_lower for w in words):
            return severity
    return "low"


def _parse_published_at(value: str | None) -> datetime:
    """NewsAPI dates look like '2026-06-19T10:00:00Z'. Fall back to now() if missing/bad."""
    if not value:
        return datetime.now(timezone.utc)
    try:
        cleaned = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime.now(timezone.utc)


def _is_recent(published_at: datetime) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_ARTICLE_AGE_HOURS)
    return published_at >= cutoff


def _has_meaningful_content(title: str, description: str) -> bool:
    """Skip articles with no usable title/description (e.g. '[Removed]' placeholders)."""
    title = (title or "").strip()
    description = (description or "").strip()
    if not title and not description:
        return False
    if title.lower() in {"[removed]", "removed"}:
        return False
    return True


def _article_to_signal(article: dict) -> DisruptionSignal | None:
    title = article.get("title") or ""
    description = article.get("description") or title
    url = article.get("url")

    if not _has_meaningful_content(title, description):
        return None

    published_at = _parse_published_at(article.get("publishedAt"))
    if not _is_recent(published_at):
        return None

    compact_raw_data = {
        "title": title,
        "source": (article.get("source") or {}).get("name", "unknown"),
        "url": url,
        "published_at": article.get("publishedAt"),
    }

    try:
        return DisruptionSignal(
            source="news",
            region="Unknown",  # Region extraction happens later, during the analysis phase.
            description=description,
            severity_hint=_guess_severity(title + " " + description),
            timestamp=published_at,
            raw_data=compact_raw_data,
        )
    except Exception as exc:
        logger.warning(f"News Agent: skipping malformed article: {exc}")
        return None


async def fetch_news_signals() -> list[DisruptionSignal]:
    """Fetch disruption-related news. Failure-safe: returns [] on any error."""

    if not settings.NEWSAPI_KEY:
        logger.warning("News Agent: NEWSAPI_KEY not set, skipping.")
        return []

    cached = await cache_get_json(CACHE_KEY)
    if cached is not None:
        logger.info("News Agent: serving from cache.")
        return [DisruptionSignal(**item) for item in cached]

    query = " OR ".join(f'"{kw}"' for kw in DISRUPTION_KEYWORDS)
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 100,
        "apiKey": settings.NEWSAPI_KEY,
    }

    signals: list[DisruptionSignal] = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(NEWSAPI_URL, params=params)
            response.raise_for_status()
            data = response.json()

        seen_urls: set[str] = set()
        for article in data.get("articles", []):
            url = article.get("url")
            if url and url in seen_urls:
                continue

            signal = _article_to_signal(article)
            if signal is None:
                continue

            if url:
                seen_urls.add(url)
            signals.append(signal)

        signals.sort(key=lambda s: s.timestamp, reverse=True)
        signals = signals[:MAX_SIGNALS]

        await cache_set_json(CACHE_KEY, [s.model_dump() for s in signals])
        logger.info(f"News Agent: fetched {len(signals)} signals.")

    except Exception as exc:
        # Agent must never crash the orchestrator. Log and return what we have (possibly nothing).
        logger.error(f"News Agent failed: {exc}")
        return []

    return signals