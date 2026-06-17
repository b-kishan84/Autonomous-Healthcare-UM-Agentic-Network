"""
src/um_agent/graph/state.py
============================
Defines UMState — the single shared mutable state dictionary that flows
through every node in the LangGraph workflow.

LangGraph nodes receive the full state and return a PARTIAL dict
containing only the keys they modified. LangGraph merges the partial
update back into the shared state automatically.
"""

from __future__ import annotations

from typing import List, Optional, TypedDict


class UMState(TypedDict):
    """
    Shared state schema for the Autonomous UM Agent Graph.

    All fields are Optional where a node may not have populated them yet,
    allowing the graph to be invoked with only `raw_intake_text` set.
    """

    # ── Input (provided at graph invocation) ───────────────────────────────
    raw_intake_text: str
    """The original unstructured medical authorization request note."""

    # ── Intake Node output ─────────────────────────────────────────────────
    extracted_data: Optional[dict]
    """
    JSON-serialized ExtractedRequest from the intake node.
    Stored as a plain dict (via .model_dump()) for MemorySaver compatibility.
    """

    # ── Policy Retrieval Node output ───────────────────────────────────────
    retrieved_policies: List[str]
    """Full text of the top-k most relevant insurance policies from ChromaDB."""

    # ── EHR Fetch Node output (conditional) ───────────────────────────────
    mock_ehr_data: Optional[str]
    """
    Natural-language EHR summary fetched from SQLite.
    None if the EHR fetch branch was not triggered.
    """

    # ── Evaluation Node output ─────────────────────────────────────────────
    next_action: str
    """
    Routing flag consumed by the conditional edge after evaluation:
      'approve'   → terminate with approval
      'fetch_ehr' → route to EHR fetch, then re-evaluate
      'escalate'  → terminate and route to human reviewer
    """

    final_determination: str
    """
    Human-readable final decision and clinical rationale.
    Populated by the evaluation node on terminal decisions only
    (approve or escalate).
    """

    # ── Loop guard ─────────────────────────────────────────────────────────
    ehr_fetch_count: int
    """
    Tracks how many times the EHR fetch node has been called.
    Prevents infinite evaluation ↔ EHR-fetch loops.
    Capped by config.MAX_EHR_RETRIES.
    """
