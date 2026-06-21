import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.scan import Alert
from app.models.supply_chain import SupplyChain
from app.models.user import User
from app.schemas.scan import AlertOut

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("/{supply_chain_id}", response_model=list[AlertOut])
def list_alerts(
    supply_chain_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    supply_chain = db.get(SupplyChain, supply_chain_id)
    if supply_chain is None:
        raise HTTPException(status_code=404, detail="Supply chain not found")
    if supply_chain.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your supply chain")

    return (
        db.query(Alert)
        .filter(Alert.supply_chain_id == supply_chain_id)
        .order_by(desc(Alert.created_at))
        .all()
    )