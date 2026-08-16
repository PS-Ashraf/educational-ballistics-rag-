import math
from typing import Any, Sequence
from backend.rag.ingestion import _load_db
from backend.rag.embeddings import get_embedding_function

def cosine_similarity(vec_a: Any, vec_b: Any) -> float:
    # Ensure float conversion
    a_floats = [float(x) for x in vec_a]
    b_floats = [float(x) for x in vec_b]
    
    dot = sum(a * b for a, b in zip(a_floats, b_floats))
    norm_a = math.sqrt(sum(a * a for a in a_floats))
    norm_b = math.sqrt(sum(b * b for b in b_floats))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

def retrieve_context(query: str, top_k: int = 4, min_similarity: float = 0.1) -> list[dict]:
    """
    Computes vector similarity against stored document chunks and returns top_k matches.
    Only returns chunks with similarity above min_similarity.
    """
    db = _load_db()
    if not db:
        return []

    emb_fn = get_embedding_function()
    query_vector = emb_fn([query])[0]

    scored_items = []
    for item in db:
        sim_val = cosine_similarity(query_vector, item["embedding"])
        dist_val = 1.0 - sim_val
        
        # Clean metadata dictionary
        clean_meta = {}
        if item.get("metadata"):
            for k, v in item["metadata"].items():
                if isinstance(v, (int, float, str, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)

        if sim_val >= min_similarity:
            scored_items.append({
                "content": str(item["content"]),
                "metadata": clean_meta,
                "distance": dist_val,
                "similarity": sim_val
            })

    # Sort descending by similarity (highest match first)
    scored_items.sort(key=lambda x: x["similarity"], reverse=True)
    return scored_items[:top_k]

