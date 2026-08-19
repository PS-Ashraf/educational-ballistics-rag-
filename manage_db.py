import os
import sys

# Ensure project root is in path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.rag.ingestion import get_kb_collection

def main():
    print("=" * 60)
    print("   CHROMA DB MANAGEMENT UTILITY")
    print("=" * 60)

    try:
        collection = get_kb_collection()
        count = collection.count()
        print(f"\n[INFO] Collection Name : '{collection.name}'")
        print(f"[INFO] Total Documents  : {count}")
    except Exception as e:
        print(f"\n[ERROR] Failed to access ChromaDB collection: {e}")
        return

    while True:
        print("\n" + "-" * 40)
        print("Please choose an option:")
        print("1. View summary & sample stored entries")
        print("2. Delete specific document by source filename")
        print("3. Clear ALL data from ChromaDB (Full Reset)")
        print("4. Exit")
        print("-" * 40)

        choice = input("Enter option number (1-4): ").strip()

        if choice == "1":
            if count == 0:
                print("\n[!] The database is currently empty.")
            else:
                data = collection.get(limit=5)
                documents = data.get('documents') or []
                metadatas = data.get('metadatas') or []
                print(f"\n--- Database Preview (Showing top {len(data['ids'])} of {count} entries) ---")
                for idx, (doc_id, doc_text, meta) in enumerate(zip(data['ids'], documents, metadatas), 1):
                    source = meta.get('source', 'Unknown') if meta else 'Unknown'
                    chunk_idx = meta.get('chunk_index', '?') if meta else '?'
                    preview = doc_text.replace('\n', ' ')[:100] + "..." if len(doc_text) > 100 else doc_text
                    # Safe print for Windows CP1252 console
                    safe_preview = preview.encode('ascii', errors='ignore').decode('ascii')
                    print(f"\nEntry #{idx}:")
                    print(f"  ID         : {doc_id}")
                    print(f"  Source File: {source} (Chunk {chunk_idx})")
                    print(f"  Snippet    : {safe_preview}")

        elif choice == "2":
            if count == 0:
                print("\n[!] Collection is empty. Nothing to delete.")
                continue

            target_filename = input("\nEnter the source filename to delete (e.g. ballistics_safety.txt): ").strip()
            if not target_filename:
                print("[!] No filename provided.")
                continue

            # Find matching items
            existing = collection.get(where={"source": target_filename})
            match_count = len(existing["ids"]) if existing and existing.get("ids") else 0

            if match_count == 0:
                print(f"[!] No entries found with source filename '{target_filename}'.")
            else:
                confirm = input(f"Found {match_count} entries for '{target_filename}'. Delete them? (y/N): ").strip().lower()
                if confirm == 'y':
                    collection.delete(where={"source": target_filename})
                    count = collection.count()
                    print(f"[SUCCESS] Deleted {match_count} entries. Remaining total: {count}")
                else:
                    print("Deletion cancelled.")

        elif choice == "3":
            if count == 0:
                print("\n[!] Collection is already empty.")
                continue

            confirm = input(f"\n[WARNING] Are you sure you want to CLEAR ALL {count} entries from ChromaDB? (y/N): ").strip().lower()
            if confirm == 'y':
                all_entries = collection.get()
                if all_entries["ids"]:
                    collection.delete(ids=all_entries["ids"])
                count = collection.count()
                print(f"[SUCCESS] Database cleared. Total entries remaining: {count}")
            else:
                print("Operation cancelled.")

        elif choice == "4":
            print("\nExiting utility.")
            break
        else:
            print("[!] Invalid option. Please enter 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()
