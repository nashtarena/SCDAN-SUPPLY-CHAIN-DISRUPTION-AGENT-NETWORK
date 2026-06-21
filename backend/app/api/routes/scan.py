import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.logging import logger
from app.models.scan import ScanResult
from app.models.supply_chain import SupplyChain
from app.models.user import User
from app.schemas.scan import ScanQueuedOut, ScanResultOut, ScanTriggerRequest
from app.workers.tasks import run_scan

router = APIRouter(prefix="/api/scans", tags=["scans"])


@router.post("", response_model=ScanQueuedOut, status_code=status.HTTP_201_CREATED)
def trigger_scan(
    payload: ScanTriggerRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Creates a ScanResult row (status=pending) and enqueues the Celery task
    with only its id. No nodes/edges/graph data ever crosses the Celery
    boundary - the task loads everything fresh from Postgres itself.
    """
    supply_chain = db.get(SupplyChain, payload.supply_chain_id)
    if supply_chain is None:
        raise HTTPException(status_code=404, detail="Supply chain not found")
    if supply_chain.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your supply chain")

    scan_result = ScanResult(supply_chain_id=supply_chain.id, status="pending")
    db.add(scan_result)
    db.commit()
    db.refresh(scan_result)

    run_scan.delay(str(scan_result.id))
    logger.info(f"Scan {scan_result.id} queued for supply chain {supply_chain.id} by {user.email}")

    return ScanQueuedOut(scan_result_id=scan_result.id, status="queued")


@router.get("/{scan_id}", response_model=ScanResultOut)
def get_scan(
    scan_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Returns scan status, timing, and error info (if failed)."""
    scan_result = db.get(ScanResult, scan_id)
    if scan_result is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    supply_chain = db.get(SupplyChain, scan_result.supply_chain_id)
    if supply_chain is None or supply_chain.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your scan")

    return scan_result