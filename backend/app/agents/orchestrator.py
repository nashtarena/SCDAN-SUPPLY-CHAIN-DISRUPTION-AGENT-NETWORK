import asyncio
import time

from app.agents.ingestion.disaster_agent import fetch_disaster_signals
from app.agents.ingestion.news_agent import fetch_news_signals
from app.agents.ingestion.weather_agent import fetch_weather_signals
from app.agents.risk_analysis_agent import classify_disruptions
from app.core.logging import logger
from app.schemas.disruption import DisruptionSignal
from app.schemas.risk import ClassifiedDisruption


async def run_ingestion_phase() -> list[DisruptionSignal]:
    """
    Runs all ingestion agents concurrently with asyncio.gather(return_exceptions=True),
    so one agent failing never blocks the others. Acts as a synchronization barrier:
    nothing downstream starts until every agent has finished (succeeded or failed).
    """
    start = time.perf_counter()

    results = await asyncio.gather(
        fetch_news_signals(),
        fetch_weather_signals(),
        fetch_disaster_signals(),
        return_exceptions=True,
    )

    agent_names = ["news_agent", "weather_agent", "disaster_agent"]
    merged: list[DisruptionSignal] = []

    for name, result in zip(agent_names, results):
        if isinstance(result, Exception):
            # Should not normally happen, since each agent already catches its own
            # errors and returns []. This is a last-resort safety net.
            logger.error(f"Orchestrator: {name} raised unexpectedly: {result}")
            continue
        logger.info(f"Orchestrator: {name} returned {len(result)} signal(s).")
        merged.extend(result)

    elapsed = time.perf_counter() - start
    logger.info(
        f"Orchestrator: ingestion phase complete in {elapsed:.2f}s, "
        f"{len(merged)} total signal(s) from {len(agent_names)} agents."
    )

    return merged


async def run_scan_pipeline() -> dict:
    """
    Entry point for a full scan. Runs ingestion, then risk analysis.
    Mapper/reroute phases plug in here in later modules without changing
    this function's external contract.
    """
    ingestion_start = time.perf_counter()
    signals = await run_ingestion_phase()
    ingestion_elapsed = time.perf_counter() - ingestion_start

    analysis_start = time.perf_counter()
    classifications: list[ClassifiedDisruption] = await classify_disruptions(signals)
    analysis_elapsed = time.perf_counter() - analysis_start
    logger.info(
        f"Orchestrator: analysis phase complete in {analysis_elapsed:.2f}s, "
        f"{len(classifications)} classification(s)."
    )

    return {
        "signals": signals,
        "classifications": classifications,
        "timing": {
            "ingestion_seconds": round(ingestion_elapsed, 2),
            "analysis_seconds": round(analysis_elapsed, 2),
        },
    }