from datetime import datetime, timedelta, timezone

import httpx

from app.core.logging import logger
from app.schemas.disruption import DisruptionSignal
from app.utils.cache import cache_get_json, cache_set_json

# Official GDACS (Global Disaster Alert and Coordination System) event list API.
# No API key required. Returns a GeoJSON FeatureCollection of active disaster events
# (earthquakes, floods, cyclones, droughts, wildfires, volcanoes, etc).
GDACS_EVENTS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"

CACHE_KEY = "scdan:cache:disaster_agent:signals"

MAX_SIGNALS = 50
MAX_EVENT_AGE_DAYS = 30

# GDACS alert levels: Green (minor/no impact expected), Orange (medium), Red (high impact).
ALERT_LEVEL_TO_SEVERITY = {
    "green": "low",
    "orange": "medium",
    "red": "critical",
}


def _parse_gdacs_date(value: str | None) -> datetime:
    """GDACS dates look like '2026-06-18T10:00:00'. Fall back to now() if missing/bad."""
    if not value:
        return datetime.now(timezone.utc)
    try:
        # Some GDACS dates include a 'Z' or offset, some don't - handle both.
        cleaned = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime.now(timezone.utc)


def _is_stale(props: dict, timestamp: datetime) -> bool:
    """An event is stale if GDACS no longer flags it current, or it's older than 30 days."""
    iscurrent = str(props.get("iscurrent", "")).lower()
    if iscurrent != "true":
        return True

    age_cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_EVENT_AGE_DAYS)
    if timestamp < age_cutoff:
        return True

    return False


def _feature_to_signal(feature: dict) -> DisruptionSignal | None:
    """
    Maps one GDACS GeoJSON feature -> DisruptionSignal.

    GDACS field          -> DisruptionSignal field
    ---------------------------------------------------
    properties.country /
    properties.iso3       -> region
    properties.eventtype +
    properties.name        -> description (human-readable event summary)
    properties.alertlevel  -> severity_hint (Green/Orange/Red -> low/medium/critical)
    properties.fromdate    -> timestamp
    (compact subset)        -> raw_data: event_id, event_type, country, alert_level,
                                          coordinates, report_url
    """
    props = feature.get("properties", {})

    timestamp = _parse_gdacs_date(props.get("fromdate"))

    if _is_stale(props, timestamp):
        return None

    region = props.get("country") or props.get("iso3") or "Unknown region"

    event_type = props.get("eventtype", "Disaster")
    name = props.get("name") or props.get("eventname") or "Unnamed event"
    severity_text = (props.get("severitydata") or {}).get("severitytext", "")
    description = f"{event_type} - {name}"
    if severity_text:
        description += f" ({severity_text})"

    alert_level = (props.get("alertlevel") or "").lower()
    severity_hint = ALERT_LEVEL_TO_SEVERITY.get(alert_level, "medium")

    coordinates = (feature.get("geometry") or {}).get("coordinates")
    report_url = (props.get("url") or {}).get("report")

    compact_raw_data = {
        "event_id": props.get("eventid"),
        "event_type": event_type,
        "country": region,
        "alert_level": props.get("alertlevel"),
        "coordinates": coordinates,
        "report_url": report_url,
    }

    try:
        return DisruptionSignal(
            source="disaster",
            region=region,
            description=description,
            severity_hint=severity_hint,
            timestamp=timestamp,
            raw_data=compact_raw_data,
        )
    except Exception as exc:
        # A single malformed feature must not take down the whole batch.
        logger.warning(f"Disaster Agent: skipping malformed feature: {exc}")
        return None


async def fetch_disaster_signals() -> list[DisruptionSignal]:
    """
    Fetch live disaster events from GDACS. Failure-safe: returns [] on any error,
    never raises. Same contract as the other ingestion agents.

    Filters out stale events (not current, or older than 30 days), sorts by
    newest first, and keeps only the newest 20 signals.
    """
    cached = await cache_get_json(CACHE_KEY)
    if cached is not None:
        logger.info("Disaster Agent: serving from cache.")
        return [DisruptionSignal(**item) for item in cached]

    signals: list[DisruptionSignal] = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(GDACS_EVENTS_URL)
            response.raise_for_status()
            data = response.json()

        features = data.get("features", [])
        for feature in features:
            signal = _feature_to_signal(feature)
            if signal is not None:
                signals.append(signal)

        signals.sort(key=lambda s: s.timestamp, reverse=True)
        signals = signals[:MAX_SIGNALS]

        await cache_set_json(CACHE_KEY, [s.model_dump() for s in signals])
        logger.info(f"Disaster Agent: fetched {len(signals)} signals from GDACS.")

    except Exception as exc:
        # Network failure, bad JSON, timeout, etc. Agent must never crash the orchestrator.
        logger.error(f"Disaster Agent failed: {exc}")
        return []

    return signals