# 🏥 Autonomous Utilization Management (UM) & Policy Digitization Agentic Network

A **multi-agent AI system** that automates healthcare prior authorization — the process where insurers evaluate whether a requested procedure or drug meets medical necessity guidelines before approving coverage.

Built with **LangGraph**, **Google Gemini 2.5 Flash**, **ChromaDB**, and **SQLite**.

---

## The Problem It Solves

When a physician submits an authorization request (e.g., for an MRI), a human reviewer must:
1. Read the unstructured clinical note
2. Look up the insurer's coverage policy
3. Cross-check whether the patient's documented history satisfies all criteria
4. Request more records if information is missing — causing multi-day delays

This system replaces that manual loop with an autonomous agent network that reaches a decision in seconds.

---

## How It Works

```
Unstructured Clinical Note (Authorization Request)
         │
         ▼
┌─────────────────────────┐
│     Intake Agent        │  Extracts structured entities via Gemini + Pydantic
│  (Extract key entities) │  patient ID, procedure, diagnosis, symptom duration
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│     Policy Agent        │  Queries ChromaDB with the procedure type
│  (Retrieve guidelines)  │  Returns the most relevant coverage criteria
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│    Evaluation Agent     │  Gemini compares extracted data against policy rules
│   (Judge compliance)    │  Issues a routing decision
└──────────┬──────────────┘
           │
     ┌─────┼──────────────────────┐
     ▼     ▼                      ▼
 APPROVE  EHR Fetch Agent      ESCALATE
  (done)  Queries SQLite EHR    (done)
          for missing history
               │
               └──► Re-evaluate with new context
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Orchestration | LangGraph — state machine with conditional edges |
| LLM | Google Gemini 2.5 Flash via `langchain-google-genai` |
| Structured Output | Pydantic v2 + `llm.with_structured_output()` |
| Vector DB | ChromaDB — persistent, cosine similarity search |
| Relational DB | SQLite — mock hospital Electronic Health Record (EHR) |
| State Persistence | LangGraph `MemorySaver` checkpointer |

---

## Project Structure

```
Project_folder/
├── .env.example              # Copy to .env — add your Google API key
├── .gitignore
├── README.md
├── pyproject.toml            # Package config — enables editable install
│
├── src/
│   └── um_agent/             # Core Python package
│       ├── config.py         # Single source of truth: paths, model, settings
│       ├── agents/           # LangGraph node functions
│       │   ├── intake.py
│       │   ├── policy_retrieval.py
│       │   ├── evaluation.py
│       │   └── ehr_fetch.py
│       ├── graph/            # LangGraph state + graph builder
│       │   ├── state.py
│       │   └── builder.py
│       ├── schemas/          # Pydantic v2 models
│       │   └── models.py
│       ├── tools/            # LangGraph tool definitions
│       │   └── ehr_query.py
│       └── db/               # Database initialization & seeding
│           ├── seed_sqlite.py
│           └── seed_chromadb.py
│
├── scripts/
│   ├── setup_databases.py    # CLI entrypoint: seeds SQLite + ChromaDB
│   └── run_demo.py           # CLI demo runner (no UI)
│
├── app.py                    # Streamlit frontend
├── .streamlit/config.toml    # Dark theme configuration
│
├── data/                     # Auto-generated at runtime, gitignored
│   ├── ehr.db                # SQLite EHR with mock patient records
│   └── chroma_db/            # ChromaDB with indexed insurance policies
│
└── tests/                    # Unit & integration tests
```

---

## Getting Started

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 2. Install the package and all dependencies
pip install -e .

# 3. Set your Google API key
cp .env.example .env
# Open .env and set: GOOGLE_API_KEY=your_key_here
# Get a free key at: https://aistudio.google.com/app/apikey

# 4. Seed the local databases
python scripts/setup_databases.py

# 5. Launch the Streamlit UI
streamlit run app.py
```

---

## Interactive UI

The project includes a Streamlit frontend with:
- **Preset scenarios** — select Sarah Jenkins (approve path) or Marcus Vance (escalate path)
- **Custom input** — paste any authorization note and see how the agent processes it
- **Real-time execution trace** — expandable step-by-step view of each agent node
- **Decision banner** — clear approve/escalate outcome with clinical rationale
- **Metrics dashboard** — processing time, LLM calls, EHR fetch count

```bash
streamlit run app.py
# Opens at http://localhost:8501
```

---

## Demo Scenarios

Two mock patients are seeded to demonstrate the two main decision paths:

| Patient | Condition | History | Expected Decision |
|---------|-----------|---------|------------------|
| Sarah Jenkins (PT-9942) | Sciatica — M54.41 | 6 weeks PT + NSAID trial, both failed | ✅ **Auto-Approved** |
| Marcus Vance (PT-1105) | Low back pain — M54.5 | No prior conservative therapy on record | 🔴 **Escalated to Human Review** |

---

