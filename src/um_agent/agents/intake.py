"""
src/um_agent/agents/intake.py
==============================
Node 1: Intake / Ingestion Agent

Receives raw unstructured clinical note text and uses Gemini with
structured output to extract a validated Pydantic ExtractedRequest.
"""

from __future__ import annotations

import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from um_agent.config import GOOGLE_API_KEY, GEMINI_MODEL_NAME
from um_agent.schemas.models import ExtractedRequest
from um_agent.graph.state import UMState

log = logging.getLogger(__name__)

# ── System prompt for the extraction LLM ────────────────────────────────────
_SYSTEM_PROMPT = """\
You are a medical data extraction specialist working in a healthcare
utilization management system.

Your task is to read an incoming prior authorization request and extract
structured clinical entities from the unstructured note.

EXTRACTION RULES:
- Extract ONLY what is explicitly stated in the note.
- If a field is not mentioned, leave it as null.
- For symptom_duration_weeks: convert months to weeks (1 month = 4 weeks).
- For radiculopathy_documented: mark True ONLY if pain radiating to an
  extremity (leg, arm) is explicitly described.
- For conservative_therapy_documented: mark True ONLY if the note states
  that therapy was COMPLETED (not merely ordered or recommended).
- Do not infer or assume information that is not in the note.
"""


def intake_node(state: UMState) -> dict:
    """
    LangGraph node function: extracts structured entities from the raw
    authorization note using Gemini's native structured output.

    Reads:   state["raw_intake_text"]
    Writes:  state["extracted_data"]
    """
    raw_text = state["raw_intake_text"]
    log.info("─── Intake Node ───")
    log.info(f"Processing authorization note ({len(raw_text)} chars)...")

    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL_NAME,
        google_api_key=GOOGLE_API_KEY,
        temperature=0,
    )

    # with_structured_output uses Gemini's native JSON schema support
    structured_llm = llm.with_structured_output(ExtractedRequest)

    result: ExtractedRequest = structured_llm.invoke(
        [
            ("system", _SYSTEM_PROMPT),
            ("human", f"Extract structured data from this authorization request:\n\n{raw_text}"),
        ]
    )

    log.info(f"  Patient     : {result.patient_name} ({result.patient_id})")
    log.info(f"  Procedure   : {result.procedure_requested}")
    log.info(f"  Diagnosis   : [{result.diagnosis_code}] {result.diagnosis_description}")
    log.info(f"  Radiculopathy: {result.radiculopathy_documented}")
    log.info(f"  Therapy doc'd: {result.conservative_therapy_documented}")

    return {"extracted_data": result.model_dump()}
