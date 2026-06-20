import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.logging import logger
from app.models.supply_chain import SupplyChain, SupplyChainEdge, SupplyChainNode
from app.models.user import User
from app.schemas.supply_chains import (
    EdgeCreate,
    EdgeOut,
    NodeCreate,
    NodeOut,
    SupplyChainCreate,
    SupplyChainDetailOut,
    SupplyChainOut,
    SupplyChainUpdate,
)

router = APIRouter(prefix="/api/supply-chains", tags=["supply-chains"])


def _get_owned_supply_chain(
    supply_chain_id: uuid.UUID, db: Session, user: User
) -> SupplyChain:
    sc = db.get(SupplyChain, supply_chain_id)
    if sc is None:
        raise HTTPException(status_code=404, detail="Supply chain not found")
    if sc.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your supply chain")
    return sc


# ---------- SupplyChain CRUD ----------

@router.post("", response_model=SupplyChainOut, status_code=status.HTTP_201_CREATED)
def create_supply_chain(
    payload: SupplyChainCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sc = SupplyChain(owner_id=user.id, name=payload.name, description=payload.description)
    db.add(sc)
    db.commit()
    db.refresh(sc)
    logger.info(f"Supply chain created: {sc.id} by {user.email}")
    return sc


@router.get("", response_model=list[SupplyChainOut])
def list_supply_chains(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return db.query(SupplyChain).filter(SupplyChain.owner_id == user.id).all()


@router.get("/{supply_chain_id}", response_model=SupplyChainDetailOut)
def get_supply_chain(
    supply_chain_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sc = (
        db.query(SupplyChain)
        .options(joinedload(SupplyChain.nodes), joinedload(SupplyChain.edges))
        .filter(SupplyChain.id == supply_chain_id)
        .first()
    )
    if sc is None:
        raise HTTPException(status_code=404, detail="Supply chain not found")
    if sc.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your supply chain")
    return sc


@router.patch("/{supply_chain_id}", response_model=SupplyChainOut)
def update_supply_chain(
    supply_chain_id: uuid.UUID,
    payload: SupplyChainUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sc = _get_owned_supply_chain(supply_chain_id, db, user)
    if payload.name is not None:
        sc.name = payload.name
    if payload.description is not None:
        sc.description = payload.description
    db.commit()
    db.refresh(sc)
    return sc


@router.delete("/{supply_chain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supply_chain(
    supply_chain_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sc = _get_owned_supply_chain(supply_chain_id, db, user)
    db.delete(sc)
    db.commit()
    logger.info(f"Supply chain deleted: {supply_chain_id} by {user.email}")
    return None


# ---------- Node CRUD ----------

@router.post(
    "/{supply_chain_id}/nodes",
    response_model=NodeOut,
    status_code=status.HTTP_201_CREATED,
)
def add_node(
    supply_chain_id: uuid.UUID,
    payload: NodeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_supply_chain(supply_chain_id, db, user)
    node = SupplyChainNode(supply_chain_id=supply_chain_id, **payload.model_dump())
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


@router.delete("/{supply_chain_id}/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_node(
    supply_chain_id: uuid.UUID,
    node_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_supply_chain(supply_chain_id, db, user)
    node = db.get(SupplyChainNode, node_id)
    if node is None or node.supply_chain_id != supply_chain_id:
        raise HTTPException(status_code=404, detail="Node not found")
    db.delete(node)
    db.commit()
    return None


# ---------- Edge CRUD ----------

@router.post(
    "/{supply_chain_id}/edges",
    response_model=EdgeOut,
    status_code=status.HTTP_201_CREATED,
)
def add_edge(
    supply_chain_id: uuid.UUID,
    payload: EdgeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_supply_chain(supply_chain_id, db, user)

    for node_id in (payload.source_node_id, payload.target_node_id):
        node = db.get(SupplyChainNode, node_id)
        if node is None or node.supply_chain_id != supply_chain_id:
            raise HTTPException(
                status_code=400, detail=f"Node {node_id} does not belong to this supply chain"
            )

    edge = SupplyChainEdge(supply_chain_id=supply_chain_id, **payload.model_dump())
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge


@router.delete("/{supply_chain_id}/edges/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_edge(
    supply_chain_id: uuid.UUID,
    edge_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_supply_chain(supply_chain_id, db, user)
    edge = db.get(SupplyChainEdge, edge_id)
    if edge is None or edge.supply_chain_id != supply_chain_id:
        raise HTTPException(status_code=404, detail="Edge not found")
    db.delete(edge)
    db.commit()
    return None