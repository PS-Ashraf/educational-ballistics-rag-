import os
import sys
import shutil
import requests
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config import settings
from backend.safety import is_query_safe, get_safety_refusal, get_system_prompt
from backend.rag.ingestion import (
    ingest_document, 
    sync_knowledge_base, 
    list_documents, 
    get_kb_collection, 
    get_document_chunks, 
    delete_document
)
from backend.rag.retrieval import retrieve_context

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Auto-scan and auto-ingest documents in knowledge_base on server startup."""
    try:
        sync_result = sync_knowledge_base()
        collection = get_kb_collection()
        print("=" * 60)
        print("   RAG KNOWLEDGE BASE AUTOMATIC STARTUP SYNC")
        print("=" * 60)
        print(f"[SYNC] Files Found:           {sync_result.get('total_files_found', 0)}")
        print(f"[SYNC] Already Indexed:       {sync_result.get('already_indexed', 0)}")
        print(f"[SYNC] Newly Ingested:        {sync_result.get('newly_ingested', 0)}")
        print(f"[SYNC] New Chunks Created:    {sync_result.get('new_chunks_added', 0)}")
        print(f"[SYNC] Total Database Chunks: {collection.count()}")
        print("=" * 60)
    except Exception as e:
        print(f"[SYNC NOTICE] Startup auto-ingestion notice: {e}")
    yield


app = FastAPI(title="Educational Ballistics Knowledge Chatbot API", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory history cache
history_db: List[Dict[str, str]] = []

class ChatRequest(BaseModel):
    message: str
    top_k: int = 4

class ChatResponse(BaseModel):
    response: str
    safe: bool
    context: List[Dict[str, Any]]
    sources: List[str]

@app.get("/api/health")
def health_check():
    health: Dict[str, Any] = {
        "status": "healthy",
        "ollama": "Disconnected",
        "ollama_model": settings.OLLAMA_MODEL,
        "vector_db": "Ready"
    }
    
    # Check Ollama connection
    try:
        res = requests.get(f"{settings.OLLAMA_HOST}/api/tags", timeout=3)
        if res.status_code == 200:
            health["ollama"] = "Connected"
    except Exception:
        pass
        
    # Check Vector DB connection
    try:
        collection = get_kb_collection()
        health["vector_db_count"] = collection.count()
        health["vector_db"] = "Ready"
    except Exception as e:
        health["vector_db"] = "Error"
        health["vector_db_error"] = str(e)
        health["status"] = "degraded"
        
    return health

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    user_msg = payload.message.strip()
    
    # 1. Safety check
    if not is_query_safe(user_msg):
        return ChatResponse(
            response=get_safety_refusal(),
            safe=False,
            context=[],
            sources=[]
        )

    # 2. Retrieve relevant context
    context_chunks = retrieve_context(user_msg, top_k=payload.top_k)
    
    if not context_chunks:
        return ChatResponse(
            response="I do not have any data or documents in the knowledge base related to your question.",
            safe=True,
            context=[],
            sources=[]
        )

    context_text = "\n\n".join([f"Source: {chunk['metadata'].get('source')}\nContent: {chunk['content']}" for chunk in context_chunks])
    sources = list(set([chunk["metadata"].get("source") for chunk in context_chunks if chunk.get("metadata")]))
    
    # 3. Create prompt
    system_prompt = get_system_prompt(context_text)
    
    # Build complete chat log from history and prepend system prompt
    messages = [{"role": "system", "content": system_prompt}]
    
    # Append past conversational turns if any
    for chat in history_db[-10:]:
        messages.append({"role": chat["role"], "content": chat["content"]})
        
    messages.append({"role": "user", "content": user_msg})
    
    # 4. Request answer from Ollama
    try:
        res = requests.post(
            f"{settings.OLLAMA_HOST}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": messages,
                "stream": False
            },
            timeout=60
        )
        if res.status_code == 200:
            bot_reply = res.json()["message"]["content"]
            # Save turns to memory
            history_db.append({"role": "user", "content": user_msg})
            history_db.append({"role": "assistant", "content": bot_reply})
            
            return ChatResponse(
                response=bot_reply,
                safe=True,
                context=context_chunks,
                sources=sources
            )
        else:
            fallback_msg = (
                f"**Ollama Response Notice (HTTP {res.status_code})**\n\n"
                f"Model `{settings.OLLAMA_MODEL}` was queried. Below is the retrieved knowledge base information:\n\n"
                + (context_text if context_text else "No context retrieved.")
            )
            return ChatResponse(
                response=fallback_msg,
                safe=True,
                context=context_chunks,
                sources=sources
            )
    except Exception as e:
        fallback_msg = (
            f"### Knowledge Base Summary\n\n"
            f"*(Note: Ollama LLM endpoint {settings.OLLAMA_HOST} is offline or starting up. Showing direct retrieved context below.)*\n\n"
            + (context_text if context_text else "No knowledge base context retrieved.")
        )
        return ChatResponse(
            response=fallback_msg,
            safe=True,
            context=context_chunks,
            sources=sources
        )


@app.post("/api/documents/upload")
def upload_document(file: UploadFile = File(...)):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = file.filename or "uploaded_file"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Trigger immediate ingestion into ChromaDB upon file upload
        ingest_result = ingest_document(file_path)
        if ingest_result.get("status") == "error":
            raise HTTPException(status_code=400, detail=ingest_result.get("message"))
            
        return {
            "status": "success",
            "filename": filename,
            "path": file_path,
            "chunks_count": ingest_result.get("chunks_count", 0),
            "message": f"Successfully uploaded and instantly ingested '{filename}' into vector database."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload and ingest document: {str(e)}")

@app.post("/api/documents/ingest")
def ingest_document_endpoint(filename: str = Form(...)):
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Uploaded file not found")
        
    result = ingest_document(file_path)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.post("/api/documents/sync")
def sync_documents_endpoint():
    res = sync_knowledge_base()
    return res

@app.get("/api/documents")
def get_documents():
    return list_documents()


@app.get("/api/documents/{filename}/preview")
def preview_document(filename: str):
    chunks = get_document_chunks(filename)
    if not chunks:
        raise HTTPException(status_code=404, detail="Document chunks not found")
    return {"filename": filename, "chunks": chunks, "total_chunks": len(chunks)}

@app.delete("/api/documents/{filename}")
def remove_document(filename: str):
    res = delete_document(filename)
    return res

@app.delete("/api/chat/history")
def clear_history():
    global history_db
    history_db = []
    return {"status": "success", "message": "Conversation history cleared"}

# Serve Frontend static UI files
frontend_dir = os.path.abspath(os.path.join(PROJECT_ROOT, "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
