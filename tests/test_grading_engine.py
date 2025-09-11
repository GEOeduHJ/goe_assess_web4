"""
Tests for the Sequential Grading Engine.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.grading_engine import (
    SequentialGradingEngine, 
    GradingStatus, 
    StudentGradingStatus, 
    GradingProgress
)
from services.llm_service import LLMService, GradingType
from models.student_model import Student
from models.rubric_model import Rubric, EvaluationElement, EvaluationCriteria
from models.result_model import GradingResult


@pytest.fixture
def sample_students():
    """Create sample students for testing."""
    return [
        Student(name="김철수", class_number="1-1", answer="한국의 수도는 서울이다."),
        Student(name="이영희", class_number="1-2", answer="부산은 한국의 제2의 도시이다."),
        Student(name="박민수", class_number="1-3", answer="제주도는 한국의 남쪽에 위치한다.")
    ]


@pytest.fixture
def sample_rubric():
    """Create sample rubric for testing."""
    rubric = Rubric(name="지리 기본 지식")
    
    # 정확성 평가 요소
    accuracy_element = EvaluationElement(name="정확성")
    accuracy_element.add_criteria(5, "완전히 정확한 답변")
    accuracy_element.add_criteria(3, "부분적으로 정확한 답변")
    accuracy_element.add_criteria(1, "부정확한 답변")
    accuracy_element.add_criteria(0, "답변 없음")
    
    # 완성도 평가 요소
    completeness_element = EvaluationElement(name="완성도")
    completeness_element.add_criteria(5, "완전한 답변")
    completeness_element.add_criteria(3, "부분적 답변")
    completeness_element.add_criteria(1, "불완전한 답변")
    completeness_element.add_criteria(0, "답변 없음")
    
    rubric.add_element(accuracy_element)
    rubric.add_element(completeness_element)
    
    return rubric


@pytest.fixture
def mock_llm_service():
    """Create mock LLM service."""
    mock_service = Mock(spec=LLMService)
    
    # Mock successful grading result
    def mock_grade_student(student, rubric, model_type, grading_type, references=None):
        result = GradingResult(
            student_name=student.name,
            student_class_number=student.class_number,
            grading_time_seconds=2.5,
            overall_feedback="좋은 답변입니다."
        )
        result.add_element_score("정확성", 4, 5, "정확한 내용입니다.")
        result.add_element_score("완성도", 3, 5, "조금 더 자세한 설명이 필요합니다.")
        return result
    
    mock_service.grade_student_sequential.side_effect = mock_grade_student
    mock_service.validate_api_availability.return_value = {"gemini": True, "groq": True}
    
    return mock_service


class TestStudentGradingStatus:
    """Test StudentGradingStatus class."""
    
    def test_initialization(self, sample_students):
        """Test status initialization."""
        student = sample_students[0]
        status = StudentGradingStatus(student=student)
        
        assert status.student == student
        assert status.status == GradingStatus.NOT_STARTED
        assert status.result is None
        assert status.error_message is None
        assert status.attempt_count == 0
        assert status.start_time is None
        assert status.end_time is None
    
    def test_processing_time_calculation(self, sample_students):
        """Test processing time calculation."""
        student = sample_students[0]
        status = StudentGradingStatus(student=student)
        
        # No times set
        assert status.processing_time == 0.0
        
        # Set times
        start_time = datetime.now()
        end_time = datetime.fromtimestamp(start_time.timestamp() + 5.0)
        status.start_time = start_time
        status.end_time = end_time
        
        assert abs(status.processing_time - 5.0) < 0.1


class TestGradingProgress:
    """Test GradingProgress class."""
    
    def test_initialization(self):
        """Test progress initialization."""
        progress = GradingProgress(total_students=10)
        
        assert progress.total_students == 10
        assert progress.completed_students == 0
        assert progress.failed_students == 0
        assert progress.current_student_index == 0
        assert progress.start_time is None
        assert progress.estimated_completion_time is None
        assert progress.average_processing_time == 0.0
    
    def test_progress_percentage(self):
        """Test progress percentage calculation."""
        progress = GradingProgress(total_students=10)
        
        # No progress
        assert progress.progress_percentage == 0.0
        
        # Partial progress
        progress.completed_students = 3
        progress.failed_students = 2
        assert progress.progress_percentage == 50.0
        
        # Complete
        progress.completed_students = 8
        progress.failed_students = 2
        assert progress.progress_percentage == 100.0
    
    def test_remaining_students(self):
        """Test remaining students calculation."""
        progress = GradingProgress(total_students=10)
        progress.completed_students = 3
        progress.failed_students = 2
        
        assert progress.remaining_students == 5
    
    def test_update_estimates(self):
        """Test time estimate updates."""
        progress = GradingProgress(total_students=10)
        progress.completed_students = 3
        progress.failed_students = 1
        
        processing_times = [2.0, 3.0, 2.5]
        progress.update_estimates(processing_times)
        
        assert progress.average_processing_time == 2.5
        assert progress.estimated_completion_time is not None


class TestSequentialGradingEngine:
    """Test SequentialGradingEngine class."""
    
    def test_initialization(self, mock_llm_service):
        """Test engine initialization."""
        engine = SequentialGradingEngine(llm_service=mock_llm_service)
        
        assert engine.llm_service == mock_llm_service
        assert engine.is_cancelled is False
        assert engine.current_batch_id is None
        assert engine.student_statuses == []
        assert engine.progress is None
    
    def test_initialization_without_llm_service(self):
        """Test engine initialization without LLM service."""
        with patch('services.grading_engine.LLMService') as mock_llm_class:
            mock_instance = Mock()
            mock_llm_class.return_value = mock_instance
            
            engine = SequentialGradingEngine()
            
            assert engine.llm_service == mock_instance
            mock_llm_class.assert_called_once()
    
    def test_callback_setters(self, mock_llm_service):
        """Test callback setter methods."""
        engine = SequentialGradingEngine(llm_service=mock_llm_service)
        
        progress_callback = Mock()
        student_callback = Mock()
        error_callback = Mock()
        
        engine.set_progress_callback(progress_callback)
        engine.set_student_completed_callback(student_callback)
        engine.set_error_callback(error_callback)
        
        assert engine.progress_callback == progress_callback
        assert engine.student_completed_callback == student_callback
        assert engine.error_callback == error_callback
    
    def test_cancel_grading(self, mock_llm_service):
        """Test grading cancellation."""
        engine = SequentialGradingEngine(llm_service=mock_llm_service)
        
        assert engine.is_cancelled is False
        engine.cancel_grading()
        assert engine.is_cancelled is True
    
    def test_successful_sequential_grading(self, mock_llm_service, sample_students, sample_rubric):
        """Test successful sequential grading process."""
        engine = SequentialGradingEngine(llm_service=mock_llm_service)
        
        # Set up callbacks
        progress_updates = []
        student_completions = []
        
        def progress_callback(progress):
            progress_updates.append(progress.progress_percentage)
        
        def student_callback(status):
            student_completions.append(status.student.name)
        
        engine.set_progress_callback(progress_callback)
        engine.set_student_completed_callback(student_callback)
        
        # Execute grading
        results = engine.grade_students_sequential(
            students=sample_students,
            rubric=sample_rubric,
            model_type="gemini",
            grading_type=GradingType.DESCRIPTIVE
        )
        
        # Verify results
        assert len(results) == 3
        assert all(isinstance(result, GradingResult) for result in results)
        assert all(result.student_name in ["김철수", "이영희", "박민수"] for result in results)
        
        # Verify LLM service calls
        assert mock_llm_service.grade_student_sequential.call_count == 3
        
        # Verify progress tracking
        assert engine.progress.total_students == 3
        assert engine.progress.completed_students == 3
        assert engine.progress.failed_students == 0
        assert engine.progress.progress_percentage == 100.0
        
        # Verify callbacks were called
        assert len(progress_updates) > 0
        assert len(student_completions) == 3
        assert set(student_completions) == {"김철수", "이영희", "박민수"}
    
    def test_grading_with_failures_and_retries(self, mock_llm_service, sample_students, sample_rubric):
        """Test grading with failures and retry mechanism."""
        engine = SequentialGradingEngine(llm_service=mock_llm_service)
        
        # Mock service to fail first two attempts, succeed on third
        call_count = 0
        def mock_grade_with_failures(student, rubric, model_type, grading_type, references=None):
            nonlocal call_count
            call_count += 1
            
            if student.name == "이영희" and call_count <= 2:
                raise Exception("API timeout")
            
            # Success case
            result = GradingResult(
                student_name=student.name,
                student_class_number=student.class_number,
                grading_time_seconds=2.5,
                overall_feedback="좋은 답변입니다."
            )
            result.add_element_score("정확성", 4, 5, "정확한 내용입니다.")
            result.add_element_score("완성도", 3, 5, "조금 더 자세한 설명이 필요합니다.")
            return result
        
        mock_llm_service.grade_student_sequential.side_effect = mock_grade_with_failures
        
        # Execute grading with retries
        results = engine.grade_students_sequential(
            students=sample_students,
            rubric=sample_rubric,
            model_type="gemini",
            grading_type=GradingType.DESCRIPTIVE,
            max_retries=3
        )
        
        # Should succeed for all students (이영희 succeeds on 3rd attempt)
        assert len(results) == 3
        assert engine.progress.completed_students == 3
        assert engine.progress.failed_students == 0
        
        # Verify retry attempts were made
        assert mock_llm_service.grade_student_sequential.call_count > 3
    
    def test_grading_with_permanent_failures(self, mock_llm_service, sample_students, sample_rubric):
        """Test grading with permanent failures."""
        engine = SequentialGradingEngine(llm_service=mock_llm_service)
        
        # Mock service to always fail for one student
        def mock_grade_with_permanent_failure(student, rubric, model_type, grading_type, references=None):
            if student.name == "이영희":
                raise Exception("Permanent API failure")
            
            # Success for other students
            result = GradingResult(
                student_name=student.name,
                student_class_number=student.class_number,
                grading_time_seconds=2.5,
                overall_feedback="좋은 답변입니다."
            )
            result.add_element_score("정확성", 4, 5, "정확한 내용입니다.")
            result.add_element_score("완성도", 3, 5, "조금 더 자세한 설명이 필요합니다.")
            return result
        
        mock_llm_service.grade_student_sequential.side_effect = mock_grade_with_permanent_failure
        
        # Set up error callback
        errors = []
        def error_callback(message, exception):
            errors.append((message, str(exception)))
        
        engine.set_error_callback(error_callback)
        
        # Execute grading
        results = engine.grade_students_sequential(
            students=sample_students,
            rubric=sample_rubric,
            model_type="gemini",
            grading_type=GradingType.DESCRIPTIVE,
            max_retries=2
        )
        
        # Should succeed for 2 students, fail for 1
        assert len(results) == 2
        assert engine.progress.completed_students == 2
        assert engine.progress.failed_students == 1
        
        # Verify error callback was called
        assert len(errors) == 1
        assert "이영희" in errors[0][0]
    
    def test_grading_cancellation(self, mock_llm_service, sample_students, sample_rubric):
        """Test grading cancellation during process."""
        engine = SequentialGradingEngine(llm_service=mock_llm_service)
        
        # Mock service to succeed normally
        def mock_grade_normal(student, rubric, model_type, grading_type, references=None):
            result = GradingResult(
                student_name=student.name,
                student_class_number=student.class_number,
                grading_time_seconds=2.5,
                overall_feedback="좋은 답변입니다."
            )
            result.add_element_score("정확성", 4, 5, "정확한 내용입니다.")
            result.add_element_score("완성도", 3, 5, "조금 더 자세한 설명이 필요합니다.")
            return result
        
        mock_llm_service.grade_student_sequential.side_effect = mock_grade_normal
        
        # Cancel grading after first student by using a callback
        def progress_callback(progress):
            if progress.completed_students == 1:
                engine.cancel_grading()
        
        engine.set_progress_callback(progress_callback)
        
        # Execute grading
        results = engine.grade_students_sequential(
            students=sample_students,
            rubric=sample_rubric,
            model_type="gemini",
            grading_type=GradingType.DESCRIPTIVE
        )
        
        # Should complete first student, then cancel before processing others
        assert len(results) >= 1  # At least first student completed
        assert len(results) < 3   # Not all students completed
        assert engine.is_cancelled is True
    
    def test_grading_summary(self, mock_llm_service, sample_students, sample_rubric):
        """Test grading summary generation."""
        engine = SequentialGradingEngine(llm_service=mock_llm_service)
        
        # Execute grading
        results = engine.grade_students_sequential(
            students=sample_students,
            rubric=sample_rubric,
            model_type="gemini",
            grading_type=GradingType.DESCRIPTIVE
        )
        
        # Get summary
        summary = engine.get_grading_summary()
        
        # Verify summary structure
        assert "batch_id" in summary
        assert summary["total_students"] == 3
        assert summary["completed_students"] == 3
        assert summary["failed_students"] == 0
        assert summary["progress_percentage"] == 100.0
        assert summary["success_rate"] == 100.0
        assert "student_details" in summary
        assert len(summary["student_details"]) == 3
        
        # Verify student details
        for detail in summary["student_details"]:
            assert "student_name" in detail
            assert "status" in detail
            assert "total_score" in detail
            assert "percentage" in detail
    
    def test_retry_failed_students(self, mock_llm_service, sample_students, sample_rubric):
        """Test retry functionality for failed students."""
        engine = SequentialGradingEngine(llm_service=mock_llm_service)
        
        # Mock initial failure for one student
        initial_call = True
        def mock_grade_with_initial_failure(student, rubric, model_type, grading_type, references=None):
            nonlocal initial_call
            
            if student.name == "이영희" and initial_call:
                raise Exception("Initial failure")
            
            result = GradingResult(
                student_name=student.name,
                student_class_number=student.class_number,
                grading_time_seconds=2.5,
                overall_feedback="좋은 답변입니다."
            )
            result.add_element_score("정확성", 4, 5, "정확한 내용입니다.")
            result.add_element_score("완성도", 3, 5, "조금 더 자세한 설명이 필요합니다.")
            return result
        
        mock_llm_service.grade_student_sequential.side_effect = mock_grade_with_initial_failure
        
        # Initial grading (should have 1 failure)
        results = engine.grade_students_sequential(
            students=sample_students,
            rubric=sample_rubric,
            model_type="gemini",
            grading_type=GradingType.DESCRIPTIVE,
            max_retries=0  # No retries in initial run
        )
        
        assert len(results) == 2  # 2 successful, 1 failed
        assert engine.progress.failed_students == 1
        
        # Now allow retries to succeed
        initial_call = False
        
        # Retry failed students
        retry_results = engine.retry_failed_students(
            rubric=sample_rubric,
            model_type="gemini",
            grading_type=GradingType.DESCRIPTIVE,
            max_retries=2
        )
        
        assert len(retry_results) == 1  # 1 additional success
        assert engine.progress.completed_students == 3
        assert engine.progress.failed_students == 0
    
    def test_validation_setup(self, mock_llm_service, sample_students, sample_rubric):
        """Test grading setup validation."""
        engine = SequentialGradingEngine(llm_service=mock_llm_service)
        
        # Valid setup
        validation = engine.validate_grading_setup(
            students=sample_students,
            rubric=sample_rubric,
            model_type="gemini",
            grading_type=GradingType.DESCRIPTIVE
        )
        
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
        
        # Invalid setup - no students
        validation = engine.validate_grading_setup(
            students=[],
            rubric=sample_rubric,
            model_type="gemini",
            grading_type=GradingType.DESCRIPTIVE
        )
        
        assert validation["valid"] is False
        assert "No students provided" in validation["errors"][0]
        
        # Invalid setup - API not available
        mock_llm_service.validate_api_availability.return_value = {"gemini": False, "groq": True}
        
        validation = engine.validate_grading_setup(
            students=sample_students,
            rubric=sample_rubric,
            model_type="gemini",
            grading_type=GradingType.DESCRIPTIVE
        )
        
        assert validation["valid"] is False
        assert "Gemini API not available" in validation["errors"][0]
    
    def test_get_successful_results(self, mock_llm_service, sample_students, sample_rubric):
        """Test getting successful results."""
        engine = SequentialGradingEngine(llm_service=mock_llm_service)
        
        # Execute grading
        results = engine.grade_students_sequential(
            students=sample_students,
            rubric=sample_rubric,
            model_type="gemini",
            grading_type=GradingType.DESCRIPTIVE
        )
        
        # Get successful results
        successful_results = engine.get_successful_results()
        
        assert len(successful_results) == 3
        assert all(isinstance(result, GradingResult) for result in successful_results)
        assert successful_results == results
    
    def test_get_failed_students(self, mock_llm_service, sample_students, sample_rubric):
        """Test getting failed students."""
        engine = SequentialGradingEngine(llm_service=mock_llm_service)
        
        # Mock failure for one student
        def mock_grade_with_failure(student, rubric, model_type, grading_type, references=None):
            if student.name == "이영희":
                raise Exception("Grading failed")
            
            result = GradingResult(
                student_name=student.name,
                student_class_number=student.class_number,
                grading_time_seconds=2.5,
                overall_feedback="좋은 답변입니다."
            )
            result.add_element_score("정확성", 4, 5, "정확한 내용입니다.")
            result.add_element_score("완성도", 3, 5, "조금 더 자세한 설명이 필요합니다.")
            return result
        
        mock_llm_service.grade_student_sequential.side_effect = mock_grade_with_failure
        
        # Execute grading
        results = engine.grade_students_sequential(
            students=sample_students,
            rubric=sample_rubric,
            model_type="gemini",
            grading_type=GradingType.DESCRIPTIVE,
            max_retries=0
        )
        
        # Get failed students
        failed_students = engine.get_failed_students()
        
        assert len(failed_students) == 1
        assert failed_students[0].student.name == "이영희"
        assert failed_students[0].status == GradingStatus.FAILED


if __name__ == "__main__":
    pytest.main([__file__])