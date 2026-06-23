import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import joinedload

from app.agents.orchestrator import run_scan_pipeline
from app.core.database import SessionLocal
from app.core.logging import logger
from app.models.scan import Alert, ScanResult
from app.models.supply_chain import SupplyChain
from app.utils.graph_converter import supply_chain_to_graph
from app.workers.celery_app import app


def _run_async(coro):
    """
    Drive an async coroutine from a sync Celery task without relying on
    asyncio.run(), which can raise 'cannot run nested event loop' in some
    Celery worker configurations. Always creates a fresh loop.
    """
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(name="run_scan", bind=True)
def run_scan(self, scan_result_id: str) -> dict:
    """
    Celery entry point. Receives only a scan_result_id string — never
    Pydantic objects, to avoid the known JSON-serialization pitfall.
    All data is loaded fresh from Postgres inside this task.

    Status flow: pending -> running -> completed | failed.
    Idempotent: skips if already past pending.
    """
    db = SessionLocal()
    try:
        # Lock the row immediately to prevent double-processing.
        scan_result = (
            db.query(ScanResult)
            .filter(ScanResult.id == uuid.UUID(scan_result_id))
            .with_for_update()
            .first()
        )
        if scan_result is None:
            logger.error(f"run_scan: ScanResult {scan_result_id} not found.")
            return {"status": "failed", "error": "ScanResult not found"}

        if scan_result.status != "pending":
            logger.warning(
                f"run_scan: {scan_result_id} already '{scan_result.status}', skipping."
            )
            return {"status": scan_result.status, "skipped": True}

        scan_result.status = "running"
        scan_result.started_at = datetime.now(timezone.utc)
        db.commit()

        # BUG FIX: db.get() does NOT load relationships. Use joinedload so
        # supply_chain.nodes and supply_chain.edges are populated before
        # passing to supply_chain_to_graph(). Without this, graph is always
        # empty and no alerts are ever written.
        supply_chain = (
            db.query(SupplyChain)
            .options(
                joinedload(SupplyChain.nodes),
                joinedload(SupplyChain.edges),
            )
            .filter(SupplyChain.id == scan_result.supply_chain_id)
            .first()
        )
        if supply_chain is None:
            _mark_failed(db, scan_result, "Supply chain not found")
            return {"status": "failed", "error": "Supply chain not found"}

        graph = supply_chain_to_graph(supply_chain)
        logger.info(
            f"run_scan: scan {scan_result_id} | supply chain {supply_chain.id} "
            f"| {len(graph.nodes)} node(s) | {len(graph.edges)} edge(s)"
        )

        result = _run_async(
            run_scan_pipeline(nodes=graph.nodes, edges=graph.edges)
        )

        _persist_alerts(db, scan_result, result)

        scan_result.status = "completed"
        scan_result.completed_at = datetime.now(timezone.utc)
        scan_result.timing = result["timing"]
        db.commit()

        logger.info(f"run_scan: {scan_result_id} completed. timing={result['timing']}")
        return {"status": "completed", "timing": result["timing"]}

    except Exception as exc:
        logger.error(f"run_scan: {scan_result_id} failed: {exc}", exc_info=True)
        db.rollback()
        # Re-fetch without lock for the failure update.
        sr = db.get(ScanResult, uuid.UUID(scan_result_id))
        if sr is not None:
            _mark_failed(db, sr, str(exc))
        return {"status": "failed", "error": str(exc)}

    finally:
        db.close()


def _mark_failed(db, scan_result: ScanResult, error_message: str) -> None:
    scan_result.status = "failed"
    scan_result.completed_at = datetime.now(timezone.utc)
    scan_result.error_message = error_message
    db.commit()


def _persist_alerts(db, scan_result: ScanResult, result: dict) -> None:
    """
    One Alert per reroute suggestion (per impacted node).
    Skipped if no impacts were produced (empty graph, agent failures, etc).
    """
    classifications = result.get("classifications", [])
    impacts = result.get("impacts", [])
    suggestions = result.get("reroute_suggestions", [])

    if not suggestions:
        logger.info("run_scan: no reroute suggestions to persist as alerts.")
        return

    impacts_by_node_id = {impact.node_id: impact for impact in impacts}

    for suggestion in suggestions:
        impact = impacts_by_node_id.get(suggestion.node_id)
        if impact is None or not (0 <= impact.disruption_index < len(classifications)):
            continue
        classification = classifications[impact.disruption_index]

        alert = Alert(
            scan_result_id=scan_result.id,
            supply_chain_id=scan_result.supply_chain_id,
            node_id=uuid.UUID(suggestion.node_id),
            severity=classification.severity,
            category=classification.category,
            region=classification.affected_region,
            message=suggestion.suggestion,
        )
        db.add(alert)

    db.commit()
    logger.info(f"run_scan: persisted {len(suggestions)} alert(s).")
