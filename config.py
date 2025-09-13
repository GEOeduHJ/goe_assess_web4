import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration class."""
    
    # API Keys
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    HF_TOKEN: Optional[str] = os.getenv("HF_TOKEN")
    
    # Application Settings
    APP_TITLE: str = os.getenv("APP_TITLE", "지리과 자동 채점 플랫폼")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nlpai-lab/KURE-v1")
    FAISS_INDEX_TYPE: str = os.getenv("FAISS_INDEX_TYPE", "IndexFlatIP")
    
    # Processing Settings
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: int = int(os.getenv("RETRY_DELAY", "2"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    TOP_K_RETRIEVAL: int = int(os.getenv("TOP_K_RETRIEVAL", "3"))
    
    # RAG Optimization Settings
    MAX_DOCS_PER_STUDENT: int = int(os.getenv("MAX_DOCS_PER_STUDENT", "5"))
    CHUNKS_PER_DOC_LIMIT: int = int(os.getenv("CHUNKS_PER_DOC_LIMIT", "20"))
    RAG_PROCESSING_TIMEOUT: int = int(os.getenv("RAG_PROCESSING_TIMEOUT", "60"))
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "8"))
    ENABLE_INCREMENTAL_CLEANUP: bool = os.getenv("ENABLE_INCREMENTAL_CLEANUP", "true").lower() == "true"
    
    # Performance Optimization Settings
    API_CACHE_TTL_SECONDS: int = int(os.getenv("API_CACHE_TTL_SECONDS", "300"))
    API_CACHE_MAX_SIZE: int = int(os.getenv("API_CACHE_MAX_SIZE", "100"))
    
    # Batch Processing Settings
    BATCH_PROCESSING_SIZE: int = int(os.getenv("BATCH_PROCESSING_SIZE", "10"))
    
    @classmethod
    def validate_api_keys(cls) -> dict:
        """
        Validate that required API keys are configured.
        
        Returns:
            dict: Validation results with missing keys
        """
        missing_keys = []
        
        if not cls.GOOGLE_API_KEY:
            missing_keys.append("GOOGLE_API_KEY")
        
        if not cls.GROQ_API_KEY:
            missing_keys.append("GROQ_API_KEY")
        
        return {
            "valid": len(missing_keys) == 0,
            "missing_keys": missing_keys
        }
    
    @classmethod
    def get_max_file_size_bytes(cls) -> int:
        """
        Get maximum file size in bytes.
        
        Returns:
            int: Maximum file size in bytes
        """
        return cls.MAX_FILE_SIZE_MB * 1024 * 1024


# Create a global config instance
config = Config()