"""
src/um_agent/db/seed_chromadb.py
=================================
Initializes and seeds the ChromaDB persistent vector store with
mock insurance medical necessity policy documents.

ChromaDB converts each policy document into dense vector embeddings using
its default sentence-transformer model (no API key required).
At runtime, the Policy Retrieval Node queries this store with the procedure
type to find the most relevant coverage criteria.

Collection:
  - medical_policies  : 4 insurance coverage / medical necessity guidelines

Policies:
  - POL-MRI-001   MRI Lumbar Spine         (primary demo policy)
  - POL-MRI-002   MRI Cervical Spine
  - POL-PT-001    Physical Therapy — Musculoskeletal
  - POL-DRUG-001  Adalimumab (Humira) — Rheumatoid Arthritis
"""

import logging
import chromadb
from chromadb.config import Settings
from um_agent.config import CHROMA_DIR, POLICY_COLLECTION_NAME

# ── Logging ────────────────────────────────────────────────────────────────────
log = logging.getLogger(__name__)

# ── Policy Documents ───────────────────────────────────────────────────────────
# Rich natural-language policy texts.
# ChromaDB embeds `document` into a vector; `metadata` is used for filtering.

_POLICIES: list[dict] = [
    {
        "id": "POL-MRI-001",
        "document": (
            "Policy ID: POL-MRI-001\n"
            "Policy Title: Magnetic Resonance Imaging (MRI) — Lumbar Spine\n"
            "Effective Date: 2024-01-01\n\n"
            "COVERAGE CRITERIA — ALL must be met for approval:\n"
            "1. SYMPTOM DURATION: Documented low back pain with radiculopathy "
            "(pain radiating down the leg / sciatica) for a minimum of six (6) "
            "consecutive weeks.\n"
            "2. CONSERVATIVE THERAPY: Documented failure of at least one of: "
            "physical therapy (PT), chiropractic care, or NSAID pharmacotherapy.\n"
            "3. DOCUMENTED FAILURE: Must be documented by a treating physician or "
            "licensed physical therapist — anecdotal self-reporting is insufficient.\n\n"
            "EXCLUSIONS: Not covered for acute non-specific back pain < 6 weeks "
            "or if conservative therapy has not been attempted.\n\n"
            "ICD-10: M54.4, M54.41, M54.42 | CPT: 72148, 72149\n"
            "Review Type: Standard Prior Authorization | Turnaround: 3 business days."
        ),
        "metadata": {
            "policy_id":      "POL-MRI-001",
            "procedure_type": "MRI",
            "body_part":      "lumbar_spine",
            "icd10_codes":    "M54.4, M54.41, M54.42",
            "cpt_codes":      "72148, 72149",
        },
    },
    {
        "id": "POL-MRI-002",
        "document": (
            "Policy ID: POL-MRI-002\n"
            "Policy Title: Magnetic Resonance Imaging (MRI) — Cervical Spine\n"
            "Effective Date: 2024-01-01\n\n"
            "COVERAGE CRITERIA — ALL must be met for approval:\n"
            "1. SYMPTOM DURATION: Documented neck pain with arm radiculopathy or "
            "myelopathy for a minimum of four (4) consecutive weeks.\n"
            "2. CONSERVATIVE THERAPY: Documented failure of physical therapy, "
            "cervical traction, or NSAID use for at least four (4) weeks.\n"
            "3. NEUROLOGICAL SYMPTOMS: New or progressive weakness, sensory loss, "
            "or reflex changes must be clinically documented.\n\n"
            "EXCLUSIONS: Not covered for acute neck strain without neurological "
            "involvement of less than 4 weeks.\n\n"
            "ICD-10: M54.2, M50.1 | CPT: 72141, 72142\n"
            "Review Type: Standard Prior Authorization | Turnaround: 3 business days."
        ),
        "metadata": {
            "policy_id":      "POL-MRI-002",
            "procedure_type": "MRI",
            "body_part":      "cervical_spine",
            "icd10_codes":    "M54.2, M50.1",
            "cpt_codes":      "72141, 72142",
        },
    },
    {
        "id": "POL-PT-001",
        "document": (
            "Policy ID: POL-PT-001\n"
            "Policy Title: Physical Therapy — Outpatient Musculoskeletal Conditions\n"
            "Effective Date: 2024-01-01\n\n"
            "COVERAGE CRITERIA:\n"
            "1. DIAGNOSIS: Musculoskeletal diagnosis with ICD-10 code from an MD/DO.\n"
            "2. FUNCTIONAL LIMITATION: PT must restore or maintain function limited "
            "by the condition.\n"
            "3. AUTHORIZED VISITS: Up to 12 outpatient visits per calendar year. "
            "Re-authorization required after 12 visits with functional progress notes.\n"
            "4. PROVIDER: Licensed Physical Therapist (PT) or PTA under PT supervision.\n\n"
            "EXCLUSIONS: Not covered for maintenance therapy with no measurable "
            "functional progress.\n\n"
            "CPT: 97110, 97530, 97140\n"
            "Review Type: Standard Prior Authorization | Turnaround: 2 business days."
        ),
        "metadata": {
            "policy_id":      "POL-PT-001",
            "procedure_type": "physical_therapy",
            "body_part":      "musculoskeletal",
            "cpt_codes":      "97110, 97530, 97140",
        },
    },
    {
        "id": "POL-DRUG-001",
        "document": (
            "Policy ID: POL-DRUG-001\n"
            "Policy Title: Adalimumab (Humira) — Rheumatoid Arthritis (RA)\n"
            "Effective Date: 2024-01-01\n\n"
            "COVERAGE CRITERIA — ALL must be met for approval:\n"
            "1. DIAGNOSIS: Confirmed moderate-to-severe Rheumatoid Arthritis (M05/M06) "
            "documented by a board-certified Rheumatologist.\n"
            "2. STEP THERAPY: Documented inadequate response or intolerance to at least "
            "two (2) conventional DMARDs, including methotrexate (unless contraindicated), "
            "for a minimum of three (3) months each.\n"
            "3. LAB VALUES: CBC, CMP, TB screening (QuantiFERON/PPD), and Hepatitis B "
            "surface antigen within the past 12 months.\n"
            "4. PREGNANCY: Female members of childbearing age must confirm contraceptive "
            "use or documented intent to become pregnant.\n\n"
            "EXCLUSIONS: Active serious infection, active TB, severe heart failure.\n\n"
            "ICD-10: M05, M06 | HCPCS: J0135\n"
            "Review Type: Specialty Drug Prior Authorization | Turnaround: 5 business days."
        ),
        "metadata": {
            "policy_id":      "POL-DRUG-001",
            "procedure_type": "specialty_drug",
            "drug_name":      "adalimumab",
            "brand_name":     "Humira",
            "icd10_codes":    "M05, M06",
            "hcpcs_codes":    "J0135",
        },
    },
]


# ── Internal Helpers ───────────────────────────────────────────────────────────

def _get_client() -> chromadb.PersistentClient:
    """Returns a disk-backed ChromaDB client. Telemetry disabled."""
    return chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )


def _verify(collection: chromadb.Collection) -> None:
    """Runs a test similarity query to confirm embeddings are working."""
    test_query = "Patient requesting MRI for lower back pain radiating down the leg"
    log.info(f'  Test query: "{test_query}"')

    results = collection.query(
        query_texts=[test_query],
        n_results=2,
        include=["metadatas", "distances"],
    )

    log.info("  Top matches:")
    for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
        score = round((1 - dist) * 100, 1)
        log.info(
            f"    [{meta['policy_id']}]  {meta['procedure_type']} / "
            f"{meta.get('body_part', 'N/A')}  →  similarity {score}%"
        )


# ── Public API ─────────────────────────────────────────────────────────────────

def run() -> None:
    """Initialize the ChromaDB collection and upsert all policies. Safe to re-run."""
    log.info("Initializing ChromaDB policy vector store...")
    log.info(f"  Path       : {CHROMA_DIR}")
    log.info(f"  Collection : {POLICY_COLLECTION_NAME}")

    client     = _get_client()
    collection = client.get_or_create_collection(
        name=POLICY_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},   # cosine similarity for text
    )

    collection.upsert(
        ids       =[p["id"]       for p in _POLICIES],
        documents =[p["document"] for p in _POLICIES],
        metadatas =[p["metadata"] for p in _POLICIES],
    )
    log.info(f"  Upserted {len(_POLICIES)} policy documents.")

    log.info("─" * 60)
    log.info("ChromaDB Seeding Verification")
    log.info("─" * 60)
    _verify(collection)
    log.info(f"  Total documents in store: {collection.count()}")
    log.info("─" * 60)

    log.info("✅  ChromaDB policy vector store ready.")
