import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")
    EMBEDDING_MODEL_TYPE: str = os.getenv("EMBEDDING_MODEL_TYPE", "sentence-transformer")
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
    VECTOR_DB_DIR: str = os.path.abspath(os.getenv("VECTOR_DB_DIR", "./vector_store"))
    UPLOAD_DIR: str = os.path.abspath(os.getenv("UPLOAD_DIR", "./knowledge_base/documents"))
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    MCP_PORT: int = int(os.getenv("MCP_PORT", "8001"))

settings = Settings()

# Ensure directories exist
os.makedirs(settings.VECTOR_DB_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
