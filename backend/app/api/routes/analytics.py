import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.supply_chain import SupplyChain
from app.models.user import User
from app.schemas.analytics import ChainAnalytics, ExecutiveSummary, GlobalAnalytics
from app.services.analytics_service import get_chain_analytics, get_global_analytics
from app.services.summary_service import chain_summary, global_summary

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=GlobalAnalytics)
def global_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_global_analytics(db, user.id)


@router.get("/summary/executive", response_model=ExecutiveSummary)
async def global_executive_summary(
    refresh: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = get_global_analytics(db, user.id)
    return await global_summary(str(user.id), data, force_refresh=refresh)


@router.get("/{supply_chain_id}", response_model=ChainAnalytics)
def chain_stats(
    supply_chain_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_owner(db, supply_chain_id, user)
    return get_chain_analytics(db, supply_chain_id)


@router.get("/{supply_chain_id}/executive", response_model=ExecutiveSummary)
async def chain_executive_summary(
    supply_chain_id: uuid.UUID,
    refresh: bool = Query(False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_owner(db, supply_chain_id, user)
    data = get_chain_analytics(db, supply_chain_id)
    return await chain_summary(str(supply_chain_id), data, force_refresh=refresh)


def _require_owner(db: Session, supply_chain_id: uuid.UUID, user: User) -> None:
    sc = db.get(SupplyChain, supply_chain_id)
    if sc is None:
        raise HTTPException(status_code=404, detail="Supply chain not found")
    if sc.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your supply chain")