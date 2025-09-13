"""
Unit tests for RAG Service

Tests the core functionality of the RAG service including document processing,
embedding generation, and similarity search.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from services.rag_service import RAGService, create_rag_service, format_retrieved_content
from utils.embedding_utils import preprocess_text, chunk_text_by_sentences


class TestRAGService:
    """Test cases for RAG Service functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rag_service = RAGService()
    
    def test_initialization(self):
        """Test RAG service initialization."""
        assert self.rag_service.model_name == "nlpai-lab/KURE-v1"
        assert self.rag_service.embedding_dimension == 768
        assert self.rag_service.faiss_index is None
        assert len(self.rag_service.document_chunks) == 0
        assert len(self.rag_service.chunk_metadata) == 0
    
    def test_chunk_document(self):
        """Test document chunking functionality."""
        # Test with normal text
        content = "이것은 첫 번째 문장입니다. 이것은 두 번째 문장입니다. 이것은 세 번째 문장입니다."
        chunks = self.rag_service._chunk_document(content, chunk_size=50, overlap=10)
        
        assert len(chunks) > 0
        assert all(len(chunk) <= 60 for chunk in chunks)  # Allow some flexibility for overlap
        
        # Test with empty content
        empty_chunks = self.rag_service._chunk_document("", chunk_size=100)
        assert len(empty_chunks) == 0
        
        # Test with very short content
        short_content = "짧은 텍스트"
        short_chunks = self.rag_service._chunk_document(short_content, chunk_size=100)
        assert len(short_chunks) == 0  # Too short, should be filtered out
    
    @patch('services.rag_service.SentenceTransformer')
    def test_load_embedding_model(self, mock_sentence_transformer):
        """Test embedding model loading."""
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model
        
        self.rag_service._load_embedding_model()
        
        mock_sentence_transformer.assert_called_once_with("nlpai-lab/KURE-v1")
        assert self.rag_service.embedding_model == mock_model
    
    @patch('services.rag_service.SentenceTransformer')
    @patch('faiss.IndexFlatIP')
    def test_create_embeddings_and_index(self, mock_faiss_index, mock_sentence_transformer):
        """Test embedding creation and FAISS index building."""
        # Mock the embedding model
        mock_model = Mock()
        mock_embeddings = np.random.rand(3, 768).astype(np.float32)
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model
        
        # Mock FAISS index
        mock_index = Mock()
        mock_faiss_index.return_value = mock_index
        
        # Test data
        chunks = ["첫 번째 청크입니다.", "두 번째 청크입니다.", "세 번째 청크입니다."]
        sources = ["test1.pdf", "test1.pdf", "test2.pdf"]
        
        self.rag_service._create_embeddings_and_index(chunks, sources)
        
        # Verify model was loaded and used
        mock_model.encode.assert_called_once()
        
        # Verify FAISS index was created and populated
        mock_faiss_index.assert_called_once_with(768)
        mock_index.add.assert_called_once()
        
        # Verify chunks and metadata were stored
        assert self.rag_service.document_chunks == chunks
        assert len(self.rag_service.chunk_metadata) == 3
        assert self.rag_service.chunk_metadata[0]["source"] == "test1.pdf"
    
    def test_create_embeddings_and_index_empty_chunks(self):
        """Test embedding creation with empty chunks."""
        with pytest.raises(ValueError, match="No chunks provided for embedding"):
            self.rag_service._create_embeddings_and_index([], [])
    
    @patch('services.rag_service.SentenceTransformer')
    def test_search_relevant_content(self, mock_sentence_transformer):
        """Test similarity search functionality."""
        # Setup mock model and index
        mock_model = Mock()
        query_embedding = np.random.rand(1, 768).astype(np.float32)
        mock_model.encode.return_value = query_embedding
        mock_sentence_transformer.return_value = mock_model
        
        # Setup mock FAISS index
        mock_index = Mock()
        similarities = np.array([[0.9, 0.8, 0.7]])
        indices = np.array([[0, 1, 2]])
        mock_index.search.return_value = (similarities, indices)
        
        # Setup test data
        self.rag_service.embedding_model = mock_model
        self.rag_service.faiss_index = mock_index
        self.rag_service.document_chunks = [
            "첫 번째 관련 내용",
            "두 번째 관련 내용", 
            "세 번째 관련 내용"
        ]
        self.rag_service.chunk_metadata = [
            {"source": "test1.pdf", "chunk_id": 0},
            {"source": "test1.pdf", "chunk_id": 1},
            {"source": "test2.pdf", "chunk_id": 2}
        ]
        
        # Test search
        query = "지리 관련 질문"
        results = self.rag_service.search_relevant_content(query, top_k=3)
        
        # Verify results
        assert len(results) == 3
        assert results[0]["content"] == "첫 번째 관련 내용"
        assert results[0]["similarity_score"] == 0.9
        assert results[0]["rank"] == 1
        assert results[0]["metadata"]["source"] == "test1.pdf"
        
        # Verify model was called correctly
        mock_model.encode.assert_called_with([query], convert_to_numpy=True)
        # Verify search was called with correct parameters (can't directly compare numpy arrays)
        assert mock_index.search.call_count == 1
        call_args = mock_index.search.call_args[0]
        assert call_args[1] == 3  # top_k parameter
        assert call_args[0].shape == query_embedding.shape  # embedding shape
    
    def test_search_relevant_content_no_index(self):
        """Test search with no FAISS index."""
        results = self.rag_service.search_relevant_content("test query")
        assert len(results) == 0
    
    def test_search_relevant_content_empty_query(self):
        """Test search with empty query."""
        # Setup minimal mock data
        self.rag_service.faiss_index = Mock()
        self.rag_service.document_chunks = ["test chunk"]
        
        results = self.rag_service.search_relevant_content("")
        assert len(results) == 0
    
    def test_get_index_stats(self):
        """Test index statistics retrieval."""
        # Test with no index
        stats = self.rag_service.get_index_stats()
        assert stats["index_exists"] is False
        assert stats["total_vectors"] == 0
        assert stats["total_chunks"] == 0
        assert stats["embedding_dimension"] == 768
        assert stats["model_name"] == "nlpai-lab/KURE-v1"
        
        # Test with mock index
        mock_index = Mock()
        mock_index.ntotal = 10
        self.rag_service.faiss_index = mock_index
        self.rag_service.document_chunks = ["chunk1", "chunk2"]
        
        stats = self.rag_service.get_index_stats()
        assert stats["index_exists"] is True
        assert stats["total_vectors"] == 10
        assert stats["total_chunks"] == 2
    
    def test_clear_index(self):
        """Test index clearing functionality."""
        # Setup some mock data
        self.rag_service.faiss_index = Mock()
        self.rag_service.document_chunks = ["chunk1", "chunk2"]
        self.rag_service.chunk_metadata = [{"source": "test.pdf"}]
        
        # Clear index
        self.rag_service.clear_index()
        
        # Verify everything is cleared
        assert self.rag_service.faiss_index is None
        assert len(self.rag_service.document_chunks) == 0
        assert len(self.rag_service.chunk_metadata) == 0
    
    def test_is_ready(self):
        """Test readiness check."""
        # Test not ready (no index)
        assert self.rag_service.is_ready() is False
        
        # Test not ready (no chunks)
        self.rag_service.faiss_index = Mock()
        assert self.rag_service.is_ready() is False
        
        # Test ready
        self.rag_service.document_chunks = ["chunk1"]
        assert self.rag_service.is_ready() is True


class TestRAGUtilityFunctions:
    """Test utility functions for RAG service."""
    
    def test_create_rag_service(self):
        """Test RAG service factory function."""
        service = create_rag_service()
        assert isinstance(service, RAGService)
        assert service.model_name == "nlpai-lab/KURE-v1"
    
    def test_format_retrieved_content(self):
        """Test content formatting for prompts."""
        # Test with empty results
        formatted = format_retrieved_content([])
        assert formatted == ""
        
        # Test with short results
        short_results = [
            "첫 번째 참고 내용입니다.",
            "두 번째 참고 내용입니다."
        ]
        
        formatted = format_retrieved_content(short_results)
        assert "참고자료 1" in formatted
        assert "참고자료 2" in formatted
        assert "첫 번째 참고 내용" in formatted
        assert "두 번째 참고 내용" in formatted
        
        # Test with long results that need truncation
        long_results = [
            "이것은 매우 긴 참고 내용입니다. " * 20 + "이 내용은 300자를 훨씬 넘어서 잘려나가야 합니다.",
            "이것도 매우 긴 참고 내용입니다. " * 15 + "이 내용도 300자를 넘어서 잘려나가야 합니다."
        ]
        
        formatted_long = format_retrieved_content(long_results)
        assert "..." in formatted_long  # Should be truncated
        
        # Check that each formatted chunk doesn't exceed 300 characters
        chunks = formatted_long.split('\n\n')
        for chunk in chunks:
            content = chunk.split(':\n', 1)[1] if ':\n' in chunk else chunk
            assert len(content) <= 303  # 300 + "..." = 303


class TestEmbeddingUtils:
    """Test embedding utility functions."""
    
    def test_preprocess_text(self):
        """Test text preprocessing."""
        # Test normal text
        text = "  이것은   테스트  텍스트입니다.  "
        processed = preprocess_text(text)
        assert processed == "이것은 테스트 텍스트입니다."
        
        # Test empty text
        assert preprocess_text("") == ""
        assert preprocess_text(None) == ""
        
        # Test text with special characters
        text_with_special = "텍스트@#$%입니다!!!"
        processed = preprocess_text(text_with_special)
        assert "@#$%" not in processed
        assert "텍스트" in processed
    
    def test_chunk_text_by_sentences(self):
        """Test sentence-based text chunking."""
        text = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다."
        chunks = chunk_text_by_sentences(text, max_chunk_size=30, overlap=5)
        
        assert len(chunks) > 0
        assert all(len(chunk) <= 40 for chunk in chunks)  # Allow some flexibility
        
        # Test empty text
        empty_chunks = chunk_text_by_sentences("")
        assert len(empty_chunks) == 0