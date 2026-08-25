from chromadb.api.types import EmbeddingFunction
from chromadb.utils import embedding_functions

_embedding_fn = None

def get_embedding_function() -> EmbeddingFunction:
    global _embedding_fn
    if _embedding_fn is None:
        # Using DefaultEmbeddingFunction (which defaults to all-MiniLM-L6-v2) 
        # to bypass the PyTorch c10.dll/fbgemm.dll missing dependencies issue on Windows
        _embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    return _embedding_fn

#This default function uses a smaller, lightweight model (all-MiniLM-L6-v2) 
# that runs perfectly on Windows without those nasty dependency crashes.