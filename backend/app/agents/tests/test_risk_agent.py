import asyncio
from app.agents.risk_analysis_agent import classify_disruptions
from app.schemas.disruption import DisruptionSignal

async def run_test():
    test_input = [
        DisruptionSignal.model_construct(
            source="news",
            region=None,
            severity_hint="unknown",
            timestamp="broken",
            description=None
        )
    ]

    result = await classify_disruptions(test_input)
    print(result)

asyncio.run(run_test())