"""
src/um_agent/agents/policy_retrieval.py
========================================
Node 2: Policy Retrieval Agent

Queries the ChromaDB vector store to find the most relevant insurance
policy guidelines based on the procedure type extracted by the Intake node.
"""

from __future__ import annotations

import logging
import chromadb
from chromadb.config import Settings
from um_agent.config import CHROMA_DIR, POLICY_COLLECTION_NAME, POLICY_RETRIEVAL_K
from um_agent.graph.state import UMState

log = logging.getLogger(__name__)


def policy_retrieval_node(state: UMState) -> dict:
    """
    LangGraph node function: retrieves matching insurance policies from
    ChromaDB using semantic similarity search.

    Reads:   state["extracted_data"] (needs "procedure_requested" and "diagnosis_description")
    Writes:  state["retrieved_policies"]
    """
    extracted = state["extracted_data"]
    procedure = extracted["procedure_requested"]
    diagnosis = extracted["diagnosis_description"]

    # Build a natural-language query combining procedure + diagnosis context
    query = f"{procedure} for {diagnosis}"

    log.info("─── Policy Retrieval Node ───")
    log.info(f"  Query: \"{query}\"")

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_collection(POLICY_COLLECTION_NAME)

    results = collection.query(
        query_texts=[query],
        n_results=POLICY_RETRIEVAL_K,
        include=["documents", "metadatas", "distances"],
    )

    policies: list[str] = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        similarity = round((1 - dist) * 100, 1)
        policy_id = meta.get("policy_id", "Unknown")
        log.info(f"  Match: [{policy_id}]  similarity={similarity}%")
        policies.append(doc)

    if not policies:
        log.warning("  ⚠ No matching policies found in vector store.")
        policies = ["No matching policy found for the requested procedure."]

    return {"retrieved_policies": policies}
