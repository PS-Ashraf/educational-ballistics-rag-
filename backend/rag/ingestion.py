import os
import re
import json
import math
from pypdf import PdfReader
from backend.config import settings
from backend.rag.embeddings import get_embedding_function

DB_FILE = os.path.join(settings.VECTOR_DB_DIR, "vector_kb.json")

def _load_db() -> list[dict]:
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_db(data: list[dict]):
    os.makedirs(settings.VECTOR_DB_DIR, exist_ok=True)
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    try:
        reader = PdfReader(file_path, strict=False)
        for page in reader.pages:
            try:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            except Exception:
                continue
    except Exception as e:
        print(f"[PDF Extract Notice] Error reading {file_path}: {e}")
    return text


def extract_text_from_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def clean_text(text: str) -> str:
    # Normalize multiple newlines and trim horizontal whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()

def chunk_text(text: str, chunk_size: int = 350, chunk_overlap: int = 50) -> list[str]:
    """
    High-precision sentence/line level chunking for exact RAG matching.
    Breaks text into smaller units (~350 characters) so each chunk focuses on a precise fact.
    """
    # Split text by paragraphs first, then by sentences/lines
    raw_blocks = text.split("\n\n")
    lines_or_sentences = []
    
    for block in raw_blocks:
        # Split paragraph into sentence units
        sentences = re.split(r'(?<=[.!?])\s+', block.strip())
        for s in sentences:
            s_clean = s.strip()
            if s_clean:
                lines_or_sentences.append(s_clean)

    chunks = []
    current_chunk = []
    current_len = 0

    for item in lines_or_sentences:
        item_len = len(item)
        if current_len + item_len > chunk_size and current_chunk:
            chunk_str = " ".join(current_chunk)
            chunks.append(chunk_str)
            
            # Keep overlap context from previous sentences
            overlap_chunk = []
            overlap_len = 0
            for prev_item in reversed(current_chunk):
                if overlap_len + len(prev_item) <= chunk_overlap:
                    overlap_chunk.insert(0, prev_item)
                    overlap_len += len(prev_item)
                else:
                    break
            
            current_chunk = overlap_chunk + [item]
            current_len = sum(len(x) for x in current_chunk) + len(current_chunk)
        else:
            current_chunk.append(item)
            current_len += item_len + 1

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks



def ingest_document(file_path: str) -> dict:
    if not os.path.exists(file_path):
        return {"status": "error", "message": f"File {file_path} does not exist"}

    filename = os.path.basename(file_path)
    _, ext = os.path.splitext(filename.lower())
    
    if ext == ".pdf":
        raw_text = extract_text_from_pdf(file_path)
    elif ext in [".txt", ".md", ".markdown"]:
        raw_text = extract_text_from_txt(file_path)
    else:
        return {"status": "error", "message": f"Unsupported file extension: {ext}"}

    cleaned = clean_text(raw_text)
    if not cleaned:
        return {"status": "error", "message": "Document contains no extractable text"}

    chunks = chunk_text(cleaned)
    emb_fn = get_embedding_function()
    embeddings = emb_fn(chunks)

    db = _load_db()
    # Remove existing chunks of same file
    db = [item for item in db if item.get("metadata", {}).get("source") != filename]

    for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        # Ensure embedding is a list of plain python floats
        float_emb = [float(x) for x in emb]
        db.append({
            "id": f"{filename}_{idx}",
            "content": chunk,
            "embedding": float_emb,
            "metadata": {
                "source": filename,
                "chunk_index": idx,
                "path": file_path
            }
        })

    _save_db(db)
        
    return {
        "status": "success",
        "chunks_count": len(chunks),
        "filename": filename
    }

def sync_knowledge_base(target_dir: str = None, force_reingest: bool = False) -> dict:
    """
    Scans the knowledge base directory for supported files (.pdf, .txt, .md).
    Automatically ingests any new/unindexed documents into the vector store.
    """
    if target_dir is None:
        target_dir = settings.UPLOAD_DIR

    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    valid_exts = ('.pdf', '.txt', '.md', '.markdown')
    db = _load_db()
    indexed_files = {item.get("metadata", {}).get("source") for item in db if item.get("metadata")}

    files_found = []
    # Search target_dir and parent knowledge_base dir if different
    dirs_to_search = [target_dir]
    kb_parent = os.path.abspath(os.path.join(target_dir, ".."))
    if os.path.exists(kb_parent) and kb_parent not in dirs_to_search:
        dirs_to_search.append(kb_parent)

    for d in dirs_to_search:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                # Skip vector_store directory if inside search path
                if "vector_store" in root:
                    continue
                for fname in files:
                    if fname.lower().endswith(valid_exts):
                        fpath = os.path.join(root, fname)
                        if fpath not in [f[1] for f in files_found]:
                            files_found.append((fname, fpath))

    new_ingested = 0
    total_new_chunks = 0
    already_indexed = 0
    errors = []

    for fname, fpath in files_found:
        if not force_reingest and fname in indexed_files:
            already_indexed += 1
            continue

        res = ingest_document(fpath)
        if res.get("status") == "success":
            new_ingested += 1
            total_new_chunks += res.get("chunks_count", 0)
        else:
            errors.append(f"{fname}: {res.get('message')}")

    return {
        "status": "success",
        "total_files_found": len(files_found),
        "already_indexed": already_indexed,
        "newly_ingested": new_ingested,
        "new_chunks_added": total_new_chunks,
        "errors": errors
    }


def list_documents() -> list[dict]:
    db = _load_db()
    seen = {}
    for item in db:
        meta = item.get("metadata", {})
        src = meta.get("source")
        if src and src not in seen:
            seen[src] = {
                "filename": src,
                "path": meta.get("path"),
                "chunks": 1
            }
        elif src:
            seen[src]["chunks"] += 1
            
    return list(seen.values())

def get_document_chunks(filename: str) -> list[dict]:
    db = _load_db()
    chunks = []
    for item in db:
        if item.get("metadata", {}).get("source") == filename:
            chunks.append({
                "id": item.get("id"),
                "content": item.get("content"),
                "chunk_index": item.get("metadata", {}).get("chunk_index", 0)
            })
    chunks.sort(key=lambda x: x.get("chunk_index", 0))
    return chunks

def delete_document(filename: str) -> dict:
    db = _load_db()
    initial_count = len(db)
    db = [item for item in db if item.get("metadata", {}).get("source") != filename]
    _save_db(db)
    
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass
            
    removed_chunks = initial_count - len(db)
    return {
        "status": "success",
        "removed_chunks": removed_chunks,
        "filename": filename
    }

class MockCollection:
    name: str = "ballistics_knowledge_base"

    def count(self) -> int:
        return len(_load_db())

    def get(self, limit: int | None = None, where: dict | None = None) -> dict:
        db = _load_db()
        if where and "source" in where:
            target_src = where["source"]
            db = [item for item in db if item.get("metadata", {}).get("source") == target_src]

        if limit is not None:
            db = db[:limit]

        ids = [item["id"] for item in db]
        documents = [item["content"] for item in db]
        metadatas = [item.get("metadata", {}) for item in db]
        return {"ids": ids, "documents": documents, "metadatas": metadatas}

    def delete(self, ids: list[str] | None = None, where: dict | None = None) -> int:
        db = _load_db()
        initial_len = len(db)
        if ids:
            ids_set = set(ids)
            db = [item for item in db if item["id"] not in ids_set]
        elif where and "source" in where:
            target_src = where["source"]
            db = [item for item in db if item.get("metadata", {}).get("source") != target_src]

        _save_db(db)
        return initial_len - len(db)

def get_kb_collection():
    return MockCollection()

