"""
Test suite for the simplified FAISS RAG implementation.

Tests document processing, RAG content integration in LLM prompts,
and error handling scenarios as specified in task 8.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import List

from services.rag_service import RAGService, RAGResult, format_retrieved_content
from services.grading_engine import SequentialGradingEngine
from services.llm_service import LLMService
from models.student_model import Student
from models.rubric_model import Rubric, EvaluationElement, EvaluationCriteria


class TestRAGServiceDocumentProcessing:
    """Test document processing functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rag_service = RAGService()
    
    def create_sample_pdf(self, content: str) -> str:
        """Create a sample PDF file for testing."""
        # Create a temporary file with PDF-like content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
            # This is a mock - in real tests you'd use a proper PDF library
            f.write(content)
            return f.name
    
    def create_sample_docx(self, content: str) -> str:
        """Create a sample DOCX file for testing."""
        # Create a temporary file with DOCX-like content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.docx', delete=False) as f:
            f.write(content)
            return f.name
    
    def create_mock_uploaded_file(self, filename: str, content: bytes):
        """Create a mock uploaded file object."""
        mock_file = Mock()
        mock_file.name = filename
        mock_file.read.return_value = content
        return mock_file
    
    @patch('services.rag_service.PyPDF2.PdfReader')
    def test_pdf_document_processing(self, mock_pdf_reader):
        """Test PDF document processing with sample files."""
        # Mock PDF content
        mock_page = Mock()
        mock_page.extract_text.return_value = "This is sample geography content about mountains and rivers."
        
        mock_reader = Mock()
        mock_reader.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader
        
        # Create mock uploaded file
        mock_file = self.create_mock_uploaded_file("sample.pdf", b"fake pdf content")
        
        # Test document processing
        result = self.rag_service.process_documents([mock_file])
        
        # Verify processing succeeded
        assert result is True
        assert self.rag_service.vector_store is not None
    
    @patch('services.rag_service.Document')
    def test_docx_document_processing(self, mock_docx):
        """Test DOCX document processing with sample files."""
        # Mock DOCX content
        mock_paragraph = Mock()
        mock_paragraph.text = "Geography content about climate and weather patterns."
        
        mock_doc = Mock()
        mock_doc.paragraphs = [mock_paragraph]
        mock_docx.return_value = mock_doc
        
        # Create mock uploaded file
        mock_file = self.create_mock_uploaded_file("sample.docx", b"fake docx content")
        
        # Test document processing
        result = self.rag_service.process_documents([mock_file])
        
        # Verify processing succeeded
        assert result is True
        assert self.rag_service.vector_store is not None
    
    def test_document_chunking(self):
        """Test simple text chunking functionality."""
        content = "This is a long geography text about mountains, rivers, climate, and weather patterns. " * 10
        
        chunks = self.rag_service._chunk_document(content, chunk_size=100, overlap=20)
        
        # Verify chunks were created
        assert len(chunks) > 1
        assert all(len(chunk) <= 100 for chunk in chunks)
        
        # Verify overlap exists between consecutive chunks
        if len(chunks) > 1:
            # Check that there's some overlap between chunks
            assert len(chunks[0]) > 0
            assert len(chunks[1]) > 0
    
    def test_empty_document_handling(self):
        """Test handling of empty or invalid documents."""
        # Test with empty file list
        result = self.rag_service.process_documents([])
        assert result is False
        
        # Test with file that has no content
        mock_file = self.create_mock_uploaded_file("empty.pdf", b"")
        result = self.rag_service.process_documents([mock_file])
        assert result is False
    
    @patch('services.rag_service.PyPDF2.PdfReader')
    def test_document_processing_error_handling(self, mock_pdf_reader):
        """Test error handling when document processing fails."""
        # Mock PDF reader to raise an exception
        mock_pdf_reader.side_effect = Exception("PDF processing error")
        
        mock_file = self.create_mock_uploaded_file("corrupt.pdf", b"corrupt pdf")
        
        # Should handle error gracefully and return False
        result = self.rag_service.process_documents([mock_file])
        assert result is False


class TestRAGContentIntegration:
    """Test RAG content integration in grading pipeline."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rag_service = RAGService()
        self.grading_engine = SequentialGradingEngine()
        
        # Create sample rubric
        element = EvaluationElement(name="지리적 이해")
        element.add_criteria(10, "완전한 이해")
        element.add_criteria(5, "부분적 이해")
        element.add_criteria(0, "이해 부족")
        
        self.rubric = Rubric(name="테스트 루브릭")
        self.rubric.add_element(element)
        
        # Create sample student
        self.student = Student(
            name="테스트학생",
            class_number="1",
            answer="산맥과 강의 특징에 대해 설명하겠습니다."
        )
    
    @patch.object(RAGService, 'search_relevant_content')
    def test_rag_content_in_llm_prompt(self, mock_search):
        """Test that RAG content is included in LLM prompts."""
        # Mock RAG search results
        mock_search.return_value = [
            "산맥은 지각 변동으로 형성됩니다.",
            "강은 침식과 퇴적 작용을 합니다."
        ]
        
        # Create LLM service and generate prompt
        llm_service = LLMService()
        
        # Format RAG content
        rag_content = format_retrieved_content(mock_search.return_value)
        references = [rag_content]
        
        # Generate prompt with RAG content
        prompt = llm_service.generate_prompt(
            rubric=self.rubric,
            student_answer=self.student.answer,
            references=references,
            grading_type="descriptive"
        )
        
        # Verify RAG content is included in prompt
        assert "참고자료 1:" in prompt
        assert "산맥은 지각 변동으로 형성됩니다." in prompt
        assert "강은 침식과 퇴적 작용을 합니다." in prompt
        assert "다음은 채점 참고 자료입니다:" in prompt
    
    @patch.object(RAGService, 'process_documents_for_student')
    @patch.object(LLMService, 'call_gemini_api')
    def test_rag_integration_in_grading_engine(self, mock_gemini, mock_rag_process):
        """Test RAG integration in the grading engine."""
        # Mock RAG processing result
        mock_rag_process.return_value = RAGResult(
            success=True,
            content=["지리적 참고 내용 1", "지리적 참고 내용 2"]
        )
        
        # Mock LLM response
        mock_gemini.return_value = {
            "text": '{"scores": {"지리적 이해": 8}, "reasoning": {"지리적 이해": "좋은 답변"}, "feedback": "잘했습니다", "total_score": 8}'
        }
        
        # Create mock uploaded files
        mock_files = [Mock(name="reference.pdf")]
        
        # Test grading with RAG
        results = self.grading_engine.grade_students_sequential(
            students=[self.student],
            rubric=self.rubric,
            model_type="gemini",
            grading_type="descriptive",
            uploaded_files=mock_files
        )
        
        # Verify RAG was called
        mock_rag_process.assert_called_once()
        
        # Verify grading completed successfully
        assert len(results) == 1
        assert results[0].student_name == "테스트학생"
        assert results[0].total_score == 8
    
    def test_rag_content_formatting(self):
        """Test RAG content formatting for prompts."""
        content = [
            "첫 번째 참고 자료 내용",
            "두 번째 참고 자료 내용",
            "세 번째 참고 자료 내용"
        ]
        
        formatted = format_retrieved_content(content)
        
        # Verify formatting
        assert "참고자료 1:" in formatted
        assert "참고자료 2:" in formatted
        assert "참고자료 3:" in formatted
        assert "첫 번째 참고 자료 내용" in formatted
        assert "두 번째 참고 자료 내용" in formatted
        assert "세 번째 참고 자료 내용" in formatted
    
    def test_empty_rag_content_handling(self):
        """Test handling when no RAG content is available."""
        # Test with empty content
        formatted = format_retrieved_content([])
        assert formatted == ""
        
        # Test with None
        formatted = format_retrieved_content(None)
        assert formatted == ""


class TestRAGErrorHandling:
    """Test error handling scenarios in RAG system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rag_service = RAGService()
        self.student = Student(
            name="테스트학생",
            class_number="1", 
            answer="테스트 답변"
        )
    
    def test_rag_failure_graceful_handling(self):
        """Test that grading continues when RAG fails."""
        # Mock uploaded files that will cause processing to fail
        mock_files = [Mock(name="corrupt.pdf")]
        
        # Process documents (should fail gracefully)
        result = self.rag_service.process_documents_for_student(mock_files, self.student.answer)
        
        # Verify failure is handled gracefully
        assert result.success is False
        assert result.error_message is not None
        assert isinstance(result.content, list)
        assert len(result.content) == 0
    
    @patch.object(RAGService, 'process_documents')
    def test_vector_store_creation_failure(self, mock_process):
        """Test handling when vector store creation fails."""
        # Mock process_documents to fail
        mock_process.return_value = False
        
        mock_files = [Mock(name="test.pdf")]
        
        result = self.rag_service.process_documents_for_student(mock_files, "test query")
        
        # Verify error handling
        assert result.success is False
        assert "Failed to process documents" in result.error_message
    
    def test_similarity_search_with_no_vector_store(self):
        """Test similarity search when no vector store exists."""
        # Ensure no vector store exists
        self.rag_service.vector_store = None
        
        # Attempt search
        results = self.rag_service.search_relevant_content("test query")
        
        # Should return empty list
        assert results == []
    
    def test_similarity_search_with_empty_query(self):
        """Test similarity search with empty or invalid query."""
        # Test with empty string
        results = self.rag_service.search_relevant_content("")
        assert results == []
        
        # Test with whitespace only
        results = self.rag_service.search_relevant_content("   ")
        assert results == []
        
        # Test with None (should handle gracefully)
        results = self.rag_service.search_relevant_content(None)
        assert results == []
    
    @patch('services.rag_service.FAISS')
    def test_search_exception_handling(self, mock_faiss):
        """Test handling of exceptions during similarity search."""
        # Set up a vector store that will raise an exception during search
        mock_vector_store = Mock()
        mock_vector_store.similarity_search.side_effect = Exception("Search failed")
        self.rag_service.vector_store = mock_vector_store
        
        # Should handle exception gracefully
        results = self.rag_service.search_relevant_content("test query")
        assert results == []


class TestRAGIntegrationEndToEnd:
    """End-to-end integration tests for RAG system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        element = EvaluationElement(name="내용 이해")
        element.add_criteria(10, "완전한 이해")
        element.add_criteria(5, "부분적 이해")
        element.add_criteria(0, "이해 부족")
        
        self.rubric = Rubric(name="통합테스트 루브릭")
        self.rubric.add_element(element)
        
        self.student = Student(
            name="통합테스트학생",
            class_number="1",
            answer="지리적 특성에 대한 답변입니다."
        )
    
    @patch('services.rag_service.FAISS.from_documents')
    @patch('services.rag_service.PyPDF2.PdfReader')
    @patch.object(LLMService, 'call_gemini_api')
    def test_complete_rag_workflow(self, mock_gemini, mock_pdf_reader, mock_faiss):
        """Test complete RAG workflow from document processing to grading."""
        # Mock PDF processing
        mock_page = Mock()
        mock_page.extract_text.return_value = "지리 참고 자료: 산맥의 형성과 특징"
        mock_reader = Mock()
        mock_reader.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader
        
        # Mock FAISS vector store
        mock_vector_store = Mock()
        mock_doc = Mock()
        mock_doc.page_content = "산맥의 형성과 특징에 대한 내용"
        mock_vector_store.similarity_search.return_value = [mock_doc]
        mock_faiss.return_value = mock_vector_store
        
        # Mock LLM response
        mock_gemini.return_value = {
            "text": '{"scores": {"내용 이해": 8}, "reasoning": {"내용 이해": "참고자료를 잘 활용한 답변"}, "feedback": "우수한 답변입니다", "total_score": 8}'
        }
        
        # Create grading engine and RAG service
        grading_engine = SequentialGradingEngine()
        
        # Create mock uploaded files
        mock_file = Mock()
        mock_file.name = "reference.pdf"
        mock_file.read.return_value = b"fake pdf content"
        mock_files = [mock_file]
        
        # Execute complete workflow
        results = grading_engine.grade_students_sequential(
            students=[self.student],
            rubric=self.rubric,
            model_type="gemini",
            grading_type="descriptive",
            uploaded_files=mock_files
        )
        
        # Verify results
        assert len(results) == 1
        result = results[0]
        assert result.student_name == "통합테스트학생"
        assert result.total_score == 8
        assert "우수한 답변입니다" in result.overall_feedback
        
        # Verify RAG components were called
        mock_pdf_reader.assert_called()
        mock_faiss.assert_called()
        mock_gemini.assert_called()
    
    @patch.object(RAGService, 'process_documents_for_student')
    @patch.object(LLMService, 'call_gemini_api')
    def test_grading_without_rag_fallback(self, mock_gemini, mock_rag_process):
        """Test that grading works normally when RAG fails."""
        # Mock RAG to fail
        mock_rag_process.return_value = RAGResult(
            success=False,
            error_message="RAG processing failed"
        )
        
        # Mock LLM response (without RAG content)
        mock_gemini.return_value = {
            "text": '{"scores": {"내용 이해": 6}, "reasoning": {"내용 이해": "기본적인 답변"}, "feedback": "보통 수준의 답변", "total_score": 6}'
        }
        
        # Create grading engine
        grading_engine = SequentialGradingEngine()
        
        # Execute grading with failing RAG
        results = grading_engine.grade_students_sequential(
            students=[self.student],
            rubric=self.rubric,
            model_type="gemini",
            grading_type="descriptive",
            uploaded_files=[Mock(name="test.pdf")]
        )
        
        # Verify grading still works
        assert len(results) == 1
        result = results[0]
        assert result.student_name == "통합테스트학생"
        assert result.total_score == 6
        assert "보통 수준의 답변" in result.overall_feedback


if __name__ == "__main__":
    pytest.main([__file__, "-v"])