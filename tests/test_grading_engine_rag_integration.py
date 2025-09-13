"""
Integration tests for the grading engine with optimized RAG functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.grading_engine import SequentialGradingEngine, StudentGradingStatus, GradingStatus
from models.student_model import Student
from models.rubric_model import Rubric, EvaluationElement, EvaluationCriteria
from models.result_model import GradingResult


class TestGradingEngineRAGIntegration(unittest.TestCase):
    """Test cases for grading engine integration with optimized RAG."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock LLM service
        self.mock_llm_service = Mock()
        self.mock_llm_service.validate_api_availability.return_value = {"gemini": True, "groq": True}
        
        # Create grading engine with mock LLM service
        self.grading_engine = SequentialGradingEngine(llm_service=self.mock_llm_service)
        
        # Create test student
        self.student = Student(
            name="Test Student",
            class_number="1반",
            answer="This is a test answer for geography questions."
        )
        
        # Create test rubric
        criteria = EvaluationCriteria(score=5, description="Excellent answer")
        element = EvaluationElement(name="Geography Knowledge", max_score=5)
        element.criteria.append(criteria)
        
        self.rubric = Rubric(name="Geography Test Rubric")
        self.rubric.elements.append(element)
        
        # Create mock grading result
        self.mock_result = GradingResult(
            student_name="Test Student",
            student_class_number="1반",
            grading_time_seconds=1.5
        )
        self.mock_result.add_element_score("Geography Knowledge", 5, 5, "Excellent work!")
    
    def test_grade_student_with_retries_uses_on_demand_rag(self):
        """Test that _grade_student_with_retries uses on-demand RAG processing."""
        # Mock the LLM service response
        self.mock_llm_service.grade_student_sequential.return_value = self.mock_result
        
        # Create student status
        student_status = StudentGradingStatus(student=self.student)
        
        # Mock RAG service
        mock_rag_result = Mock()
        mock_rag_result.success = True
        mock_rag_result.content = [{"content": "Test reference content", "similarity_score": 0.9}]
        
        with patch('services.grading_engine.RAGService') as mock_rag_service_class:
            mock_rag_service_instance = Mock()
            mock_rag_service_instance.process_documents_for_student.return_value = mock_rag_result
            mock_rag_service_class.return_value = mock_rag_service_instance
            
            # Call _grade_student_with_retries with uploaded_files for on-demand RAG
            result = self.grading_engine._grade_student_with_retries(
                student_status=student_status,
                rubric=self.rubric,
                model_type="gemini",
                grading_type="descriptive",
                references=None,
                max_retries=1,
                uploaded_files=[Mock()]  # Provide uploaded files to trigger on-demand RAG
            )
            
            # Verify that RAG service was called
            mock_rag_service_class.assert_called()
            mock_rag_service_instance.process_documents_for_student.assert_called()
            
            # Verify that the result is returned correctly
            self.assertIsNotNone(result)
            self.assertEqual(student_status.status, GradingStatus.COMPLETED)
    
    def test_grade_student_with_retries_handles_rag_failure(self):
        """Test that _grade_student_with_retries handles RAG processing failures."""
        # Mock the LLM service response
        self.mock_llm_service.grade_student_sequential.return_value = self.mock_result
        
        # Create student status
        student_status = StudentGradingStatus(student=self.student)
        
        # Mock RAG service to simulate failure
        mock_rag_result = Mock()
        mock_rag_result.success = False
        mock_rag_result.error_message = "RAG processing failed"
        
        with patch('services.grading_engine.RAGService') as mock_rag_service_class:
            mock_rag_service_instance = Mock()
            mock_rag_service_instance.process_documents_for_student.return_value = mock_rag_result
            mock_rag_service_class.return_value = mock_rag_service_instance
            
            # Call _grade_student_with_retries with uploaded_files
            result = self.grading_engine._grade_student_with_retries(
                student_status=student_status,
                rubric=self.rubric,
                model_type="gemini",
                grading_type="descriptive",
                references=None,
                max_retries=1,
                uploaded_files=[Mock()]  # Provide uploaded files to trigger on-demand RAG
            )
            
            # Even with RAG failure, grading should continue with fallback
            self.assertIsNotNone(result)
            self.assertEqual(student_status.status, GradingStatus.COMPLETED)
    
    def test_grade_students_sequential_passes_uploaded_files(self):
        """Test that grade_students_sequential passes uploaded_files to individual grading."""
        # Mock the LLM service response
        self.mock_llm_service.grade_student_sequential.return_value = self.mock_result
        
        students = [self.student]
        
        # Mock RAG service
        mock_rag_result = Mock()
        mock_rag_result.success = True
        mock_rag_result.content = [{"content": "Test reference content", "similarity_score": 0.9}]
        
        with patch('services.grading_engine.RAGService') as mock_rag_service_class:
            mock_rag_service_instance = Mock()
            mock_rag_service_instance.process_documents_for_student.return_value = mock_rag_result
            mock_rag_service_class.return_value = mock_rag_service_instance
            
            # Call grade_students_sequential with uploaded_files
            results = self.grading_engine.grade_students_sequential(
                students=students,
                rubric=self.rubric,
                model_type="gemini",
                grading_type="descriptive",
                references=None,
                uploaded_files=[Mock()]  # Provide uploaded files
            )
            
            # Verify that the method was called and returned results
            self.assertEqual(len(results), 1)
            self.mock_llm_service.grade_student_sequential.assert_called()


if __name__ == '__main__':
    unittest.main()