import os
import sys

# Ensure backend modules are importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp.server.fastmcp import FastMCP
from backend.rag.retrieval import retrieve_context
from backend.rag.ingestion import list_documents

mcp = FastMCP("Ballistics KB Server")

@mcp.tool()
def search_knowledge_base(query: str) -> str:
    """
    Search the educational ballistics knowledge base for matches to a query.
    Returns matched paragraphs/chunks.
    """
    results = retrieve_context(query, top_k=3)
    if not results:
        return "No relevant information found in the knowledge base."
    
    out = []
    for r in results:
        src = r["metadata"].get("source", "Unknown")
        out.append(f"[{src}]: {r['content']}")
    return "\n\n".join(out)

@mcp.tool()
def retrieve_document_context(query: str, top_k: int = 4) -> str:
    """
    Retrieve up to top_k document chunks related to the query for RAG grounding.
    """
    results = retrieve_context(query, top_k=top_k)
    if not results:
        return "No relevant context found."
    
    out = []
    for idx, r in enumerate(results):
        src = r["metadata"].get("source", "Unknown")
        out.append(f"Chunk {idx+1} (Source: {src}):\n{r['content']}")
    return "\n\n---\n\n".join(out)

@mcp.tool()
def list_available_sources() -> str:
    """
    List all documents currently ingested and indexed in the knowledge base.
    """
    docs = list_documents()
    if not docs:
        return "No documents uploaded or ingested yet."
    
    out = []
    for doc in docs:
        out.append(f"- {doc['filename']} ({doc['chunks']} chunks, located at: {doc['path']})")
    return "\n".join(out)

@mcp.tool()
def get_source_metadata(source_id: str) -> str:
    """
    Retrieve metadata for a specific document source.
    """
    docs = list_documents()
    for doc in docs:
        if doc["filename"] == source_id:
            return f"Source: {doc['filename']}\nPath: {doc['path']}\nChunks: {doc['chunks']}"
    return f"Source '{source_id}' not found."

if __name__ == "__main__":
    mcp.run()



#[ AI Client ]  ---> Sends JSON-RPC: call "search_knowledge_base(query='bullet drag')"
      
#[ MCP Server ] ---> Runs search_knowledge_base() -> Calls retrieve_context()
      
#[ ChromaDB ]   ---> Searches vector store and returns matching document chunks
      
#[ MCP Server ] ---> Formats text and responds to AI
      
#[ AI Client ]  ---> Reads ground-truth document chunks and answers user
