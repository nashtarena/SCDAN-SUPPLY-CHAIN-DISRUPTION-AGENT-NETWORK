import asyncio
import uuid
from datetime import datetime, timezone

from app.agents.orchestrator import run_scan_pipeline
from app.core.database import SessionLocal
from app.core.logging import logger
from app.models.scan import Alert, ScanResult
from app.models.supply_chain import SupplyChain
from app.utils.graph_converter import supply_chain_to_graph
from app.workers.celery_app import app


@app.task(name="run_scan", bind=True)
def run_scan(self, scan_result_id: str) -> dict:
    """
    Celery entry point. Receives only a scan_result_id (a plain string) as the
    task argument - deliberately NOT Node/Edge/Pydantic objects, to avoid the
    known Celery JSON-serialization pitfall where rich objects silently
    degrade to dicts. All graph data is loaded fresh from Postgres inside
    this task.

    Status flow: pending -> running -> completed | failed.

    Idempotent-safe: if this task is somehow invoked twice for the same
    scan_result_id (retry, duplicate enqueue, etc), the second invocation
    sees status already in {"running", "completed", "failed"} and exits
    without reprocessing or double-writing alerts.
    """
    db = SessionLocal()
    try:
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
                f"run_scan: ScanResult {scan_result_id} already in status "
                f"'{scan_result.status}', skipping duplicate processing."
            )
            return {"status": scan_result.status, "skipped": True}

        scan_result.status = "running"
        scan_result.started_at = datetime.now(timezone.utc)
        db.commit()

        supply_chain = db.get(SupplyChain, scan_result.supply_chain_id)
        if supply_chain is None:
            _mark_failed(db, scan_result, "Supply chain not found")
            return {"status": "failed", "error": "Supply chain not found"}

        graph = supply_chain_to_graph(supply_chain)

        logger.info(
            f"run_scan: starting scan {scan_result_id} for supply chain "
            f"{supply_chain.id} ({len(graph.nodes)} nodes, {len(graph.edges)} edges)."
        )

        # The pipeline itself is async; Celery's worker process runs sync tasks,
        # so we drive the event loop explicitly here.
        result = asyncio.run(run_scan_pipeline(nodes=graph.nodes, edges=graph.edges))

        _persist_alerts(db, scan_result, result)

        scan_result.status = "completed"
        scan_result.completed_at = datetime.now(timezone.utc)
        scan_result.timing = result["timing"]
        db.commit()

        logger.info(f"run_scan: scan {scan_result_id} completed.")
        return {"status": "completed", "timing": result["timing"]}

    except Exception as exc:
        logger.error(f"run_scan: scan {scan_result_id} failed: {exc}")
        db.rollback()
        scan_result = db.get(ScanResult, uuid.UUID(scan_result_id))
        if scan_result is not None:
            _mark_failed(db, scan_result, str(exc))
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
    Persists one Alert per reroute suggestion (i.e. per genuinely impacted
    node). If mapping/reroute were skipped (no graph), no alerts are created.
    """
    classifications = result.get("classifications", [])
    impacts = result.get("impacts", [])
    suggestions = result.get("reroute_suggestions", [])

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