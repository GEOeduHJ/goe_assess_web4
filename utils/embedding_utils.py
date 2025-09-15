"""
지리 자동 채점 시스템을 위한 임베딩 유틸리티

이 모듈은 텍스트 전처리, 임베딩 연산, 벡터 유사도 계산을 위한
유틸리티 함수들을 제공합니다.
"""

import re
from typing import List, Dict, Optional
import numpy as np
from sentence_transformers import SentenceTransformer


def preprocess_text(text: str) -> str:
    """
    더 나은 임베딩 품질을 위한 텍스트 전처리
    
    Args:
        text: 전처리할 원본 텍스트
        
    Returns:
        정리되고 정규화된 텍스트
    """
    if not text:
        return ""
    
    # 여분의 공백 제거 및 정규화
    text = re.sub(r'\s+', ' ', text.strip())
    
    # 특수 문자 제거하되 한국어, 영어, 숫자, 기본 구두점은 유지
    text = re.sub(r'[^\w\s가-힣.,!?()-]', ' ', text)
    
    # 연속된 구두점 제거
    text = re.sub(r'[.,!?]{2,}', '.', text)
    
    return text.strip()


def calculate_text_similarity(text1: str, text2: str, model: SentenceTransformer) -> float:
    """
    임베딩을 사용하여 두 텍스트 간의 의미적 유사도를 계산합니다.
    
    Args:
        text1: 첫 번째 텍스트
        text2: 두 번째 텍스트
        model: 로드된 SentenceTransformer 모델
        
    Returns:
        0과 1 사이의 유사도 점수
    """
    try:
        # 텍스트 전처리
        text1 = preprocess_text(text1)
        text2 = preprocess_text(text2)
        
        if not text1 or not text2:
            return 0.0
        
        # 임베딩 생성
        embeddings = model.encode([text1, text2], convert_to_numpy=True)
        
        # 코사인 유사도 계산
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        
        # 유사도가 0과 1 사이인지 확인
        return max(0.0, min(1.0, float(similarity)))
        
    except Exception:
        return 0.0


def validate_embedding_dimension(embeddings: np.ndarray, expected_dim: int) -> bool:
    """
    임베딩이 예상 차원을 가지는지 검증합니다.
    
    Args:
        embeddings: 임베딩의 Numpy 배열
        expected_dim: 예상 임베딩 차원
        
    Returns:
        차원이 일치하면 True, 아니면 False
    """
    if embeddings is None or embeddings.size == 0:
        return False
    
    return embeddings.shape[-1] == expected_dim


def normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
    """
    더 나은 유사도 계산을 위해 임베딩을 단위 길이로 정규화합니다.
    
    Args:
        embeddings: 임베딩의 Numpy 배열
        
    Returns:
        정규화된 임베딩
    """
    if embeddings is None or embeddings.size == 0:
        return embeddings
    
    # Calculate L2 norm along the last dimension
    norms = np.linalg.norm(embeddings, axis=-1, keepdims=True)
    
    # Avoid division by zero
    norms = np.where(norms == 0, 1, norms)
    
    return embeddings / norms


def chunk_text_by_sentences(text: str, max_chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into chunks based on sentence boundaries with overlap.
    
    Args:
        text: Text to chunk
        max_chunk_size: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text or len(text.strip()) == 0:
        return []
    
    # Preprocess text
    text = preprocess_text(text)
    
    # Split by sentence endings (Korean and English)
    sentences = re.split(r'[.!?]\s+', text)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # Add sentence to current chunk
        potential_chunk = current_chunk + ". " + sentence if current_chunk else sentence
        
        # If chunk would be too large, save current and start new
        if len(potential_chunk) > max_chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            
            # Start new chunk with overlap
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + ". " + sentence
            else:
                current_chunk = sentence
        else:
            current_chunk = potential_chunk
    
    # Add the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Filter out very short chunks
    return [chunk for chunk in chunks if len(chunk.strip()) > 10]


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract key terms from text for better retrieval.
    
    Args:
        text: Text to extract keywords from
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of extracted keywords
    """
    if not text:
        return []
    
    # Preprocess text
    text = preprocess_text(text)
    
    # Simple keyword extraction based on word frequency and length
    words = text.split()
    
    # Filter words (remove short words, common words)
    filtered_words = []
    common_words = {'이', '그', '저', '것', '수', '있', '없', '하', '되', '의', '를', '을', '가', '이', '에', '와', '과'}
    
    for word in words:
        # Keep words that are longer than 2 characters and not common words
        if len(word) > 2 and word not in common_words:
            filtered_words.append(word)
    
    # Count frequency
    word_freq = {}
    for word in filtered_words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    keywords = sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)
    
    return keywords[:max_keywords]