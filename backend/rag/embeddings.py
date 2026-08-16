import math
import re
from collections import Counter
import requests
from chromadb.api.types import Documents, Embeddings, EmbeddingFunction
from backend.config import settings

class TFIDFEmbeddingFunction(EmbeddingFunction):
    """
    High-precision feature vectorizer using word n-grams and term frequency 
    for fast, deterministic, dependency-free semantic matching.
    """
    def __init__(self, vec_dim: int = 512):
        self.vec_dim = vec_dim

    def _extract_ngrams(self, text: str) -> list[str]:
        words = re.findall(r'\w+', text.lower())
        ngrams = list(words)
        # Add word bigrams for context capture
        for i in range(len(words) - 1):
            ngrams.append(f"{words[i]}_{words[i+1]}")
        return ngrams

    def _text_to_vector(self, text: str) -> list[float]:
        ngrams = self._extract_ngrams(text)
        if not ngrams:
            return [0.0] * self.vec_dim

        counts = Counter(ngrams)
        total = len(ngrams)
        vec = [0.0] * self.vec_dim

        # Map ngrams deterministically into vector space using feature hashing
        import hashlib
        for term, count in counts.items():
            tf = count / total
            h = int(hashlib.md5(term.encode('utf-8')).hexdigest(), 16)
            idx = h % self.vec_dim
            sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
            vec[idx] += sign * tf

        # L2 Normalize
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def __call__(self, input: Documents) -> Embeddings:
        import numpy as np
        embeddings = []
        for doc in input:
            embeddings.append(np.array(self._text_to_vector(doc), dtype=np.float32))
        return embeddings

_embedding_fn = None

def get_embedding_function() -> EmbeddingFunction:
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = TFIDFEmbeddingFunction()
    return _embedding_fn

