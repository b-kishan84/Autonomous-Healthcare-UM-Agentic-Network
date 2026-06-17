"""
scripts/setup_databases.py
===========================
CLI entrypoint for Phase 1 database initialization.

Seeds both the SQLite EHR database and the ChromaDB policy vector store
with synthetic data for local development and portfolio demonstration.

Prerequisites:
  pip install -e .          (installs um_agent as an editable package)

Usage (from project root, with .venv active):
  python scripts/setup_databases.py
"""

import logging

# ── Configure logging FIRST — before any application imports ──────────────────
# This ensures log messages emitted during module import are formatted correctly.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Application imports ────────────────────────────────────────────────────────
# um_agent is installed as an editable package via `pip install -e .`
# No sys.path manipulation needed.
from um_agent.db.seed_sqlite import run as seed_sqlite        # noqa: E402
from um_agent.db.seed_chromadb import run as seed_chromadb    # noqa: E402


def main() -> None:
    log.info("=" * 60)
    log.info("  🏥  UM Agentic Network — Database Setup")
    log.info("=" * 60)

    log.info("\n[1/2] Seeding SQLite EHR Database...")
    seed_sqlite()

    log.info("\n[2/2] Seeding ChromaDB Policy Vector Store...")
    seed_chromadb()

    log.info("\n" + "=" * 60)
    log.info("  ✅  Phase 1 Complete. Both databases are initialized.")
    log.info("  ➡️   Say 'Proceed to Phase 2' when ready.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
