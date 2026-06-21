import asyncio
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.schemas.disruption import DisruptionSignal
from app.utils.cache import cache_get_json, cache_set_json

GEOCODE_URL = "https://api.openweathermap.org/geo/1.0/direct"
ONECALL_URL = "https://api.openweathermap.org/data/2.5/onecall"
CACHE_KEY_PREFIX = "scdan:cache:weather_agent"
GEOCODE_CACHE_TTL_SECONDS = 24 * 60 * 60  # geocoding rarely changes, cache for 24h

MAX_SIGNALS = 20
HTTP_TIMEOUT = 15

# Deterministic severity mapping. Checked against event name, tags, and description.
# Order matters: more severe keywords are checked first within each tier.
SEVERITY_EVENT_KEYWORDS = {
    "critical": ["hurricane", "cyclone", "typhoon", "tornado"],
    "high": ["flash flood", "flood", "wildfire", "blizzard"],
    "medium": ["extreme heat", "severe thunderstorm"],
}

# Fallback for OpenWeatherMap's own severity tag, used if no keyword matched.
TAG_SEVERITY_MAP = {
    "Extreme": "critical",
    "Severe": "high",
    "Moderate": "medium",
    "Minor": "low",
}


def _guess_severity(event: str, tags: list[str], description: str) -> str:
    """
    Deterministic severity guess from event name, tags, and description combined.
    No LLM is used. Falls back to OpenWeatherMap's own tag, then to 'medium'.
    """
    haystack = " ".join([event or "", " ".join(tags or []), description or ""]).lower()

    for severity, keywords in SEVERITY_EVENT_KEYWORDS.items():
        if any(kw in haystack for kw in keywords):
            return severity

    if tags:
        mapped = TAG_SEVERITY_MAP.get(tags[0])
        if mapped:
            return mapped

    return "medium"


def _parse_alert_timestamp(value) -> datetime | None:
    """OpenWeatherMap alert 'start'/'end' are unix timestamps (seconds). Returns None if invalid."""
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


async def _geocode(client: httpx.AsyncClient, region: str) -> tuple[float, float] | None:
    """Resolve a region string to (lat, lon), cached for 24h since geocoding rarely changes."""
    cache_key = f"{CACHE_KEY_PREFIX}:geocode:{region}"

    cached = await cache_get_json(cache_key)
    if cached is not None:
        logger.info(f"Weather Agent: geocode cache hit for '{region}'.")
        return cached["lat"], cached["lon"]

    logger.info(f"Weather Agent: geocode cache miss for '{region}', calling API.")
    params = {"q": region, "limit": 1, "appid": settings.OPENWEATHERMAP_KEY}
    resp = await client.get(GEOCODE_URL, params=params)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return None

    lat, lon = data[0]["lat"], data[0]["lon"]
    await cache_set_json(cache_key, {"lat": lat, "lon": lon}, ttl_seconds=GEOCODE_CACHE_TTL_SECONDS)
    return lat, lon


def _alert_to_signal(alert: dict, region: str, lat: float, lon: float) -> DisruptionSignal | None:
    event = alert.get("event")
    description = alert.get("description") or ""
    tags = alert.get("tags") or []

    if not event or not description.strip():
        return None

    timestamp = _parse_alert_timestamp(alert.get("start"))
    if timestamp is None:
        return None

    severity = _guess_severity(event, tags, description)

    compact_raw_data = {
        "event": event,
        "sender_name": alert.get("sender_name"),
        "start": alert.get("start"),
        "end": alert.get("end"),
        "tags": tags,
        "coordinates": [lat, lon],
        "region": region,
    }

    try:
        return DisruptionSignal(
            source="weather",
            region=region,
            description=f"{event}: {description[:300]}",
            severity_hint=severity,
            timestamp=timestamp,
            raw_data=compact_raw_data,
        )
    except Exception as exc:
        logger.warning(f"Weather Agent: skipping malformed alert for '{region}': {exc}")
        return None


async def _fetch_alerts_for_region(client: httpx.AsyncClient, region: str) -> list[DisruptionSignal]:
    signals: list[DisruptionSignal] = []
    try:
        coords = await _geocode(client, region)
        if coords is None:
            logger.warning(f"Weather Agent: could not geocode region '{region}'.")
            return []
        lat, lon = coords

        params = {
            "lat": lat,
            "lon": lon,
            "exclude": "minutely,hourly,daily",
            "appid": settings.OPENWEATHERMAP_KEY,
        }
        resp = await client.get(ONECALL_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        for alert in data.get("alerts", []):
            signal = _alert_to_signal(alert, region, lat, lon)
            if signal is not None:
                signals.append(signal)

        logger.info(f"Weather Agent: region '{region}' succeeded with {len(signals)} alert(s).")

    except Exception as exc:
        logger.warning(f"Weather Agent: region '{region}' failed: {exc}")

    return signals


async def fetch_weather_signals() -> list[DisruptionSignal]:
    """
    Fetch extreme-weather alerts for watched regions (app.core.config.settings.WATCHED_REGIONS).
    Failure-safe: returns [] on total failure. Deterministic only - no LLM is used here.
    """

    if not settings.OPENWEATHERMAP_KEY:
        logger.warning("Weather Agent: OPENWEATHERMAP_KEY not set, skipping.")
        return []

    watched_regions = settings.WATCHED_REGIONS
    logger.info(f"Weather Agent: watching {len(watched_regions)} region(s): {watched_regions}")

    cache_key = f"{CACHE_KEY_PREFIX}:signals"
    cached = await cache_get_json(cache_key)
    if cached is not None:
        logger.info("Weather Agent: serving from cache.")
        return [DisruptionSignal(**item) for item in cached]

    signals: list[DisruptionSignal] = []
    succeeded_regions: list[str] = []
    failed_regions: list[str] = []

    try:
        timeout = httpx.Timeout(HTTP_TIMEOUT)
        async with httpx.AsyncClient(timeout=timeout) as client:
            results = await asyncio.gather(
                *(_fetch_alerts_for_region(client, region) for region in watched_regions),
                return_exceptions=True,
            )

        for region, result in zip(watched_regions, results):
            if isinstance(result, Exception):
                logger.warning(f"Weather Agent: region '{region}' task raised {result}")
                failed_regions.append(region)
                continue
            if result:
                succeeded_regions.append(region)
            signals.extend(result)

        signals.sort(key=lambda s: s.timestamp, reverse=True)
        signals = signals[:MAX_SIGNALS]

        await cache_set_json(cache_key, [s.model_dump() for s in signals])
        logger.info(
            f"Weather Agent: done. succeeded={succeeded_regions} "
            f"failed={failed_regions} alerts_returned={len(signals)}"
        )

    except Exception as exc:
        logger.error(f"Weather Agent failed: {exc}")
        return []

    return signals