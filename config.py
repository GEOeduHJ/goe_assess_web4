import os
from typing import Optional
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# Streamlit secrets 지원
try:
    import streamlit as st
    _use_streamlit_secrets = hasattr(st, 'secrets')
except ImportError:
    _use_streamlit_secrets = False


def get_config_value(key: str, default=None):
    """Streamlit secrets 또는 환경 변수에서 설정 값을 가져옵니다."""
    if _use_streamlit_secrets:
        try:
            # 먼저 streamlit secrets에서 가져오기 시도
            keys = key.lower().split('_')
            if len(keys) >= 2:
                section = keys[0] if keys[0] in ['api', 'application', 'processing'] else 'api'
                secret_key = '_'.join(keys[1:]) if section == keys[0] else key.lower()
                return st.secrets[section].get(secret_key, os.getenv(key, default))
            else:
                # 단순 키의 대체 방법
                return st.secrets.get(key.lower(), os.getenv(key, default))
        except (KeyError, AttributeError):
            pass
    
    # 환경 변수로 대체
    return os.getenv(key, default)


class Config:
    """애플리케이션 설정 클래스"""
    
    # API 키
    GOOGLE_API_KEY: Optional[str] = get_config_value("GOOGLE_API_KEY")
    GROQ_API_KEY: Optional[str] = get_config_value("GROQ_API_KEY")
    HF_TOKEN: Optional[str] = get_config_value("HF_TOKEN")
    
    # 애플리케이션 설정
    APP_TITLE: str = get_config_value("APP_TITLE", "지리과 자동 채점 플랫폼")
    MAX_FILE_SIZE_MB: int = int(get_config_value("MAX_FILE_SIZE_MB", "50"))
    EMBEDDING_MODEL: str = get_config_value("EMBEDDING_MODEL", "nlpai-lab/KURE-v1")
    FAISS_INDEX_TYPE: str = get_config_value("FAISS_INDEX_TYPE", "IndexFlatIP")
    
    # 처리 설정
    MAX_RETRIES: int = int(get_config_value("MAX_RETRIES", "3"))
    RETRY_DELAY: int = int(get_config_value("RETRY_DELAY", "2"))
    CHUNK_SIZE: int = int(get_config_value("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(get_config_value("CHUNK_OVERLAP", "50"))
    TOP_K_RETRIEVAL: int = int(get_config_value("TOP_K_RETRIEVAL", "3"))
    
    # RAG 최적화 설정
    MAX_DOCS_PER_STUDENT: int = int(os.getenv("MAX_DOCS_PER_STUDENT", "5"))
    CHUNKS_PER_DOC_LIMIT: int = int(os.getenv("CHUNKS_PER_DOC_LIMIT", "20"))
    RAG_PROCESSING_TIMEOUT: int = int(os.getenv("RAG_PROCESSING_TIMEOUT", "60"))
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "8"))
    ENABLE_INCREMENTAL_CLEANUP: bool = os.getenv("ENABLE_INCREMENTAL_CLEANUP", "true").lower() == "true"
    
    # 성능 최적화 설정
    API_CACHE_TTL_SECONDS: int = int(os.getenv("API_CACHE_TTL_SECONDS", "300"))
    API_CACHE_MAX_SIZE: int = int(os.getenv("API_CACHE_MAX_SIZE", "100"))
    
    # 배치 처리 설정
    BATCH_PROCESSING_SIZE: int = int(os.getenv("BATCH_PROCESSING_SIZE", "10"))
    
    @classmethod
    def validate_api_keys(cls) -> dict:
        """
        필요한 API 키가 설정되어 있는지 검증합니다.
        
        Returns:
            dict: 누락된 키가 포함된 검증 결과
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
        최대 파일 크기를 바이트 단위로 가져옵니다.
        
        Returns:
            int: 바이트 단위의 최대 파일 크기
        """
        return cls.MAX_FILE_SIZE_MB * 1024 * 1024


# 전역 config 인스턴스 생성
config = Config()