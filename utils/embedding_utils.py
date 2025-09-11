"""
Embedding utilities for the Geography Auto-Grading System

This module provides utility functions for text preprocessing, 
embedding operations, and vector similarity calculations.
"""

import re
from typing import List, Dict, Optional
import numpy as np
from sentence_transformers import SentenceTransformer


def preprocess_text(text: str) -> str:
    """
    Preprocess text for better embedding quality.
    
    Args:
        text: Raw text to preprocess
        
    Returns:
        Cleaned and normalized text
    """
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters but keep Korean, English, numbers, and basic punctuation
    text = re.sub(r'[^\w\s가-힣.,!?()-]', ' ', text)
    
    # Remove multiple consecutive punctuation
    text = re.sub(r'[.,!?]{2,}', '.', text)
    
    return text.strip()


def calculate_text_similarity(text1: str, text2: str, model: SentenceTransformer) -> float:
    """
    Calculate semantic similarity between two texts using embeddings.
    
    Args:
        text1: First text
        text2: Second text  
        model: Loaded SentenceTransformer model
        
    Returns:
        Similarity score between 0 and 1
    """
    try:
        # Preprocess texts
        text1 = preprocess_text(text1)
        text2 = preprocess_text(text2)
        
        if not text1 or not text2:
            return 0.0
        
        # Generate embeddings
        embeddings = model.encode([text1, text2], convert_to_numpy=True)
        
        # Calculate cosine similarity
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        
        # Ensure similarity is between 0 and 1
        return max(0.0, min(1.0, float(similarity)))
        
    except Exception:
        return 0.0


def validate_embedding_dimension(embeddings: np.ndarray, expected_dim: int) -> bool:
    """
    Validate that embeddings have the expected dimension.
    
    Args:
        embeddings: Numpy array of embeddings
        expected_dim: Expected embedding dimension
        
    Returns:
        True if dimensions match, False otherwise
    """
    if embeddings is None or embeddings.size == 0:
        return False
    
    return embeddings.shape[-1] == expected_dim


def normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
    """
    Normalize embeddings to unit length for better similarity calculations.
    
    Args:
        embeddings: Numpy array of embeddings
        
    Returns:
        Normalized embeddings
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