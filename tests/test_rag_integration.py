"""
Integration tests for RAG Service

Tests the RAG service with actual document processing and embedding generation.
"""

import pytest
import tempfile
import os
from io import BytesIO
from unittest.mock import patch, Mock

from services.rag_service import RAGService


class TestRAGIntegration:
    """Integration tests for RAG service with real document processing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rag_service = RAGService()
    
    def create_mock_pdf_file(self, content: str) -> BytesIO:
        """Create a mock PDF file for testing."""
        # Create a simple mock file object
        mock_file = Mock()
        mock_file.name = "test_document.pdf"
        mock_file.read.return_value = b"mock pdf content"
        return mock_file
    
    def create_mock_docx_file(self, content: str) -> BytesIO:
        """Create a mock DOCX file for testing."""
        mock_file = Mock()
        mock_file.name = "test_document.docx"
        mock_file.read.return_value = b"mock docx content"
        return mock_file
    
    @patch('services.rag_service.SentenceTransformer')
    @patch('services.rag_service.PyPDF2.PdfReader')
    @patch('faiss.IndexFlatIP')
    def test_end_to_end_pdf_processing(self, mock_faiss, mock_pdf_reader, mock_transformer):
        """Test complete PDF processing workflow."""
        # Mock PDF content extraction
        mock_page = Mock()
        mock_page.extract_text.return_value = "지리학은 지구의 표면과 인간 활동 간의 관계를 연구하는 학문입니다. 지형, 기후, 인구 분포 등을 다룹니다."
        
        mock_reader = Mock()
        mock_reader.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader
        
        # Mock embedding model
        mock_model = Mock()
        import numpy as np
        mock_embeddings = np.array([[0.1] * 768, [0.2] * 768], dtype=np.float32)  # 2 chunks
        mock_model.encode.return_value = mock_embeddings
        mock_transformer.return_value = mock_model
        
        # Mock FAISS index
        mock_index = Mock()
        mock_faiss.return_value = mock_index
        
        # Create mock file
        mock_file = self.create_mock_pdf_file("test content")
        
        # Process document
        result = self.rag_service.process_reference_documents([mock_file])
        
        # Verify processing was successful
        assert result["success"] is True
        assert result["chunks_created"] > 0
        assert "test_document.pdf" in result["files_processed"]
        
        # Verify model and index were used
        mock_transformer.assert_called_once_with("nlpai-lab/KURE-v1")
        mock_model.encode.assert_called()
        mock_index.add.assert_called_once()
    
    @patch('services.rag_service.SentenceTransformer')
    @patch('services.rag_service.Document')
    @patch('faiss.IndexFlatIP')
    def test_end_to_end_docx_processing(self, mock_faiss, mock_docx, mock_transformer):
        """Test complete DOCX processing workflow."""
        # Mock DOCX content extraction
        mock_paragraph1 = Mock()
        mock_paragraph1.text = "한국의 지형은 산지가 많고 평야가 적습니다."
        
        mock_paragraph2 = Mock()
        mock_paragraph2.text = "기후는 온대 몬순 기후로 사계절이 뚜렷합니다."
        
        mock_doc = Mock()
        mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2]
        mock_docx.return_value = mock_doc
        
        # Mock embedding model
        mock_model = Mock()
        import numpy as np
        mock_embeddings = np.array([[0.1] * 768], dtype=np.float32)  # 1 chunk
        mock_model.encode.return_value = mock_embeddings
        mock_transformer.return_value = mock_model
        
        # Mock FAISS index
        mock_index = Mock()
        mock_faiss.return_value = mock_index
        
        # Create mock file
        mock_file = self.create_mock_docx_file("test content")
        
        # Process document
        result = self.rag_service.process_reference_documents([mock_file])
        
        # Verify processing was successful
        assert result["success"] is True
        assert result["chunks_created"] > 0
        assert "test_document.docx" in result["files_processed"]
    
    @patch('services.rag_service.SentenceTransformer')
    @patch('faiss.IndexFlatIP')
    def test_search_after_processing(self, mock_faiss, mock_transformer):
        """Test similarity search after document processing."""
        # Setup mock embedding model
        mock_model = Mock()
        
        # Mock embeddings for document chunks
        import numpy as np
        doc_embeddings = np.array([[0.1] * 768, [0.2] * 768, [0.3] * 768], dtype=np.float32)
        query_embedding = np.array([[0.15] * 768], dtype=np.float32)  # Similar to first chunk
        
        mock_model.encode.side_effect = [doc_embeddings, query_embedding]
        mock_transformer.return_value = mock_model
        
        # Setup mock FAISS index
        mock_index = Mock()
        similarities = [[0.9, 0.7, 0.5]]  # Similarity scores
        indices = [[0, 1, 2]]  # Chunk indices
        mock_index.search.return_value = (similarities, indices)
        mock_faiss.return_value = mock_index
        
        # Manually setup processed data (simulating successful processing)
        self.rag_service.faiss_index = mock_index
        self.rag_service.document_chunks = [
            "지리학은 지구 표면을 연구하는 학문입니다.",
            "한국의 지형은 산지가 많습니다.",
            "기후는 온대 몬순 기후입니다."
        ]
        self.rag_service.chunk_metadata = [
            {"source": "test.pdf", "chunk_id": 0},
            {"source": "test.pdf", "chunk_id": 1},
            {"source": "test.pdf", "chunk_id": 2}
        ]
        self.rag_service.embedding_model = mock_model
        
        # Perform search
        query = "지리학이 무엇인가요?"
        results = self.rag_service.search_relevant_content(query, top_k=3)
        
        # Verify search results
        assert len(results) == 3
        assert results[0]["content"] == "지리학은 지구 표면을 연구하는 학문입니다."
        assert results[0]["similarity_score"] == 0.9
        assert results[0]["rank"] == 1
        assert results[0]["metadata"]["source"] == "test.pdf"
        
        # Verify search was performed correctly
        mock_index.search.assert_called_once()
    
    def test_unsupported_file_format(self):
        """Test handling of unsupported file formats."""
        # Create mock file with unsupported extension
        mock_file = Mock()
        mock_file.name = "test_document.txt"
        mock_file.read.return_value = b"text content"
        
        # Process document
        result = self.rag_service.process_reference_documents([mock_file])
        
        # Should handle gracefully but not create chunks
        assert result["success"] is False
        assert result["chunks_created"] == 0
    
    def test_empty_document_handling(self):
        """Test handling of empty documents."""
        # Test with empty file list
        result = self.rag_service.process_reference_documents([])
        
        assert result["success"] is False
        assert result["chunks_created"] == 0
        assert "No valid content" in result["message"]
    
    @patch('services.rag_service.SentenceTransformer')
    def test_service_readiness_check(self, mock_transformer):
        """Test service readiness checks."""
        # Initially not ready
        assert self.rag_service.is_ready() is False
        
        # Mock setup
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        
        # After setting up index and chunks, should be ready
        self.rag_service.faiss_index = Mock()
        self.rag_service.document_chunks = ["test chunk"]
        
        assert self.rag_service.is_ready() is True
        
        # After clearing, should not be ready
        self.rag_service.clear_index()
        assert self.rag_service.is_ready() is False