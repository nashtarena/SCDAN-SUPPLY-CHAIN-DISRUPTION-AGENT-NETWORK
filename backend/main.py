from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, supply_chains, scan, alerts
from app.core.config import settings
from app.core.database import Base, engine
from app.core.logging import logger

# Import all models so Base.metadata knows about them before create_all.
from app.models import user, supply_chain, scan as scan_models  # noqa: F401

app = FastAPI(title="SCDAN - Supply Chain Disruption Agent Network")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(supply_chains.router)
app.include_router(scan.router)
app.include_router(alerts.router)


@app.on_event("startup")
def on_startup():
    # MVP: auto-create tables. Swap for Alembic migrations later.
    Base.metadata.create_all(bind=engine)
    logger.info("SCDAN backend started, tables ensured.")


@app.get("/health")
def health():
    return {"status": "ok"}