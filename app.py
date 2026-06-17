"""
app.py — Streamlit Frontend
=============================
Premium interactive UI for the Autonomous UM Agent.

Run from the project root:
    streamlit run app.py
"""

import streamlit as st
import uuid
import time
import logging
from io import StringIO

from um_agent.graph.builder import build_graph

# ──────────────────────────────────────────────────────────────────────────────
# Page Configuration
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="UM Agent — Autonomous Medical Review",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# Custom CSS for Premium Styling
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Global */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Hero header */
.hero-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    padding: 2rem 2.5rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    border: 1px solid rgba(99, 102, 241, 0.15);
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
}
.hero-header h1 {
    color: #f1f5f9;
    font-weight: 700;
    font-size: 1.75rem;
    margin-bottom: 0.25rem;
}
.hero-header p {
    color: #94a3b8;
    font-size: 0.95rem;
    margin: 0;
}

/* Status badges */
.status-badge {
    display: inline-block;
    padding: 0.35rem 1rem;
    border-radius: 24px;
    font-weight: 600;
    font-size: 0.8rem;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.badge-approved {
    background: linear-gradient(135deg, #065f46, #047857);
    color: #d1fae5;
    border: 1px solid #34d399;
}
.badge-escalated {
    background: linear-gradient(135deg, #7f1d1d, #991b1b);
    color: #fecaca;
    border: 1px solid #f87171;
}
.badge-pending {
    background: linear-gradient(135deg, #78350f, #92400e);
    color: #fef3c7;
    border: 1px solid #fbbf24;
}

/* Decision card */
.decision-card {
    padding: 1.5rem 2rem;
    border-radius: 12px;
    margin: 1rem 0;
}
.decision-approve {
    background: linear-gradient(135deg, #064e3b, #065f46);
    border: 1px solid #34d399;
}
.decision-escalate {
    background: linear-gradient(135deg, #7f1d1d, #991b1b);
    border: 1px solid #f87171;
}
.decision-card h2 {
    margin: 0 0 0.5rem 0;
    font-size: 1.3rem;
}
.decision-card p {
    margin: 0;
    color: #e2e8f0;
    line-height: 1.6;
}

/* Node step cards */
.node-step {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.75rem;
    transition: border-color 0.2s ease;
}
.node-step:hover {
    border-color: #6366f1;
}
.node-step h4 {
    color: #c7d2fe;
    margin: 0 0 0.5rem 0;
    font-size: 0.9rem;
    font-weight: 600;
}
.node-step p, .node-step li {
    color: #cbd5e1;
    font-size: 0.85rem;
    line-height: 1.5;
}

/* Metrics row */
.metric-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    text-align: center;
}
.metric-card .metric-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #a5b4fc;
}
.metric-card .metric-label {
    font-size: 0.75rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: #0f172a;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #e2e8f0;
}

/* Expander */
.streamlit-expanderHeader {
    background: #1e293b !important;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Preset Authorization Notes
# ──────────────────────────────────────────────────────────────────────────────
PRESETS = {
    "Sarah Jenkins (PT-9942) — Should Approve": """\
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

Urgency: Standard""",
    "Marcus Vance (PT-1105) — Should Escalate": """\
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

Urgency: Standard""",
    "Custom — Enter Your Own": "",
}


# ──────────────────────────────────────────────────────────────────────────────
# Helper: Run the agent graph and capture step-by-step trace
# ──────────────────────────────────────────────────────────────────────────────
def run_agent(note_text: str):
    """
    Runs the UM Agent graph and yields step-by-step updates
    as (step_name, step_data) tuples for the UI to consume.
    """
    graph = build_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "raw_intake_text": note_text,
        "extracted_data": None,
        "retrieved_policies": [],
        "mock_ehr_data": None,
        "next_action": "",
        "final_determination": "",
        "ehr_fetch_count": 0,
    }

    # Stream node-by-node updates
    steps = []
    for event in graph.stream(initial_state, config=config, stream_mode="updates"):
        for node_name, node_output in event.items():
            steps.append((node_name, node_output))

    return steps


# ──────────────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧠 Agent Configuration")
    st.divider()

    st.markdown("**Select a Scenario**")
    selected = st.selectbox(
        "Choose a preset authorization note or enter your own:",
        list(PRESETS.keys()),
        label_visibility="collapsed",
    )

    if selected == "Custom — Enter Your Own":
        note_input = st.text_area(
            "Paste Authorization Note",
            height=300,
            placeholder="Paste a prior authorization request here...",
        )
    else:
        note_input = PRESETS[selected]
        st.text_area(
            "Authorization Note (read-only)",
            value=note_input,
            height=300,
            disabled=True,
        )

    st.divider()

    st.markdown("**Tech Stack**")
    st.caption("LangGraph · Gemini 2.5 Flash · ChromaDB · SQLite")

    st.divider()

    run_button = st.button(
        "▶  Run Agent Review",
        type="primary",
        use_container_width=True,
        disabled=not note_input.strip(),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Main Content Area
# ──────────────────────────────────────────────────────────────────────────────

# Hero Header
st.markdown("""
<div class="hero-header">
    <h1>🏥 Autonomous Utilization Management Agent</h1>
    <p>Multi-agent AI system that automates healthcare prior authorization decisions using LangGraph, Gemini, and real-time EHR integration.</p>
</div>
""", unsafe_allow_html=True)

# If not yet run, show the architecture
if not run_button:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">4</div>
            <div class="metric-label">Agent Nodes</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">4</div>
            <div class="metric-label">Policies Indexed</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">2</div>
            <div class="metric-label">Patient Records</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">~15s</div>
            <div class="metric-label">Avg. Decision Time</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    st.markdown("### How It Works")
    st.markdown("""
    ```
    Authorization Note → Intake Agent → Policy Retrieval → Evaluation Agent
                                                              │
                                          ┌───────────────────┼───────────────────┐
                                          ▼                   ▼                   ▼
                                      APPROVE            EHR Fetch            ESCALATE
                                       (done)          (query SQLite)          (done)
                                                            │
                                                            └──► Re-Evaluate
    ```
    """)
    st.info("👈 Select a scenario from the sidebar and click **Run Agent Review** to start.")

# ──────────────────────────────────────────────────────────────────────────────
# Run the Agent
# ──────────────────────────────────────────────────────────────────────────────
if run_button and note_input.strip():

    # Progress bar and status
    progress_bar = st.progress(0, text="Initializing agent graph...")
    status_container = st.empty()

    start_time = time.time()

    try:
        # Run the agent and collect all steps
        with st.spinner("Running autonomous review..."):
            steps = run_agent(note_input.strip())

        elapsed = time.time() - start_time
        progress_bar.progress(100, text="Review complete!")

        # Parse final state from the last step
        final_state = {}
        for _, step_data in steps:
            final_state.update(step_data)

        decision = final_state.get("next_action", "unknown")
        rationale = final_state.get("final_determination", "No rationale provided.")
        extracted = final_state.get("extracted_data", {})
        ehr_count = final_state.get("ehr_fetch_count", 0)

        # ── Decision Banner ──────────────────────────────────────────────
        if decision == "approve":
            st.markdown(f"""
            <div class="decision-card decision-approve">
                <h2>✅ AUTO-APPROVED</h2>
                <p>All policy criteria have been met. Authorization is granted.</p>
            </div>
            """, unsafe_allow_html=True)
        elif decision == "escalate":
            st.markdown(f"""
            <div class="decision-card decision-escalate">
                <h2>🔴 ESCALATED TO HUMAN REVIEW</h2>
                <p>One or more policy criteria were not satisfied. This request requires manual clinical review.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning(f"Unexpected decision: {decision}")

        # ── Metrics row ──────────────────────────────────────────────────
        st.markdown("")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Decision", decision.upper())
        m2.metric("Processing Time", f"{elapsed:.1f}s")
        m3.metric("LLM Calls", sum(1 for name, _ in steps if name in ("intake", "evaluation")))
        m4.metric("EHR Fetches", ehr_count)

        # ── Clinical Rationale ───────────────────────────────────────────
        st.markdown("### 📋 Clinical Rationale")
        st.markdown(f"> {rationale}")

        # ── Agent Execution Trace ────────────────────────────────────────
        st.markdown("### 🔍 Agent Execution Trace")

        node_icons = {
            "intake": "📥",
            "policy_retrieval": "📚",
            "evaluation": "⚖️",
            "ehr_fetch": "🗄️",
        }
        node_labels = {
            "intake": "Intake Agent — Entity Extraction",
            "policy_retrieval": "Policy Retrieval Agent — ChromaDB Search",
            "evaluation": "Evaluation Agent — Compliance Check",
            "ehr_fetch": "EHR Fetch Agent — SQLite Query",
        }

        for i, (node_name, node_data) in enumerate(steps):
            icon = node_icons.get(node_name, "⚙️")
            label = node_labels.get(node_name, node_name)
            step_num = i + 1

            with st.expander(f"Step {step_num}: {icon} {label}", expanded=(i == 0 or node_name == "ehr_fetch")):
                if node_name == "intake" and "extracted_data" in node_data:
                    ed = node_data["extracted_data"]
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**Patient Details**")
                        st.markdown(f"- **Name**: {ed.get('patient_name', 'N/A')}")
                        st.markdown(f"- **ID**: {ed.get('patient_id', 'N/A')}")
                        st.markdown(f"- **Physician**: {ed.get('requesting_physician', 'N/A')}")
                    with col_b:
                        st.markdown("**Clinical Extraction**")
                        st.markdown(f"- **Procedure**: {ed.get('procedure_requested', 'N/A')}")
                        st.markdown(f"- **Diagnosis**: [{ed.get('diagnosis_code', '')}] {ed.get('diagnosis_description', '')}")
                        st.markdown(f"- **Duration**: {ed.get('symptom_duration_weeks', 'N/A')} weeks")
                        st.markdown(f"- **Radiculopathy**: {ed.get('radiculopathy_documented', 'N/A')}")
                        st.markdown(f"- **Conservative Therapy**: {ed.get('conservative_therapy_documented', 'N/A')}")

                    if ed.get("clinical_summary"):
                        st.info(f"**Summary**: {ed['clinical_summary']}")

                elif node_name == "policy_retrieval" and "retrieved_policies" in node_data:
                    for j, policy in enumerate(node_data["retrieved_policies"], 1):
                        st.text_area(
                            f"Policy {j}",
                            value=policy,
                            height=200,
                            disabled=True,
                            key=f"policy_{i}_{j}",
                        )

                elif node_name == "evaluation":
                    action = node_data.get("next_action", "N/A")
                    determ = node_data.get("final_determination", "N/A")

                    if action == "approve":
                        st.markdown('<span class="status-badge badge-approved">APPROVE</span>', unsafe_allow_html=True)
                    elif action == "escalate":
                        st.markdown('<span class="status-badge badge-escalated">ESCALATE</span>', unsafe_allow_html=True)
                    elif action == "fetch_ehr":
                        st.markdown('<span class="status-badge badge-pending">FETCH EHR</span>', unsafe_allow_html=True)

                    st.markdown(f"**Reasoning**: {determ}")

                elif node_name == "ehr_fetch" and "mock_ehr_data" in node_data:
                    st.code(node_data["mock_ehr_data"], language="text")

                else:
                    st.json(node_data)

    except Exception as e:
        progress_bar.empty()
        st.error(f"**Agent Error**: {str(e)}")
        st.exception(e)
