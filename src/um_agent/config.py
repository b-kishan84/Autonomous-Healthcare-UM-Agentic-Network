"""
src/um_agent/config.py
======================
Single source of truth for all project-wide configuration:
paths, model names, collection names, database identifiers.

Every other module imports from here — nothing is hardcoded elsewhere.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env from project root ────────────────────────────────────────────────
# Walks up from this file's location to find the .env at the project root.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]   # ZeOmega/
load_dotenv(_PROJECT_ROOT / ".env")

# ── Directory Paths ────────────────────────────────────────────────────────────
DATA_DIR     = _PROJECT_ROOT / "data"
SQLITE_PATH  = DATA_DIR / "ehr.db"
CHROMA_DIR   = DATA_DIR / "chroma_db"

# Ensure the data directory always exists when this module is imported
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── LLM Configuration ──────────────────────────────────────────────────────────
GOOGLE_API_KEY      = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL_NAME   = "gemini-2.5-flash"

# ── ChromaDB Configuration ─────────────────────────────────────────────────────
POLICY_COLLECTION_NAME = "medical_policies"
POLICY_RETRIEVAL_K     = 2   # number of top-k policies to retrieve per query

# ── Graph Configuration ────────────────────────────────────────────────────────
MAX_EHR_RETRIES = 1  # maximum times the graph can loop through EHR fetch
