from fastapi import APIRouter
from app.agents.orchestrator import run_scan_pipeline

router = APIRouter(prefix="/debug", tags=["Debug"])

@router.get("/pipeline")
async def test_pipeline():
    result = await run_scan_pipeline()

    return {
        "count": len(result["signals"]),
        "timing": result["timing"],
        "signals": [s.model_dump() for s in result["signals"]],
    }