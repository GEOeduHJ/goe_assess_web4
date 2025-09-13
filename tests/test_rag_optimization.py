"""
Unit tests for the optimized RAG service functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from io import BytesIO

from services.rag_service import RAGService, RAGProcessingResult
from config import config


class TestRAGOptimization(unittest.TestCase):
    """Test cases for the optimized RAG service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rag_service = RAGService()
        
        # Create mock file objects
        self.mock_pdf_file = Mock()
        self.mock_pdf_file.name = "test.pdf"
        self.mock_pdf_file.read.return_value = b"PDF content for testing"
        
        self.mock_docx_file = Mock()
        self.mock_docx_file.name = "test.docx"
        self.mock_docx_file.read.return_value = b"DOCX content for testing"
    
    def test_process_documents_for_student_returns_result(self):
        """Test that process_documents_for_student returns a RAGProcessingResult."""
        # Mock the select_relevant_documents method
        with patch.object(self.rag_service, 'select_relevant_documents', return_value=[self.mock_pdf_file]):
            # Mock the process_single_document_for_student method
            with patch.object(self.rag_service, 'process_single_document_for_student', return_value=[]):
                result = self.rag_service.process_documents_for_student(
                    uploaded_files=[self.mock_pdf_file],
                    student_response="Test student response"
                )
                
                # Check that result is of correct type
                self.assertIsInstance(result, RAGProcessingResult)
                self.assertTrue(hasattr(result, 'success'))
                self.assertTrue(hasattr(result, 'content'))
                self.assertTrue(hasattr(result, 'processing_time'))
    
    def test_process_single_document_for_student_returns_list(self):
        """Test that process_single_document_for_student returns a list of chunks."""
        # Mock the _extract_document_content method
        with patch.object(self.rag_service, '_extract_document_content', return_value="Test content"):
            # Mock the embedding model
            mock_model = Mock()
            mock_model.encode.return_value = [[0.1, 0.2, 0.3]]  # Mock embeddings
            self.rag_service.embedding_model = mock_model
            
            # Mock faiss
            with patch('services.rag_service.faiss'):
                result = self.rag_service.process_single_document_for_student(
                    file_obj=self.mock_pdf_file,
                    student_response="Test response"
                )
                
                # Check that result is a list
                self.assertIsInstance(result, list)
    
    def test_select_relevant_documents_limits_documents(self):
        """Test that select_relevant_documents limits the number of documents."""
        # Create more mock files than the limit
        mock_files = [Mock() for _ in range(10)]
        for i, mock_file in enumerate(mock_files):
            mock_file.name = f"document_{i}.pdf"
        
        selected = self.rag_service.select_relevant_documents(
            uploaded_files=mock_files,
            student_response="Test response",
            max_docs=5
        )
        
        # Should return limited number of documents
        self.assertEqual(len(selected), 5)
        self.assertEqual(selected, mock_files[:5])
    
    def test_process_documents_for_student_handles_empty_files(self):
        """Test that process_documents_for_student handles empty file list."""
        result = self.rag_service.process_documents_for_student(
            uploaded_files=[],
            student_response="Test response"
        )
        
        # Should return successful result with empty content
        self.assertTrue(result.success)
        self.assertEqual(result.content, [])
        self.assertGreaterEqual(result.processing_time, 0)
    
    def test_rag_processing_result_structure(self):
        """Test that RAGProcessingResult has the correct structure."""
        result = RAGProcessingResult(
            success=True,
            content=[{"test": "data"}],
            processing_time=1.5,
            error_message=None
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.content, [{"test": "data"}])
        self.assertEqual(result.processing_time, 1.5)
        self.assertIsNone(result.error_message)
        
        # Test with error
        error_result = RAGProcessingResult(
            success=False,
            content=[],
            processing_time=2.0,
            error_message="Test error"
        )
        
        self.assertFalse(error_result.success)
        self.assertEqual(error_result.content, [])
        self.assertEqual(error_result.processing_time, 2.0)
        self.assertEqual(error_result.error_message, "Test error")


if __name__ == '__main__':
    unittest.main()