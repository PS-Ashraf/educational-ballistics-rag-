# 🎯 Project Overview & Mentor Q&A Guide: Educational Ballistics RAG Assistant

---

## 📌 Executive Summary
This project is an **Educational Ballistics Retrieval-Augmented Generation (RAG) System** with strict safety guardrails. It enables users to ask technical, historical, and physical questions regarding ballistics while ensuring that **harmful DIY weapon manufacturing or conversion instructions are strictly blocked**. 

The system uses **lightweight, high-precision sentence-level vector embeddings** (TF-IDF feature hashing + Cosine Similarity) backed by a local vector store and **FastAPI** web backend.

---

## 🏗️ Architecture & Component Flow

```
+------------------+      +-------------------------------+
|    User Query    | ---> |  FastAPI Endpoint /api/chat   |
+------------------+      +-------------------------------+
                                          |
                                 [Safety Check]
                                          |
                   +----------------------+----------------------+
                   |                                             |
             (Unsafe Query)                                (Safe Query)
                   |                                             |
                   v                                             v
     +---------------------------+                +----------------------------+
     |   Return Safety Refusal   |                | TFIDF Embedding Generation |
     +---------------------------+                +----------------------------+
                                                                 |
                                                                 v
                                                  +----------------------------+
                                                  | Cosine Similarity DB Search|
                                                  +----------------------------+
                                                                 |
                                                        [Matches >= 0.1?]
                                                                 |
                                          +----------------------+----------------------+
                                          |                                             |
                                     (No Matches)                                 (Matches Found)
                                          |                                             |
                                          v                                             v
                           +------------------------------+              +------------------------------+
                           | Return Direct "No Data" Msg  |              | Send Context + Prompt to LLM |
                           +------------------------------+              +------------------------------+
```

---

## 🚀 How to Explain This Project to Your Mentor (30-Second Elevator Pitch)

> *"I built a lightweight, privacy-focused RAG system for educational ballistics science. It ingests PDF and text documents into a vector database using a custom sentence-level vectorizer. When a user asks a question, it runs a two-tier safety filter, retrieves high-relevance chunks using cosine similarity, and formats a grounded system prompt for the LLM. If the user asks something outside the knowledge base or unsafe, it gracefully refuses or states that data is unavailable rather than hallucinating."*

---

## ❓ Top 10 Mentor Questions & Winning Technical Answers

### 1. RAG & Vector Search Questions

#### Q1: "Why did you choose small sentence-level chunking (~350 chars) instead of large paragraph chunking (~1000 chars)?"
- **Answer**: *"Large paragraph chunks often dilute semantic vector embeddings with multiple unrelated topics. By using sentence-level chunking (~350 characters with a 50-character overlap), each chunk represents a single, highly specific fact. This drastically improves retrieval precision and prevents the model from hallucinating or fetching irrelevant text."*

#### Q2: "How does your embedding function work without relying on heavy external APIs?"
- **Answer**: *"We implemented `TFIDFEmbeddingFunction` using deterministic n-gram extraction (unigrams + bigrams) and feature hashing into a fixed 512-dimensional vector space, followed by L2 normalization. This makes vector embedding super fast, zero-dependency, and 100% local."*

#### Q3: "How do you handle queries when there is NO relevant document in your database?"
- **Answer**: *"We introduced a strict similarity threshold (`min_similarity = 0.1`). If no retrieved document chunk meets this threshold, the API immediately returns `I do not have any data or documents in the knowledge base related to your question.` without making unnecessary LLM calls or providing generic answers."*

#### Q4: "What distance/similarity metric are you using for vector search?"
- **Answer**: *"We compute **Cosine Similarity** between the query vector and document chunk vectors. Cosine similarity evaluates the angle between vectors rather than magnitude, which works exceptionally well for normalized text embeddings."*

---

### 2. Safety & System Architecture Questions

#### Q5: "How do you ensure users cannot abuse the chatbot to request DIY firearm manufacturing guides?"
- **Answer**: *"We implement a **Two-Layer Guardrail System**:"*
  1. **Regex/Rule-based Pre-Filter (`backend/safety.py`)**: Intercepts illegal or dangerous intent (e.g., 3D printing lower receivers, full-auto conversions, DIY explosives) before querying the database.
  2. **System Prompt Constraint**: The LLM system prompt explicitly instructs the model: *"Under no circumstances should you provide blueprints, design files, or step-by-step instructions for building or modifying weapons."*

#### Q6: "What happens if the local Ollama LLM server crashes or goes offline?"
- **Answer**: *"The system has a resilient fallback mechanism. If the backend fails to connect to Ollama, it catches the exception and returns the exact retrieved knowledge base context snippets directly to the user so they still get the authoritative data."*

---

### 3. Database Management & Ingestion Questions

#### Q7: "How do you manage database ingestion and cleaning?"
- **Answer**: *"We built two dedicated CLI management scripts:"*
  - **`run_ingestion.py`**: Automatically scans the `knowledge_base/documents` folder for `.pdf`, `.txt`, and `.md` files, cleans whitespace, generates sentence chunks, and saves them to the database.
  - **`manage_db.py`**: An interactive CLI utility that lets us inspect stored chunks, delete specific document vectors by filename, or execute a full database reset.

#### Q8: "How does ingestion avoid duplicate entries when re-uploading an edited file?"
- **Answer**: *"During ingestion, the system checks existing chunk metadata for the incoming filename and removes old entries matching that source filename before writing the new chunks."*

---

### 4. API & Backend Questions

#### Q9: "How is the backend API structured?"
- **Answer**: *"It is built using **FastAPI** with Pydantic schema validation (`ChatRequest`, `ChatResponse`), CORS middleware, and an automatic lifespan trigger that auto-ingests initial documents on startup if the vector database is empty."*

#### Q10: "How do you maintain conversation history?"
- **Answer**: *"The backend maintains an in-memory chat memory buffer (`history_db`). When querying the LLM, the last 10 conversational turns are appended to the system prompt so the LLM retains context throughout the user session."*

---

## 📋 Project Directory Quick Reference

| Path | Description |
| :--- | :--- |
| **`backend/main.py`** | FastAPI server routes (`/api/chat`, `/api/health`, `/api/documents`) |
| **`backend/safety.py`** | Safety guardrails & system prompt definition |
| **`backend/rag/embeddings.py`** | TF-IDF deterministic 512-dim vectorizer |
| **`backend/rag/ingestion.py`** | Sentence-level text chunking & vector persistence |
| **`backend/rag/retrieval.py`** | Cosine similarity vector search & threshold filtering |
| **`run_ingestion.py`** | Manual ingestion CLI script |
| **`manage_db.py`** | Database inspection, deletion, and reset CLI script |
