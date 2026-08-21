import math
from typing import Any, Sequence
from backend.rag.ingestion import get_kb_collection


def retrieve_context(query: str, top_k: int = 4, min_similarity: float = 0.5) -> list[dict]:
    """
    Computes vector similarity against stored document chunks and returns top_k matches.
    Only returns chunks with similarity above min_similarity.
    """
    collection = get_kb_collection()
    
    if collection.count() == 0:
        return []

    # Chroma uses L2 distance by default.
    res = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
    
    scored_items = []
    
    if not res.get("documents") or not res["documents"][0]:
        return []
        
    for i in range(len(res["documents"][0])):
        dist_val = res["distances"][0][i] if res.get("distances") else 0.0
        
        # Pseudo similarity map from L2 distance
        sim_val = 1.0 / (1.0 + dist_val)
        
        if sim_val >= min_similarity:
            doc = res["documents"][0][i]
            meta = res["metadatas"][0][i] if res.get("metadatas") else {}
            
            clean_meta = {}
            for k, v in meta.items():
                if isinstance(v, (int, float, str, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
            
            scored_items.append({
                "content": doc,
                "metadata": clean_meta,
                "distance": dist_val,
                "similarity": sim_val
            })
            
    # Sort descending by similarity (highest match first)
    scored_items.sort(key=lambda x: x["similarity"], reverse=True)
    return scored_items

