"""
scripts/run_demo.py
====================
End-to-end demo runner for the Autonomous UM Agent Graph.

Runs two demo scenarios:
  1. Sarah Jenkins (PT-9942) — should be auto-approved after EHR fetch
  2. Marcus Vance  (PT-1105) — should be escalated to human review

Usage (from project root, with .venv active):
  python scripts/run_demo.py
"""

import logging
import uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

from um_agent.graph.builder import build_graph   # noqa: E402


# ── Sample authorization notes ─────────────────────────────────────────────────

SARAH_JENKINS_NOTE = """\
PRIOR AUTHORIZATION REQUEST

Date: 2025-02-15
Requesting Provider: Dr. Priya Sharma, MD — Orthopedic Surgery
Patient: Sarah Jenkins
Patient ID: PT-9942
Insurance Member ID: INS-882341

Procedure Requested: MRI Lumbar Spine (CPT 72148)

Clinical Information:
Patient is a 42-year-old female presenting with chronic lower back pain
radiating down the left leg, consistent with left-sided sciatica.
Symptoms have been persistent for approximately 8 weeks with progressive
worsening. Patient reports numbness and tingling in the left foot.

The patient's note does not document prior conservative therapy attempts
in this submission. Please review.

Primary Diagnosis: M54.41 — Lumbago with sciatica, left side

Urgency: Standard
"""

MARCUS_VANCE_NOTE = """\
PRIOR AUTHORIZATION REQUEST

Date: 2025-03-01
Requesting Provider: Dr. Raymond Cole, MD — Family Medicine
Patient: Marcus Vance
Patient ID: PT-1105
Insurance Member ID: INS-551882

Procedure Requested: MRI Lumbar Spine (CPT 72148)

Clinical Information:
Patient is a 49-year-old male presenting with lower back pain for
approximately 3 weeks. Pain is localized to the lumbar region. No
radiation to the lower extremities. No numbness or tingling reported.
Patient has not yet attempted any conservative therapy.

Primary Diagnosis: M54.5 — Low back pain, unspecified

Urgency: Standard
"""


# ── Runner ─────────────────────────────────────────────────────────────────────

def run_scenario(graph, note: str, label: str) -> None:
    """Invokes the compiled graph on a single authorization note."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    log.info("=" * 70)
    log.info(f"  SCENARIO: {label}")
    log.info(f"  Thread  : {thread_id}")
    log.info("=" * 70)

    result = graph.invoke(
        {
            "raw_intake_text": note,
            "extracted_data": None,
            "retrieved_policies": [],
            "mock_ehr_data": None,
            "next_action": "",
            "final_determination": "",
            "ehr_fetch_count": 0,
        },
        config=config,
    )

    # ── Print final result ─────────────────────────────────────────────────
    decision = result.get("next_action", "UNKNOWN")
    rationale = result.get("final_determination", "No rationale provided.")

    log.info("")
    log.info("╔══════════════════════════════════════════════════════════════════╗")
    if decision == "approve":
        log.info("║  ✅  DECISION: AUTO-APPROVED                                    ║")
    elif decision == "escalate":
        log.info("║  🔴  DECISION: ESCALATED TO HUMAN REVIEW                       ║")
    else:
        log.info(f"║  ⚠️   DECISION: {decision:<49}║")
    log.info("╚══════════════════════════════════════════════════════════════════╝")
    log.info("")
    log.info("CLINICAL RATIONALE:")
    for line in rationale.split("\n"):
        log.info(f"  {line}")
    log.info("")

    ehr_fetched = result.get("ehr_fetch_count", 0)
    if ehr_fetched > 0:
        log.info(f"  [EHR was fetched {ehr_fetched} time(s) during evaluation]")
    log.info("")


def main() -> None:
    log.info("\n" + "=" * 70)
    log.info("  🏥  Autonomous UM Agent — End-to-End Demo")
    log.info("=" * 70 + "\n")

    graph = build_graph()

    # Scenario 1: Sarah Jenkins — expected outcome: approve (after EHR fetch)
    run_scenario(graph, SARAH_JENKINS_NOTE, "Sarah Jenkins (PT-9942) — Should APPROVE")

    # Scenario 2: Marcus Vance — expected outcome: escalate
    run_scenario(graph, MARCUS_VANCE_NOTE, "Marcus Vance (PT-1105) — Should ESCALATE")

    log.info("=" * 70)
    log.info("  ✅  Demo complete.")
    log.info("=" * 70)


if __name__ == "__main__":
    main()
