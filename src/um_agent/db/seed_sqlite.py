"""
src/um_agent/db/seed_sqlite.py
================================
Initializes and seeds the local SQLite database that acts as the
hospital's Electronic Health Record (EHR) system.

Tables:
  - patients          : Demographics and insurance info
  - clinical_history  : Diagnoses, ICD-10 codes, severity
  - treatments        : Prior therapy / conservative treatment history
  - medications       : Current and past medication records

Seed Patients:
  - PT-9942  Sarah Jenkins  — Has all required prior authorizations (→ Auto-Approve)
  - PT-1105  Marcus Vance   — Missing prior therapy records (→ Escalate)
"""

import sqlite3
import logging
from um_agent.config import SQLITE_PATH

# ── Logging ────────────────────────────────────────────────────────────────────
log = logging.getLogger(__name__)

# ── Schema DDL ─────────────────────────────────────────────────────────────────
_SCHEMA_SQL = """
-- ─── Patients ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS patients (
    patient_id        TEXT PRIMARY KEY,   -- e.g. PT-9942
    full_name         TEXT NOT NULL,
    date_of_birth     TEXT NOT NULL,      -- ISO-8601 YYYY-MM-DD
    gender            TEXT NOT NULL,
    insurer_id        TEXT NOT NULL,
    primary_physician TEXT NOT NULL
);

-- ─── Clinical History ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clinical_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      TEXT NOT NULL REFERENCES patients(patient_id),
    diagnosis_date  TEXT NOT NULL,        -- ISO-8601 YYYY-MM-DD
    diagnosis_code  TEXT NOT NULL,        -- ICD-10 code
    diagnosis_desc  TEXT NOT NULL,
    severity        TEXT NOT NULL,        -- mild | moderate | severe
    UNIQUE(patient_id, diagnosis_code)    -- prevents duplicate rows on re-seed
);

-- ─── Treatments ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS treatments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      TEXT NOT NULL REFERENCES patients(patient_id),
    treatment_type  TEXT NOT NULL,        -- physical_therapy | chiropractic | etc.
    start_date      TEXT NOT NULL,
    end_date        TEXT,                 -- NULL = ongoing
    duration_weeks  INTEGER,
    outcome         TEXT NOT NULL,        -- no_improvement | partial_relief | resolved
    provider        TEXT NOT NULL,
    UNIQUE(patient_id, treatment_type, start_date)  -- prevents duplicate rows on re-seed
);

-- ─── Medications ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS medications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      TEXT NOT NULL REFERENCES patients(patient_id),
    drug_name       TEXT NOT NULL,
    drug_class      TEXT NOT NULL,        -- NSAID | opioid | DMARD | etc.
    prescribed_date TEXT NOT NULL,
    end_date        TEXT,                 -- NULL = ongoing
    response        TEXT NOT NULL,        -- ineffective | effective | partial
    UNIQUE(patient_id, drug_name, prescribed_date)  -- prevents duplicate rows on re-seed
);
"""

# ── Seed Data ──────────────────────────────────────────────────────────────────

_PATIENTS = [
    # PT-9942: Sarah Jenkins — SHOULD be auto-approved.
    # Has 6-week PT course + NSAID trial → meets all MRI-Lumbar criteria.
    ("PT-9942", "Sarah Jenkins", "1982-04-15", "Female", "INS-882341", "Dr. Priya Sharma"),

    # PT-1105: Marcus Vance — SHOULD be escalated.
    # Has back pain diagnosis but NO documented prior conservative therapy.
    ("PT-1105", "Marcus Vance", "1975-11-03", "Male",   "INS-551882", "Dr. Raymond Cole"),
]

_CLINICAL_HISTORY = [
    # Sarah Jenkins — chronic low back pain with left-sided sciatica
    ("PT-9942", "2024-11-10", "M54.41", "Lumbago with sciatica, left side", "moderate"),

    # Marcus Vance — non-specific low back pain, no radiculopathy documented
    ("PT-1105", "2025-01-22", "M54.5",  "Low back pain, unspecified",        "mild"),
]

_TREATMENTS = [
    # Sarah Jenkins — completed 6-week PT course with no improvement
    (
        "PT-9942", "physical_therapy",
        "2024-11-20", "2025-01-01",
        6,                                  # duration_weeks ≥ 6 → satisfies criterion
        "no_improvement",
        "ActiveCare Physical Therapy Center",
    ),
    # Marcus Vance — intentionally NO treatment rows (missing record)
]

_MEDICATIONS = [
    # Sarah Jenkins — NSAID trial: Naproxen, ineffective → satisfies criterion
    ("PT-9942", "Naproxen 500mg", "NSAID", "2024-11-15", "2025-01-10", "ineffective"),

    # Marcus Vance — intentionally NO medication rows (missing record)
]


# ── Internal Helpers ───────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    """Returns a SQLite connection with foreign-key enforcement and Row factory."""
    conn = sqlite3.connect(SQLITE_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_SQL)
    conn.commit()
    log.info("Schema applied (CREATE IF NOT EXISTS — idempotent).")


def _seed_table(conn: sqlite3.Connection, table: str, sql: str, rows: list) -> None:
    conn.executemany(sql, rows)
    conn.commit()
    log.info(f"  {table:<20} → seeded {len(rows)} row(s).")


def _verify(conn: sqlite3.Connection) -> None:
    """Prints a structured EHR summary for every seeded patient."""
    log.info("─" * 60)
    log.info("EHR Seeding Verification")
    log.info("─" * 60)

    for p in conn.execute("SELECT * FROM patients").fetchall():
        pid = p["patient_id"]
        log.info(f"\n  [{pid}]  {p['full_name']}  |  Physician: {p['primary_physician']}")

        for d in conn.execute(
            "SELECT diagnosis_code, diagnosis_desc, severity FROM clinical_history WHERE patient_id=?", (pid,)
        ).fetchall():
            log.info(f"    Dx   [{d['diagnosis_code']}]  {d['diagnosis_desc']}  ({d['severity']})")

        tx = conn.execute(
            "SELECT treatment_type, duration_weeks, outcome FROM treatments WHERE patient_id=?", (pid,)
        ).fetchall()
        tx_str = (
            f"{tx[0]['treatment_type']} — {tx[0]['duration_weeks']}wks — {tx[0]['outcome']}"
            if tx else "⚠  NO prior therapy on record"
        )
        log.info(f"    Tx   {tx_str}")

        meds = conn.execute(
            "SELECT drug_name, drug_class, response FROM medications WHERE patient_id=?", (pid,)
        ).fetchall()
        meds_str = (
            f"{meds[0]['drug_name']} ({meds[0]['drug_class']}) — {meds[0]['response']}"
            if meds else "⚠  NO medication trial on record"
        )
        log.info(f"    Meds {meds_str}")

    log.info("─" * 60)


# ── Public API ─────────────────────────────────────────────────────────────────

def run() -> None:
    """Initialize schema and seed all EHR tables. Safe to call multiple times."""
    log.info("Initializing SQLite EHR database...")
    log.info(f"  Path: {SQLITE_PATH}")

    with _connect() as conn:
        _create_schema(conn)
        _seed_table(
            conn, "patients",
            "INSERT OR IGNORE INTO patients VALUES (?,?,?,?,?,?)",
            _PATIENTS,
        )
        _seed_table(
            conn, "clinical_history",
            "INSERT OR IGNORE INTO clinical_history (patient_id,diagnosis_date,diagnosis_code,diagnosis_desc,severity) VALUES (?,?,?,?,?)",
            _CLINICAL_HISTORY,
        )
        _seed_table(
            conn, "treatments",
            "INSERT OR IGNORE INTO treatments (patient_id,treatment_type,start_date,end_date,duration_weeks,outcome,provider) VALUES (?,?,?,?,?,?,?)",
            _TREATMENTS,
        )
        _seed_table(
            conn, "medications",
            "INSERT OR IGNORE INTO medications (patient_id,drug_name,drug_class,prescribed_date,end_date,response) VALUES (?,?,?,?,?,?)",
            _MEDICATIONS,
        )
        _verify(conn)

    log.info(f"✅  SQLite EHR database ready.")
