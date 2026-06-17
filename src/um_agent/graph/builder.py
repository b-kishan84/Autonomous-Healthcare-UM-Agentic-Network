"""
src/um_agent/graph/builder.py
==============================
Compiles the full LangGraph StateGraph for the UM Agent workflow.

Graph topology:
    START → intake → policy_retrieval → evaluation → conditional_edge
        conditional_edge:
            "approve"   → END
            "escalate"  → END
            "fetch_ehr" → ehr_fetch → evaluation  (loops back)
"""

from __future__ import annotations

import logging
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from um_agent.graph.state import UMState
from um_agent.agents.intake import intake_node
from um_agent.agents.policy_retrieval import policy_retrieval_node
from um_agent.agents.evaluation import evaluation_node
from um_agent.agents.ehr_fetch import ehr_fetch_node

log = logging.getLogger(__name__)


# ── Conditional routing function ───────────────────────────────────────────────

def _route_after_evaluation(state: UMState) -> str:
    """
    Reads the `next_action` field set by the evaluation node and returns
    the name of the next node (or END) for LangGraph's conditional edge.
    """
    action = state["next_action"]
    log.info(f"  Routing → {action}")

    if action == "approve":
        return END
    elif action == "fetch_ehr":
        return "ehr_fetch"
    else:
        # "escalate" or any unexpected value → terminate
        return END


# ── Graph builder ──────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Constructs and compiles the LangGraph StateGraph with MemorySaver.

    Returns a compiled graph ready to be invoked with:
        graph.invoke({"raw_intake_text": "..."}, config={"configurable": {"thread_id": "..."}})
    """
    log.info("Building LangGraph state machine...")

    graph = StateGraph(UMState)

    # ── Register nodes ─────────────────────────────────────────────────────
    graph.add_node("intake", intake_node)
    graph.add_node("policy_retrieval", policy_retrieval_node)
    graph.add_node("evaluation", evaluation_node)
    graph.add_node("ehr_fetch", ehr_fetch_node)

    # ── Wire edges ─────────────────────────────────────────────────────────
    # Linear flow: START → intake → policy_retrieval → evaluation
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "policy_retrieval")
    graph.add_edge("policy_retrieval", "evaluation")

    # Conditional edge after evaluation — routes based on next_action
    graph.add_conditional_edges(
        "evaluation",
        _route_after_evaluation,
        {
            END: END,
            "ehr_fetch": "ehr_fetch",
        },
    )

    # After EHR fetch, loop back to evaluation for re-assessment
    graph.add_edge("ehr_fetch", "evaluation")

    # ── Compile with MemorySaver checkpointer ──────────────────────────────
    checkpointer = MemorySaver()
    compiled = graph.compile(checkpointer=checkpointer)

    log.info("Graph compiled successfully.")
    return compiled
