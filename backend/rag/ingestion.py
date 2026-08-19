import os
import re
import json
import math
import pymupdf as fitz # PyMuPDF
from backend.config import settings
from backend.rag.embeddings import get_embedding_function

import chromadb

_chroma_client = None

def get_kb_collection():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.VECTOR_DB_DIR)
        
    return _chroma_client.get_or_create_collection(
        name="ballistics_knowledge_base",
        embedding_function=get_embedding_function()
    )

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            try:
                page_text = page.get_text("text")
                if page_text:
                    text += str(page_text) + "\n"
            except Exception:
                continue
        doc.close()
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

    collection = get_kb_collection()
    
    # Remove existing chunks of same file
    try:
        collection.delete(where={"source": filename})
    except Exception:
        pass

    # Ensure embedding is a list of plain python floats
    float_embs = [[float(x) for x in emb] for emb in embeddings]
    
    ids = [f"{filename}_{idx}" for idx in range(len(chunks))]
    metadatas = [{"source": filename, "chunk_index": idx, "path": file_path} for idx in range(len(chunks))]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=float_embs, # type: ignore
        metadatas=metadatas  # type: ignore
    )
        
    return {
        "status": "success",
        "chunks_count": len(chunks),
        "filename": filename
    }

def sync_knowledge_base(target_dir: str | None = None, force_reingest: bool = False) -> dict:
    """
    Scans the knowledge base directory for supported files (.pdf, .txt, .md).
    Automatically ingests any new/unindexed documents into the vector store.
    """
    if target_dir is None:
        target_dir = settings.UPLOAD_DIR

    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    valid_exts = ('.pdf', '.txt', '.md', '.markdown')
    collection = get_kb_collection()
    res = collection.get(include=["metadatas"])
    indexed_files = set()
    for meta in (res.get("metadatas") or []):
        if meta and "source" in meta:
            indexed_files.add(meta["source"])

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
    collection = get_kb_collection()
    res = collection.get(include=["metadatas"])
    seen: dict[str, dict] = {}
    for meta in (res.get("metadatas") or []):
        if meta:
            src = meta.get("source")
            if isinstance(src, str):
                if src not in seen:
                    seen[src] = {
                        "filename": src,
                        "path": meta.get("path"),
                        "chunks": 1
                    }
                else:
                    seen[src]["chunks"] += 1
                
    return list(seen.values())

def get_document_chunks(filename: str) -> list[dict]:
    collection = get_kb_collection()
    res = collection.get(where={"source": filename}, include=["metadatas", "documents"])
    chunks = []
    
    if res and res.get("ids"):
        for i in range(len(res["ids"])):
            meta = res["metadatas"][i] if res.get("metadatas") else {}
            doc = res["documents"][i] if res.get("documents") else ""
            chunks.append({
                "id": res["ids"][i],
                "content": doc,
                "chunk_index": meta.get("chunk_index", 0)
            })
            
    chunks.sort(key=lambda x: x.get("chunk_index", 0))
    return chunks

def delete_document(filename: str) -> dict:
    collection = get_kb_collection()
    initial_count = collection.count()
    try:
        collection.delete(where={"source": filename})
    except Exception:
        pass
        
    removed_chunks = initial_count - collection.count()
    
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass
            
    return {
        "status": "success",
        "removed_chunks": removed_chunks,
        "filename": filename
    }

# get_kb_collection moved to the top of the file
