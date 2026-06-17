"""
src/um_agent/tools/ehr_query.py
================================
EHR query tool — retrieves a patient's complete clinical history from
the local SQLite EHR database and returns it as a formatted string.

Provides two interfaces:
  1. `fetch_patient_ehr(patient_id)`  — plain Python function for direct
     invocation by the ehr_fetch node (no LLM overhead).
  2. `query_patient_ehr`              — @tool-decorated version for
     optional binding to a LangChain LLM agent.
"""

from __future__ import annotations

import sqlite3
import logging
from langchain_core.tools import tool
from um_agent.config import SQLITE_PATH

log = logging.getLogger(__name__)


# ── Core Query Function ────────────────────────────────────────────────────────

def fetch_patient_ehr(patient_id: str) -> str:
    """
    Queries the SQLite EHR database and returns a structured,
    natural-language summary of the patient's medical history.

    Returns a "not found" message if the patient ID does not exist.
    """
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row

    try:
        # ── Patient demographics ───────────────────────────────────────────
        patient = conn.execute(
            "SELECT * FROM patients WHERE patient_id = ?", (patient_id,)
        ).fetchone()

        if not patient:
            return (
                f"No EHR records found for patient ID '{patient_id}'. "
                "The patient may not be registered in this system."
            )

        lines: list[str] = [
            f"═══ EHR SUMMARY: {patient['full_name']} ({patient_id}) ═══",
            f"DOB          : {patient['date_of_birth']} | Gender: {patient['gender']}",
            f"Insurer ID   : {patient['insurer_id']}",
            f"Physician    : {patient['primary_physician']}",
            "",
        ]

        # ── Clinical diagnoses ─────────────────────────────────────────────
        diagnoses = conn.execute(
            """SELECT diagnosis_date, diagnosis_code, diagnosis_desc, severity
               FROM clinical_history
               WHERE patient_id = ?
               ORDER BY diagnosis_date""",
            (patient_id,),
        ).fetchall()

        lines.append("CLINICAL DIAGNOSES:")
        if diagnoses:
            for d in diagnoses:
                lines.append(
                    f"  [{d['diagnosis_date']}]  {d['diagnosis_code']} — "
                    f"{d['diagnosis_desc']}  (Severity: {d['severity']})"
                )
        else:
            lines.append("  ⚠ No clinical diagnoses on record.")
        lines.append("")

        # ── Prior conservative treatments ──────────────────────────────────
        treatments = conn.execute(
            """SELECT treatment_type, start_date, end_date, duration_weeks, outcome, provider
               FROM treatments
               WHERE patient_id = ?
               ORDER BY start_date""",
            (patient_id,),
        ).fetchall()

        lines.append("PRIOR CONSERVATIVE THERAPY:")
        if treatments:
            for t in treatments:
                end_date = t["end_date"] or "ongoing"
                tx_type  = t["treatment_type"].replace("_", " ").title()
                lines.append(
                    f"  [{t['start_date']} → {end_date}]  {tx_type} — "
                    f"{t['duration_weeks']} weeks — Outcome: {t['outcome']} — "
                    f"Provider: {t['provider']}"
                )
        else:
            lines.append("  ⚠ No prior conservative therapy documented in EHR.")
        lines.append("")

        # ── Medication history ─────────────────────────────────────────────
        medications = conn.execute(
            """SELECT drug_name, drug_class, prescribed_date, end_date, response
               FROM medications
               WHERE patient_id = ?
               ORDER BY prescribed_date""",
            (patient_id,),
        ).fetchall()

        lines.append("MEDICATION HISTORY:")
        if medications:
            for m in medications:
                end_date = m["end_date"] or "ongoing"
                lines.append(
                    f"  [{m['prescribed_date']} → {end_date}]  {m['drug_name']} "
                    f"({m['drug_class']}) — Response: {m['response']}"
                )
        else:
            lines.append("  ⚠ No relevant medications on record.")

        return "\n".join(lines)

    finally:
        conn.close()


# ── LangChain Tool Wrapper ─────────────────────────────────────────────────────

@tool
def query_patient_ehr(patient_id: str) -> str:
    """
    Retrieves a patient's complete medical history from the hospital EHR database.

    Use this tool when a prior authorization request lacks documented clinical
    history (e.g., prior therapy, medications) that may already exist in the
    patient's electronic health record.

    Args:
        patient_id: The patient identifier from the authorization note (e.g. 'PT-9942').

    Returns:
        A formatted summary of the patient's diagnoses, prior conservative
        treatments, and medication trial history.
    """
    log.info(f"[tool] query_patient_ehr called for patient: {patient_id}")
    return fetch_patient_ehr(patient_id)
