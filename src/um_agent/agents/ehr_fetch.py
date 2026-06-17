"""
src/um_agent/agents/ehr_fetch.py
=================================
Node 4: EHR Fetch Agent

Triggered conditionally when the Evaluation node decides that clinical
history data is missing from the authorization note, but might exist
in the patient's Electronic Health Record (EHR) database.

This node:
  1. Reads the patient_id from extracted_data
  2. Queries SQLite via the ehr_query tool
  3. Appends the result to state and increments the loop counter
  4. The graph then routes back to the Evaluation node for re-assessment
"""

from __future__ import annotations

import logging
from um_agent.tools.ehr_query import fetch_patient_ehr
from um_agent.graph.state import UMState

log = logging.getLogger(__name__)


def ehr_fetch_node(state: UMState) -> dict:
    """
    LangGraph node function: fetches EHR data from SQLite for the
    patient referenced in the authorization request.

    Reads:   state["extracted_data"]["patient_id"]
    Writes:  state["mock_ehr_data"], state["ehr_fetch_count"]
    """
    extracted  = state["extracted_data"]
    patient_id = extracted["patient_id"]
    fetch_count = state.get("ehr_fetch_count", 0)

    log.info("─── EHR Fetch Node ───")
    log.info(f"  Patient ID : {patient_id}")
    log.info(f"  Fetch #{fetch_count + 1}")

    ehr_summary = fetch_patient_ehr(patient_id)

    log.info(f"  Retrieved {len(ehr_summary)} chars of EHR data.")

    return {
        "mock_ehr_data": ehr_summary,
        "ehr_fetch_count": fetch_count + 1,
    }
