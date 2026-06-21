"""
Reroute Agent.

For each impacted node: deterministic BFS (services/graph_utils.py) finds
candidate alternative nodes first, then LangChain + ChatGroq phrases a
human-readable suggestion from that context. Runs in parallel per node via
asyncio.gather, per spec.
"""

import asyncio

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.logging import logger
from app.schemas.graph import Edge, Node
from app.schemas.mapping import NodeImpact
from app.schemas.reroute import RerouteSuggestion
from app.schemas.risk import ClassifiedDisruption
from app.utils.graph import find_alternative_nodes

SYSTEM_PROMPT = """\
You are a supply chain rerouting advisor. A node in the supply chain has \
been impacted by a disruption. You are given the impacted node, the \
disruption details, and a list of candidate alternative nodes (same type, \
ranked by graph proximity).

Write a short, actionable rerouting suggestion (1-3 sentences) and choose \
which of the given alternative node ids you actually recommend, in priority \
order. Only use the exact node ids given to you - do not invent new ones. \
If there are no good alternatives, say so plainly and return an empty list.
"""


def _build_chain():
    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.2,
    )
    structured_llm = llm.with_structured_output(RerouteSuggestion)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", "{context_text}"),
        ]
    )

    return prompt | structured_llm


def _format_context(
    impacted_node: Node,
    disruption: ClassifiedDisruption,
    alternatives: list[Node],
) -> str:
    alt_lines = "\n".join(f"- {n.id} | {n.name} ({n.type}, {n.region})" for n in alternatives) or "(none)"
    return (
        f"IMPACTED NODE: {impacted_node.id} | {impacted_node.name} "
        f"({impacted_node.type}, {impacted_node.region})\n\n"
        f"DISRUPTION: category={disruption.category} | severity={disruption.severity} | "
        f"affected_region={disruption.affected_region} | "
        f"estimated_duration_days={disruption.estimated_duration_days}\n\n"
        f"CANDIDATE ALTERNATIVES:\n{alt_lines}"
    )


def _fallback_suggestion(
    impacted_node: Node, alternatives: list[Node]
) -> RerouteSuggestion:
    """Deterministic fallback if the LLM call fails. Never crashes the pipeline."""
    if alternatives:
        names = ", ".join(n.name for n in alternatives)
        suggestion = (
            f"{impacted_node.name} is impacted. Consider rerouting through: {names}."
        )
    else:
        suggestion = (
            f"{impacted_node.name} is impacted and no alternative {impacted_node.type} "
            f"node is available in this supply chain."
        )
    return RerouteSuggestion(
        node_id=impacted_node.id,
        node_name=impacted_node.name,
        suggestion=suggestion,
        recommended_alternative_node_ids=[n.id for n in alternatives],
    )


async def _suggest_for_node(
    impacted_node: Node,
    disruption: ClassifiedDisruption,
    all_nodes: list[Node],
    edges: list[Edge],
) -> RerouteSuggestion:
    alternatives = find_alternative_nodes(impacted_node, all_nodes, edges)

    if not settings.GROQ_API_KEY:
        return _fallback_suggestion(impacted_node, alternatives)

    context_text = _format_context(impacted_node, disruption, alternatives)
    valid_ids = {n.id for n in alternatives}

    try:
        chain = _build_chain()
        result: RerouteSuggestion = await chain.ainvoke({"context_text": context_text})

        # Defense: never trust the LLM blindly - drop any invented ids.
        result.recommended_alternative_node_ids = [
            nid for nid in result.recommended_alternative_node_ids if nid in valid_ids
        ]
        result.node_id = impacted_node.id
        result.node_name = impacted_node.name
        return result

    except Exception as exc:
        logger.warning(f"Reroute Agent: node '{impacted_node.name}' LLM call failed: {exc}. Using fallback.")
        return _fallback_suggestion(impacted_node, alternatives)


async def generate_reroute_suggestions(
    impacts: list[NodeImpact],
    classifications: list[ClassifiedDisruption],
    all_nodes: list[Node],
    edges: list[Edge],
) -> list[RerouteSuggestion]:
    """
    Generates one reroute suggestion per impacted node, running all node tasks
    concurrently via asyncio.gather(return_exceptions=True). Never raises.
    """
    if not impacts:
        return []

    nodes_by_id = {n.id: n for n in all_nodes}

    tasks = []
    valid_impacts: list[NodeImpact] = []
    for impact in impacts:
        node = nodes_by_id.get(impact.node_id)
        if node is None:
            logger.warning(f"Reroute Agent: impact references unknown node_id={impact.node_id}, skipping.")
            continue
        if not (0 <= impact.disruption_index < len(classifications)):
            logger.warning(
                f"Reroute Agent: impact for node {impact.node_id} has invalid "
                f"disruption_index={impact.disruption_index}, skipping."
            )
            continue
        disruption = classifications[impact.disruption_index]
        valid_impacts.append(impact)
        tasks.append(_suggest_for_node(node, disruption, all_nodes, edges))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    suggestions: list[RerouteSuggestion] = []
    for impact, result in zip(valid_impacts, results):
        if isinstance(result, Exception):
            logger.error(f"Reroute Agent: node '{impact.node_id}' task raised unexpectedly: {result}")
            node = nodes_by_id[impact.node_id]
            suggestions.append(_fallback_suggestion(node, []))
            continue
        suggestions.append(result)

    logger.info(f"Reroute Agent: generated {len(suggestions)} suggestion(s).")
    return suggestions