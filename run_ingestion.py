import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config import settings
from backend.rag.ingestion import ingest_document, sync_knowledge_base, get_kb_collection

def run_ingestion(target_dir: str | None = None, force: bool = False):
    if target_dir is None:
        target_dir = settings.UPLOAD_DIR

    print("=" * 60)
    print("   AUTOMATIC KNOWLEDGE BASE RAG INGESTION")
    print("=" * 60)
    print(f"[INFO] Target Directory: {target_dir}")

    res = sync_knowledge_base(target_dir, force_reingest=force)
    collection = get_kb_collection()

    print("-" * 60)
    print("INGESTION SUMMARY:")
    print(f"  - Total Files Found:     {res.get('total_files_found', 0)}")
    print(f"  - Already Indexed:       {res.get('already_indexed', 0)}")
    print(f"  - Newly Ingested:        {res.get('newly_ingested', 0)}")
    print(f"  - New Chunks Created:    {res.get('new_chunks_added', 0)}")
    print(f"  - Total Vector DB Count: {collection.count()} chunks")
    
    if res.get("errors"):
        print("\n[!] Errors encountered:")
        for err in res["errors"]:
            print(f"  - {err}")
    print("=" * 60)

if __name__ == "__main__":
    target_directory = sys.argv[1] if len(sys.argv) > 1 else None
    force_flag = "--force" in sys.argv or "-f" in sys.argv
    run_ingestion(target_directory, force=force_flag)

