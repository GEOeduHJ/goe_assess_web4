import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Streamlit secrets support
try:
    import streamlit as st
    _use_streamlit_secrets = hasattr(st, 'secrets')
except ImportError:
    _use_streamlit_secrets = False


def get_config_value(key: str, default=None):
    """Get configuration value from Streamlit secrets or environment variables."""
    if _use_streamlit_secrets:
        try:
            # Try to get from streamlit secrets first
            keys = key.lower().split('_')
            if len(keys) >= 2:
                section = keys[0] if keys[0] in ['api', 'application', 'processing'] else 'api'
                secret_key = '_'.join(keys[1:]) if section == keys[0] else key.lower()
                return st.secrets[section].get(secret_key, os.getenv(key, default))
            else:
                # Fallback for simple keys
                return st.secrets.get(key.lower(), os.getenv(key, default))
        except (KeyError, AttributeError):
            pass
    
    # Fallback to environment variables
    return os.getenv(key, default)


class Config:
    """Application configuration class."""
    
    # API Keys
    GOOGLE_API_KEY: Optional[str] = get_config_value("GOOGLE_API_KEY")
    GROQ_API_KEY: Optional[str] = get_config_value("GROQ_API_KEY")
    HF_TOKEN: Optional[str] = get_config_value("HF_TOKEN")
    
    # Application Settings
    APP_TITLE: str = get_config_value("APP_TITLE", "지리과 자동 채점 플랫폼")
    MAX_FILE_SIZE_MB: int = int(get_config_value("MAX_FILE_SIZE_MB", "50"))
    EMBEDDING_MODEL: str = get_config_value("EMBEDDING_MODEL", "nlpai-lab/KURE-v1")
    FAISS_INDEX_TYPE: str = get_config_value("FAISS_INDEX_TYPE", "IndexFlatIP")
    
    # Processing Settings
    MAX_RETRIES: int = int(get_config_value("MAX_RETRIES", "3"))
    RETRY_DELAY: int = int(get_config_value("RETRY_DELAY", "2"))
    CHUNK_SIZE: int = int(get_config_value("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(get_config_value("CHUNK_OVERLAP", "50"))
    TOP_K_RETRIEVAL: int = int(get_config_value("TOP_K_RETRIEVAL", "3"))
    
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