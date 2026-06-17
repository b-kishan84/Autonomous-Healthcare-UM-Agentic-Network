"""
src/um_agent/agents/evaluation.py
==================================
Node 3: Evaluation Agent

Compares the extracted request data against the retrieved policy criteria.
If EHR data was fetched, it is included as additional context.

Outputs an EvaluationResult with a routing decision:
  - "approve"   → all policy criteria are met
  - "fetch_ehr" → data missing, but might exist in the patient's EHR
  - "escalate"  → criteria definitively fail, needs human review
"""

from __future__ import annotations

import json
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from um_agent.config import GOOGLE_API_KEY, GEMINI_MODEL_NAME, MAX_EHR_RETRIES
from um_agent.schemas.models import EvaluationResult
from um_agent.graph.state import UMState

log = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a senior clinical reviewer evaluating a prior authorization request
against insurance policy criteria.

YOUR TASK:
Given:
  1. Extracted request data (structured entities from the clinical note)
  2. Insurance policy criteria (the rules the request must satisfy)
  3. Optionally: EHR data (additional patient history from the hospital database)

Decide:
  - "approve"   — ONLY if ALL mandatory policy criteria are CLEARLY and
    EXPLICITLY satisfied by the combined information.
  - "fetch_ehr" — If one or more criteria CANNOT be confirmed from the
    available data, but might be documented in the patient's electronic
    health record. Use this when information is ABSENT (not mentioned),
    NOT when it is present but fails to meet the criteria.
  - "escalate"  — If criteria definitively FAIL (contradicted by evidence),
    or if EHR data has already been fetched and still does not satisfy
    all requirements. Route to human review.

CRITICAL RULES:
- Do NOT approve if ANY criterion is uncertain or undocumented.
- Do NOT request EHR fetch if the data has already been fetched and is
  included in the context below.
- Be precise — cite specific policy criteria by number.
"""


def evaluation_node(state: UMState) -> dict:
    """
    LangGraph node function: evaluates the request against policy criteria.

    Reads:   state["extracted_data"], state["retrieved_policies"],
             state["mock_ehr_data"], state["ehr_fetch_count"]
    Writes:  state["next_action"], state["final_determination"]
    """
    extracted  = state["extracted_data"]
    policies   = state["retrieved_policies"]
    ehr_data   = state.get("mock_ehr_data")
    fetch_count = state.get("ehr_fetch_count", 0)

    log.info("─── Evaluation Node ───")

    # ── Build the human message with all available context ──────────────────
    context_parts = [
        "EXTRACTED REQUEST DATA:",
        json.dumps(extracted, indent=2, default=str),
        "",
        "INSURANCE POLICY CRITERIA:",
    ]
    for i, policy in enumerate(policies, 1):
        context_parts.append(f"--- Policy {i} ---")
        context_parts.append(policy)
        context_parts.append("")

    if ehr_data:
        context_parts.append("ADDITIONAL EHR DATA (fetched from hospital database):")
        context_parts.append(ehr_data)
        context_parts.append("")
        context_parts.append(
            "NOTE: EHR data has already been retrieved. "
            "Do NOT request another fetch. Make your final decision now."
        )

    # If we've already fetched EHR data, force a terminal decision
    if fetch_count >= MAX_EHR_RETRIES:
        context_parts.append(
            "\n⚠ IMPORTANT: The EHR has already been queried. "
            "You MUST choose 'approve' or 'escalate' — 'fetch_ehr' is no longer available."
        )

    human_message = "\n".join(context_parts)

    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL_NAME,
        google_api_key=GOOGLE_API_KEY,
        temperature=0,
    )
    structured_llm = llm.with_structured_output(EvaluationResult)

    result: EvaluationResult = structured_llm.invoke(
        [
            ("system", _SYSTEM_PROMPT),
            ("human", human_message),
        ]
    )

    # Override fetch_ehr if we've exhausted retries
    decision = result.decision
    if decision == "fetch_ehr" and fetch_count >= MAX_EHR_RETRIES:
        log.warning("  EHR fetch limit reached — forcing escalation.")
        decision = "escalate"

    log.info(f"  Decision       : {decision}")
    log.info(f"  Criteria met   : {result.criteria_met}")
    log.info(f"  Criteria unmet : {result.criteria_not_met}")
    if result.missing_information:
        log.info(f"  Missing info   : {result.missing_information}")

    return {
        "next_action": decision,
        "final_determination": result.clinical_rationale,
    }
