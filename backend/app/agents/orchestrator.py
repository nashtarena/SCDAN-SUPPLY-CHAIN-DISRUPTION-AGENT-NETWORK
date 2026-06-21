import asyncio
import time

from app.agents.ingestion.disaster_agent import fetch_disaster_signals
from app.agents.ingestion.news_agent import fetch_news_signals
from app.agents.ingestion.weather_agent import fetch_weather_signals
from app.agents.reroute_agent import generate_reroute_suggestions
from app.agents.risk_analysis_agent import classify_disruptions
from app.agents.supply_chain_mapper_agent import map_disruptions_to_nodes
from app.core.logging import logger
from app.schemas.disruption import DisruptionSignal
from app.schemas.graph import Edge, Node
from app.schemas.mapping import NodeImpact
from app.schemas.reroute import RerouteSuggestion
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


async def run_scan_pipeline(
    nodes: list[Node] | None = None,
    edges: list[Edge] | None = None,
) -> dict:
    """
    Entry point for a full scan: ingestion -> analysis -> mapping -> reroute.

    `nodes`/`edges` represent the target supply chain's graph. This is the
    one place pipeline data crosses a serialization boundary (e.g. a Celery
    task that received JSON-deserialized dicts instead of Node/Edge
    instances), so we defensively re-validate here. Everything downstream of
    this point can safely assume real Node/Edge objects.
    """
    if nodes:
        nodes = [n if isinstance(n, Node) else Node.model_validate(n) for n in nodes]
    if edges:
        edges = [e if isinstance(e, Edge) else Edge.model_validate(e) for e in edges]

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

    impacts: list[NodeImpact] = []
    suggestions: list[RerouteSuggestion] = []
    mapping_elapsed = 0.0
    reroute_elapsed = 0.0

    if nodes:
        mapping_start = time.perf_counter()
        impacts = await map_disruptions_to_nodes(nodes, classifications)
        mapping_elapsed = time.perf_counter() - mapping_start
        logger.info(
            f"Orchestrator: mapping phase complete in {mapping_elapsed:.2f}s, "
            f"{len(impacts)} impact(s)."
        )

        reroute_start = time.perf_counter()
        suggestions = await generate_reroute_suggestions(
            impacts, classifications, nodes, edges or []
        )
        reroute_elapsed = time.perf_counter() - reroute_start
        logger.info(
            f"Orchestrator: reroute phase complete in {reroute_elapsed:.2f}s, "
            f"{len(suggestions)} suggestion(s)."
        )
    else:
        logger.info("Orchestrator: no supply chain graph provided, skipping mapping/reroute phases.")

    return {
        "signals": signals,
        "classifications": classifications,
        "impacts": impacts,
        "reroute_suggestions": suggestions,
        "timing": {
            "ingestion_seconds": round(ingestion_elapsed, 2),
            "analysis_seconds": round(analysis_elapsed, 2),
            "mapping_seconds": round(mapping_elapsed, 2),
            "reroute_seconds": round(reroute_elapsed, 2),
        },
    }