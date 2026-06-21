"""
Supply Chain Mapping Agent.

Given the supply chain's nodes and a batch of ClassifiedDisruption, decides
which nodes are impacted by which disruption. Built with LangChain LCEL,
same pattern as the Risk Analysis Agent:

    prompt (ChatPromptTemplate) | llm.with_structured_output(NodeImpactBatch)

Failure-safe: if the LLM call fails or returns malformed output twice, falls
back to deterministic region-substring matching (the original MVP approach)
so the pipeline can always proceed. The LLM is never trusted blindly.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.logging import logger
from app.schemas.graph import Node
from app.schemas.mapping import NodeImpact, NodeImpactBatch
from app.schemas.risk import ClassifiedDisruption

SYSTEM_PROMPT = """\
You are a supply chain mapping analyst. You will be given:
1. A numbered list of supply chain nodes (id, name, type, region).
2. A numbered list of classified disruptions (index, affected_region, \
severity, category).

For each node that is plausibly impacted by a disruption (matching or \
overlapping region, or a region clearly nearby/related), output one impact \
record with:
- node_id: the exact id of the node
- node_name: the node's name
- disruption_index: the 0-based index of the disruption it matches
- confidence: 0.0 to 1.0
- reasoning: one short sentence

Only include nodes that are genuinely plausibly impacted. A node with no \
matching disruption should not appear in the output at all. Do not invent \
node ids or disruption indices that were not given to you.
"""

RETRY_SYSTEM_PROMPT = SYSTEM_PROMPT + """
IMPORTANT: Your previous response was invalid (bad format, or referenced a \
node_id/disruption_index that does not exist). Only use the exact ids and \
indices provided below.
"""


def _format_nodes_text(nodes: list[Node]) -> str:
    lines = [f"{n.id} | name={n.name} | type={n.type} | region={n.region}" for n in nodes]
    return "\n".join(lines)


def _format_disruptions_text(classifications: list[ClassifiedDisruption]) -> str:
    lines = []
    for i, c in enumerate(classifications):
        lines.append(
            f"{i}. affected_region={c.affected_region} | severity={c.severity} | "
            f"category={c.category} | estimated_duration_days={c.estimated_duration_days}"
        )
    return "\n".join(lines)


def _build_chain(system_prompt: str):
    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0,
    )
    structured_llm = llm.with_structured_output(NodeImpactBatch)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "NODES:\n{nodes_text}\n\nDISRUPTIONS:\n{disruptions_text}"),
        ]
    )

    return prompt | structured_llm


def _validate_impacts(
    impacts: list[NodeImpact], nodes: list[Node], classifications: list[ClassifiedDisruption]
) -> bool:
    """Every impact must reference a real node id and a real disruption index."""
    valid_node_ids = {n.id for n in nodes}
    max_index = len(classifications) - 1

    for impact in impacts:
        if impact.node_id not in valid_node_ids:
            return False
        if not (0 <= impact.disruption_index <= max_index):
            return False
    return True


def _fallback_mapping(
    nodes: list[Node], classifications: list[ClassifiedDisruption]
) -> list[NodeImpact]:
    """
    Deterministic region-substring fallback (the original MVP mapper logic).
    Used only if the LLM mapping fails entirely.
    """
    impacts: list[NodeImpact] = []
    for node in nodes:
        for i, c in enumerate(classifications):
            node_region = node.region.lower()
            disruption_region = c.affected_region.lower()
            if node_region in disruption_region or disruption_region in node_region:
                impacts.append(
                    NodeImpact(
                        node_id=node.id,
                        node_name=node.name,
                        disruption_index=i,
                        confidence=0.4,  # lower confidence: deterministic fallback, not LLM reasoning
                        reasoning="Fallback region-substring match (LLM mapping unavailable).",
                    )
                )
    return impacts


async def map_disruptions_to_nodes(
    nodes: list[Node], classifications: list[ClassifiedDisruption]
) -> list[NodeImpact]:
    """
    Map classified disruptions onto supply chain nodes via LangChain + ChatGroq.
    Failure-safe: retries once, then falls back to deterministic matching.
    Never raises.
    """
    if not nodes or not classifications:
        return []

    if not all(isinstance(n, Node) for n in nodes):
        logger.error(f"Invalid node types detected: {[type(n) for n in nodes]}")
        raise TypeError("Node contract violated inside mapper")

    if not settings.GROQ_API_KEY:
        logger.warning("Mapping Agent: GROQ_API_KEY not set, using fallback mapping.")
        return _fallback_mapping(nodes, classifications)

    nodes_text = _format_nodes_text(nodes)
    disruptions_text = _format_disruptions_text(classifications)

    # Attempt 1
    try:
        chain = _build_chain(SYSTEM_PROMPT)
        result: NodeImpactBatch = await chain.ainvoke(
            {"nodes_text": nodes_text, "disruptions_text": disruptions_text}
        )
        if not isinstance(result, NodeImpactBatch):
            result = NodeImpactBatch.model_validate(result.model_dump() if hasattr(result, "model_dump") else result)
        if _validate_impacts(result.impacts, nodes, classifications):
            logger.info(f"Mapping Agent: mapped {len(result.impacts)} impact(s) on first attempt.")
            return result.impacts
        logger.warning("Mapping Agent: attempt 1 returned invalid node/disruption references. Retrying.")
    except Exception as exc:
        logger.warning(f"Mapping Agent: attempt 1 failed: {exc}. Retrying.")

    # Attempt 2 (retry once)
    try:
        chain = _build_chain(RETRY_SYSTEM_PROMPT)
        result = await chain.ainvoke(
            {"nodes_text": nodes_text, "disruptions_text": disruptions_text}
        )
        if isinstance(result, dict):
            result = NodeImpactBatch.model_validate(result)
        if _validate_impacts(result.impacts, nodes, classifications):
            logger.info(f"Mapping Agent: mapped {len(result.impacts)} impact(s) on retry.")
            return result.impacts
        logger.error("Mapping Agent: retry returned invalid references. Falling back.")
    except Exception as exc:
        logger.error(f"Mapping Agent: retry failed: {exc}. Falling back.")

    # Fallback: deterministic, must never crash the pipeline either.
    try:
        fallback = _fallback_mapping(nodes, classifications)
    except Exception as exc:
        logger.error(f"Mapping Agent: fallback itself failed: {exc}. Returning no impacts.")
        return []

    logger.info(f"Mapping Agent: fallback produced {len(fallback)} impact(s).")
    return fallback