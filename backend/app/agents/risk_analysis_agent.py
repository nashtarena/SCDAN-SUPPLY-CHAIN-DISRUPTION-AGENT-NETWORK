"""
Risk Analysis Agent.

Takes a batch of DisruptionSignal (from the ingestion agents) and asks the LLM
to classify each one into a ClassifiedDisruption. Built with LangChain LCEL:

    prompt (ChatPromptTemplate) | llm.with_structured_output(ClassifiedDisruptionBatch)

This is intentionally NOT raw httpx - LangChain provides the structured-output
parsing, retry surface, and a swappable LLM layer (ChatGroq today, anything
LangChain supports tomorrow) without changing this agent's logic.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.logging import logger
from app.schemas.disruption import DisruptionSignal
from app.schemas.risk import ClassifiedDisruption, ClassifiedDisruptionBatch

llm = ChatGroq(
    model=settings.GROQ_MODEL,
    api_key=settings.GROQ_API_KEY,
    temperature=0,
)
structured_llm = llm.with_structured_output(ClassifiedDisruptionBatch)

SYSTEM_PROMPT = """\
You are a supply chain risk analyst. You will be given a numbered list of \
disruption signals gathered from news, weather, and disaster-monitoring sources.

For EACH signal, produce one classification with:
- affected_region: the region/country the disruption affects
- severity: one of low, medium, high, critical
- estimated_duration_days: your best estimate of how many days this disruption \
will keep affecting operations
- confidence_score: your confidence in this classification, from 0.0 to 1.0
- category: a short label such as labor, weather, geopolitical, infrastructure, \
or similar

Return exactly one classification per signal, in the same order the signals \
were given. Do not skip or merge any signal.
"""

RETRY_SYSTEM_PROMPT = SYSTEM_PROMPT + """
IMPORTANT: Your previous response was invalid (wrong format or wrong number of \
items). You MUST return exactly {expected_count} classifications, one per \
signal, in the same order.
"""


def _format_signals_text(signals: list[DisruptionSignal]) -> str:
    lines = []
    for i, s in enumerate(signals, start=1):
        ts = (
            s.timestamp.isoformat()
            if hasattr(s.timestamp, "isoformat") 
            else str(s.timestamp)
        )
        lines.append(
            f"{i}. source={s.source} | region={s.region} | "
            f"severity_hint={s.severity_hint} | timestamp={ts} | "
            f"description={s.description}"
        )
    return "\n".join(lines)


def _build_chain(system_prompt: str):
    """Builds the LCEL RunnableSequence: prompt -> structured-output LLM."""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{signals_text}"),
        ]
    )

    return prompt | structured_llm  # LCEL RunnableSequence


def _fallback_classification(signal: DisruptionSignal) -> ClassifiedDisruption:
    """
    Never trust the LLM blindly. If classification fails entirely, fall back to
    a conservative, deterministic classification derived from the agent's own
    severity_hint so the pipeline can still proceed.
    """
    return ClassifiedDisruption(
        affected_region=signal.region,
        severity=signal.severity_hint if signal.severity_hint in (
            "low", "medium", "high", "critical"
        ) else "medium",
        estimated_duration_days=1,
        confidence_score=0.0,
        category="unclassified",
    )


async def classify_disruptions(
    signals: list[DisruptionSignal],
) -> list[ClassifiedDisruption]:
    """
    Classify a batch of DisruptionSignal via LangChain + ChatGroq.

    Failure-safe: retries once on malformed/mismatched output, then falls back
    to deterministic per-signal classifications. Never raises.
    """
    if not signals:
        return []

    if not settings.GROQ_API_KEY:
        logger.warning("Risk Analysis Agent: GROQ_API_KEY not set, using fallback classifications.")
        return [_fallback_classification(s) for s in signals]

    signals_text = _format_signals_text(signals)

    # Attempt 1
    try:
        chain = _build_chain(SYSTEM_PROMPT)
        result: ClassifiedDisruptionBatch = await chain.ainvoke({"signals_text": signals_text})
        if len(result.items) == len(signals):
            logger.info(f"Risk Analysis Agent: classified {len(result.items)} signal(s) on first attempt.")
            return result.items
        logger.warning(
            f"Risk Analysis Agent: attempt 1 returned {len(result.items)} items, "
            f"expected {len(signals)}. Retrying."
        )
    except Exception as exc:
        logger.warning(f"Risk Analysis Agent: attempt 1 failed: {exc}. Retrying.")

    # Attempt 2 (retry once, per spec)
    try:
        retry_prompt = RETRY_SYSTEM_PROMPT.format(expected_count=len(signals))
        chain = _build_chain(retry_prompt)
        result = await chain.ainvoke({"signals_text": signals_text})
        if len(result.items) == len(signals):
            logger.info(f"Risk Analysis Agent: classified {len(result.items)} signal(s) on retry.")
            return result.items
        logger.error(
            f"Risk Analysis Agent: retry returned {len(result.items)} items, "
            f"expected {len(signals)}. Falling back."
        )
    except Exception as exc:
        logger.error(f"Risk Analysis Agent: retry failed: {exc}. Falling back.")

    # Fallback: deterministic, never crashes the pipeline.
    return [_fallback_classification(s) for s in signals]