"""
src/um_agent/schemas/models.py
================================
Pydantic v2 models used as structured output schemas for Gemini LLM calls.

Two models:
  - ExtractedRequest  : Output of the Intake node (entity extraction)
  - EvaluationResult  : Output of the Evaluation node (drives graph routing)
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ExtractedRequest(BaseModel):
    """
    Structured entities parsed from an unstructured medical authorization note.
    Used as the schema for `llm.with_structured_output(ExtractedRequest)`.
    Gemini maps this to a native JSON schema, ensuring type-safe extraction.
    """

    patient_id: str = Field(
        description="The patient identifier found in the note, e.g. 'PT-9942'."
    )
    patient_name: str = Field(
        description="Full legal name of the patient."
    )
    requesting_physician: str = Field(
        description="Name and credentials of the requesting physician."
    )
    procedure_requested: str = Field(
        description="The medical procedure or drug being requested, e.g. 'MRI Lumbar Spine'."
    )
    diagnosis_code: str = Field(
        description="Primary ICD-10 diagnosis code, e.g. 'M54.41'."
    )
    diagnosis_description: str = Field(
        description="Human-readable description of the primary diagnosis."
    )
    symptom_duration_weeks: Optional[int] = Field(
        default=None,
        description=(
            "Duration of the primary symptom in weeks. "
            "Convert months to weeks if needed. Null if not mentioned."
        ),
    )
    radiculopathy_documented: Optional[bool] = Field(
        default=None,
        description=(
            "True only if pain radiation to a limb (sciatica/radiculopathy) "
            "is explicitly described. Null if not mentioned."
        ),
    )
    conservative_therapy_documented: Optional[bool] = Field(
        default=None,
        description=(
            "True only if the note EXPLICITLY states that conservative therapy "
            "(PT, chiropractic, NSAIDs) was completed — not merely prescribed. "
            "Null if not mentioned."
        ),
    )
    clinical_summary: str = Field(
        description="A concise 2-3 sentence clinical summary of the authorization request."
    )


class EvaluationResult(BaseModel):
    """
    Output of the Evaluation Agent — drives the conditional routing decision.

    The `decision` field is read by the graph's conditional edge function
    to route the workflow to the correct next node or terminal state.
    """

    decision: Literal["approve", "fetch_ehr", "escalate"] = Field(
        description=(
            "'approve'   : All mandatory policy criteria are explicitly and clearly met. "
            "'fetch_ehr' : One or more criteria cannot be confirmed from the note alone; "
            "the patient's EHR records may contain the missing evidence. "
            "Use this when information is ABSENT, not when it is present but fails. "
            "'escalate'  : Criteria definitively FAIL, or EHR data was retrieved but "
            "still does not satisfy all criteria. Route to human review."
        )
    )
    clinical_rationale: str = Field(
        description=(
            "Detailed clinical reasoning explaining why each policy criterion "
            "is or is not met by the available information."
        )
    )
    criteria_met: list[str] = Field(
        default_factory=list,
        description="Policy criteria clearly satisfied by the available information.",
    )
    criteria_not_met: list[str] = Field(
        default_factory=list,
        description="Policy criteria not satisfied or impossible to confirm.",
    )
    missing_information: Optional[str] = Field(
        default=None,
        description=(
            "The specific clinical data that is missing and may exist in the patient's "
            "EHR records. Only relevant when decision is 'fetch_ehr'."
        ),
    )
