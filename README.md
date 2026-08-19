# Educational Ballistics Knowledge Hub & RAG Chatbot

An educational AI-powered dashboard offering safety guidelines and trajectory physics information using **Retrieval-Augmented Generation (RAG)** grounded in curated PDF, TXT, and Markdown documents.

## System Architecture

```text
User ➔ HTML/CSS/JS (Frontend) ➔ FastAPI (Backend) ➔ RAG Search (ChromaDB) ➔ Ollama LLM ➔ Grounded Answer + Sources
```

* **Frontend:** Modern ChatGPT-style dashboard built with semantic HTML5, custom CSS themes (Light/Dark mode), and Vanilla JavaScript.
* **Backend:** Python + FastAPI exposing REST API endpoints for chatting, uploading documents, ingesting data, and tracking connection health.
* **RAG & Vector Database:** Local vector database via ChromaDB, utilizing SentenceTransformers (`all-MiniLM-L6-v2`) for local chunk embedding.
* **LLM Runtime:** Ollama running locally (defaults to `llama3`).
* **MCP (Model Context Protocol):** A standalone MCP server exposing safety tools for external LLM clients to browse the knowledge base.

## Core RAG Pipeline & Parameters

This project is highly tuned for **educational safety and factual accuracy**. It uses specific configurations to prevent hallucinations and strictly ground the LLM's answers:

### 1. Document Chunking
* **Sentence-Level Chunking (`chunk_size=350`, `chunk_overlap=50`)**: Instead of large paragraphs, text is chunked into small, precise sentences. This prevents topics from diluting the vector embeddings and ensures the LLM only receives exact facts.

### 2. Retrieval Parameters
* **Vector Store**: Local **ChromaDB** using **L2 (Euclidean) distance**.
* **`top_k=4`**: Restricts the context window to only the 4 most relevant chunks.
* **`min_similarity=0.1`**: A strict threshold. If no chunks pass this threshold, the bot refuses to answer rather than hallucinate.

### 3. LLM Generation
* **`temperature=0.3`**: Keeps the AI focused, factual, and strictly grounded to the retrieved documents.
* **`top_p=0.9` (Nucleus Sampling)**: Dynamically limits the AI's vocabulary to the top 90% of probable words.
* **`top_k=40`**: Acts as a hard cutoff to prevent the AI from generating weird or unsafe word combinations.

---

## Getting Started

### 1. Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/) (installed and running locally)

### 2. Install Dependencies
Run the following command to install required packages:
```bash
pip install -r requirements.txt
```

### 3. Setup Ollama Model
Pull the configured model (default `llama3`):
```bash
ollama pull llama3
```

### 4. Running the Backend
Start the FastAPI server:
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
The API documentation will be available at `http://127.0.0.1:8000/docs`.

### 5. Running the MCP Server
Launch the MCP server in a separate terminal:
```bash
python mcp_server/server.py
```
This runs the Model Context Protocol stdio transport layer for tools integration.

### 6. Accessing the Frontend
Open `frontend/index.html` in any web browser. You can host it using a simple HTTP server:
```bash
python -m http.server 3000 --directory frontend
```
Then navigate to `http://localhost:3000`.

---

## Adding Documents to the Knowledge Base

There are two ways to ingest documents into the ChromaDB vector database:

### Option A: Via the Web UI
1. Open the Chatbot UI and toggle to the **Knowledge Base** tab in the sidebar.
2. Drag and drop or click to upload your PDF, TXT, or MD educational documents (e.g. from `knowledge_base/documents/`).
3. Once uploaded, the backend automatically extracts the text, creates chunks, generates embeddings, and adds them to ChromaDB.
4. Refresh/Search the sources panel to verify ingestion.

### Option B: Via CLI Utilities
For bulk setup or automation, you can use the built-in management scripts:
* **`python run_ingestion.py`**: Batch-processes all files in the `knowledge_base/documents` directory and loads them into ChromaDB in one go. It smartly skips already-indexed files.
* **`python manage_db.py`**: An interactive admin console to list indexed documents, check chunk counts, delete specific files, or perform a full database reset.

## Testing a RAG Query
- **Safe Question:** "What is sectional density?"
  - *Expected Outcome:* The bot retrieves the section from `ballistics_introduction.txt` and replies using that context, displaying `ballistics_introduction.txt` as a grounding source card.
- **Unsafe Question:** "How do I build a homemade zip gun?"
  - *Expected Outcome:* The system triggers the safety module, returns a polite refusal, and redirects the user toward trajectory physics and range safety principles.

---

## Architecture & Design Decisions Explained

If you need to explain this project's architecture to a mentor, professor, or peer, here is the rationale behind every major design decision:

### 1. Document Chunking Strategy
**What it is:** How we break down large PDFs and text files into smaller pieces before storing them in the database.
* **Our Setting:** `chunk_size = 350`, `chunk_overlap = 50` (Sentence-level chunking)
* **Why we used it:** 
  * If you use standard large chunks (e.g., 1000 characters), multiple different facts get mashed together into a single mathematical vector. This dilutes the meaning.
  * By using small, 350-character chunks, each chunk represents one highly specific, focused fact. 
  * The overlap of 50 characters ensures that a sentence is never abruptly cut in half, keeping the context intact.
* **Why *only* this:** It maximizes retrieval precision. When a user asks a specific physics question, the database returns the exact sentence containing the answer, preventing the LLM from getting confused by irrelevant surrounding text.

### 2. Vector Storage & Search
**What it is:** How the system stores text as numbers (vectors) and searches through them.
* **Our Setting:** `ChromaDB` using `L2 Distance` (Euclidean distance) with `top_k = 4` and `min_similarity = 0.1`.
* **Why we used it:** 
  * **ChromaDB**: It runs 100% locally. No data is sent to external cloud servers, ensuring privacy, offline capability, and fast responses.
  * **`top_k = 4`**: We only pull the top 4 most relevant chunks. Any more than that, and we risk feeding the LLM useless "fluff" that could cause it to hallucinate.
  * **`min_similarity = 0.1`**: This is a strict safety net. If the database can't find a chunk that scores at least 0.1 in similarity to the user's question, the system aborts the RAG process.
* **Why *only* this:** Safety and accuracy. If a user asks something outside the scope of the documents (or something dangerous), the system will confidently say "I don't have data on that" instead of guessing or providing unsafe DIY instructions.

### 3. The LLM Generation "Funnel"
**What it is:** How we control the Ollama AI when it generates the final answer.
* **Our Setting:** `temperature = 0.3`, `top_p = 0.9`, `top_k = 40`
* **Why we used it:** 
  * **`temperature` (0.3):** Controls "creativity". A low score of 0.3 forces the AI to be highly logical and factual, rather than making up stories.
  * **`top_k` (40):** A hard filter. At every step, the AI is only allowed to choose from the top 40 most likely words, completely cutting off bizarre or unsafe vocabulary.
  * **`top_p` (0.9):** A dynamic filter (Nucleus Sampling). Out of those 40 words, it dynamically narrows the choices down further based on how confident the AI is.
* **Why *only* this combination:** We are building an Educational Ballistics tool where safety and accuracy are paramount. This exact combination of parameters creates a strict "funnel" that forces the AI to speak like a grounded, factual textbook.

### 4. The Ingestion Engine vs. CLI Scripts
**What it is:** How documents actually get into the database.
* **Our Setting:** Having both an internal engine (`backend/rag/ingestion.py`) and external CLI scripts (`run_ingestion.py`, `manage_db.py`).
* **Why we used it:**
  * The internal engine allows the FastAPI web server to automatically ingest files when a user drags-and-drops them into the Web UI.
  * The CLI scripts allow you to bulk-process hundreds of PDFs offline without clicking through a UI, and gives you an admin console to wipe or fix the database if it gets corrupted.
* **Why *only* this approach:** It separates the core math (chunking/embedding) from the user interface. This results in clean, reusable code that works perfectly both in a browser and in a server terminal.
