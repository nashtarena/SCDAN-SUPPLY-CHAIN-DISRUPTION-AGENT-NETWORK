"""
Generates an executive summary paragraph from analytics data.
Uses LangChain + ChatGroq (same pattern as risk_analysis_agent).
Result is cached in Redis for 24 hours to avoid repeated LLM calls.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.logging import logger
from app.schemas.analytics import ChainAnalytics, ExecutiveSummary, GlobalAnalytics
from app.utils.cache import cache_get_json, cache_set_json

SUMMARY_CACHE_TTL = 24 * 60 * 60  # 24 hours

SYSTEM_PROMPT = """\
You are a supply chain risk analyst writing a brief executive summary.
Given the following supply chain risk statistics, write 3–4 sentences that:
- State the overall risk posture clearly
- Highlight the most critical findings
- Give one concrete recommendation

Be direct. No bullet points. Plain prose only.
"""


def _build_chain():
    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.3,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{stats_text}"),
    ])
    return prompt | llm


def _format_global(data: GlobalAnalytics) -> str:
    sev = data.severity_breakdown
    scans = data.scan_status_breakdown
    regions = ", ".join(f"{r.region} ({r.count})" for r in data.top_regions) or "none"
    return (
        f"Supply chains monitored: {data.total_supply_chains}\n"
        f"Total alerts: {data.total_alerts} "
        f"(critical={sev.critical}, high={sev.high}, medium={sev.medium}, low={sev.low})\n"
        f"Scans: completed={scans.completed}, failed={scans.failed}\n"
        f"Top affected regions: {regions}"
    )


def _format_chain(data: ChainAnalytics) -> str:
    sev = data.severity_breakdown
    regions = ", ".join(f"{r.region} ({r.count})" for r in data.top_regions) or "none"
    recent = data.scan_history[:3]
    scan_lines = "; ".join(
        f"scan {s.scan_id[:8]}… status={s.status} alerts={s.alert_count}"
        for s in recent
    ) or "no scans yet"
    return (
        f"Total alerts: {data.total_alerts} "
        f"(critical={sev.critical}, high={sev.high}, medium={sev.medium}, low={sev.low})\n"
        f"Top affected regions: {regions}\n"
        f"Recent scans: {scan_lines}"
    )


async def get_or_generate_summary(
    cache_key: str,
    stats_text: str,
    force_refresh: bool = False,
) -> ExecutiveSummary:
    if not force_refresh:
        cached = await cache_get_json(cache_key)
        if cached:
            logger.info(f"Summary cache hit: {cache_key}")
            return ExecutiveSummary(summary=cached["summary"], cached=True)

    if not settings.GROQ_API_KEY:
        return ExecutiveSummary(
            summary="Executive summary unavailable: GROQ_API_KEY not configured.",
            cached=False,
        )

    try:
        chain = _build_chain()
        result = await chain.ainvoke({"stats_text": stats_text})
        text = result.content.strip()
        await cache_set_json(cache_key, {"summary": text}, ttl_seconds=SUMMARY_CACHE_TTL)
        logger.info(f"Summary generated and cached: {cache_key}")
        return ExecutiveSummary(summary=text, cached=False)
    except Exception as exc:
        logger.error(f"Summary generation failed: {exc}")
        return ExecutiveSummary(
            summary="Executive summary could not be generated at this time.",
            cached=False,
        )


async def global_summary(
    user_id: str, data: GlobalAnalytics, force_refresh: bool = False
) -> ExecutiveSummary:
    cache_key = f"scdan:summary:global:{user_id}"
    return await get_or_generate_summary(cache_key, _format_global(data), force_refresh)


async def chain_summary(
    supply_chain_id: str, data: ChainAnalytics, force_refresh: bool = False
) -> ExecutiveSummary:
    cache_key = f"scdan:summary:chain:{supply_chain_id}"
    return await get_or_generate_summary(cache_key, _format_chain(data), force_refresh)