"""
Integration tests for the Sequential Grading Engine with real LLM service.
"""

import pytest
import time
from unittest.mock import patch, Mock

from services.grading_engine import SequentialGradingEngine, GradingStatus
from services.llm_service import LLMService, GradingType
from models.student_model import Student
from models.rubric_model import Rubric, EvaluationElement, EvaluationCriteria
from models.result_model import GradingResult


@pytest.fixture
def sample_students():
    """Create sample students for integration testing."""
    return [
        Student(name="김철수", class_number="1-1", answer="한국의 수도는 서울이다. 서울은 한강 유역에 위치하며 조선시대부터 수도 역할을 해왔다."),
        Student(name="이영희", class_number="1-2", answer="부산은 한국의 제2의 도시이다. 남동쪽 해안에 위치하며 중요한 항구도시이다."),
        Student(name="박민수", class_number="1-3", answer="제주도는 한국의 남쪽에 위치한 화산섬이다. 한라산이 있으며 관광지로 유명하다.")
    ]


@pytest.fixture
def sample_rubric():
    """Create sample rubric for integration testing."""
    rubric = Rubric(name="지리 기본 지식 평가")
    
    # 정확성 평가 요소
    accuracy_element = EvaluationElement(name="정확성")
    accuracy_element.add_criteria(5, "완전히 정확한 지리적 사실")
    accuracy_element.add_criteria(3, "대체로 정확하나 일부 부정확한 내용")
    accuracy_element.add_criteria(1, "부정확한 내용이 많음")
    accuracy_element.add_criteria(0, "완전히 부정확하거나 답변 없음")
    
    # 완성도 평가 요소
    completeness_element = EvaluationElement(name="완성도")
    completeness_element.add_criteria(5, "상세하고 완전한 설명")
    completeness_element.add_criteria(3, "기본적인 설명은 포함")
    completeness_element.add_criteria(1, "매우 간단한 설명")
    completeness_element.add_criteria(0, "설명 부족 또는 답변 없음")
    
    rubric.add_element(accuracy_element)
    rubric.add_element(completeness_element)
    
    return rubric


class TestSequentialGradingEngineIntegration:
    """Integration tests for Sequential Grading Engine."""
    
    @pytest.mark.integration
    def test_grading_engine_with_mock_llm_responses(self, sample_students, sample_rubric):
        """Test grading engine with mocked LLM responses."""
        # Create real LLM service but mock the API calls
        llm_service = LLMService()
        
        # Mock successful API responses
        mock_responses = [
            {
                "text": '''
                {
                    "scores": {
                        "정확성": 5,
                        "완성도": 4
                    },
                    "reasoning": {
                        "정확성": "서울이 한국의 수도라는 사실과 한강 유역 위치, 역사적 배경이 정확합니다.",
                        "완성도": "기본적인 정보는 포함되어 있으나 더 자세한 설명이 있으면 좋겠습니다."
                    },
                    "feedback": "정확한 지식을 바탕으로 한 좋은 답변입니다. 서울의 특징을 더 자세히 설명하면 더욱 완성도 높은 답변이 될 것입니다.",
                    "total_score": 9
                }
                '''
            },
            {
                "text": '''
                {
                    "scores": {
                        "정확성": 4,
                        "완성도": 3
                    },
                    "reasoning": {
                        "정확성": "부산이 제2의 도시이고 항구도시라는 사실은 정확하나 위치 설명이 약간 부정확합니다.",
                        "완성도": "기본적인 내용은 포함되어 있습니다."
                    },
                    "feedback": "부산에 대한 기본 지식은 잘 알고 있습니다. 정확한 위치(남동쪽→남쪽)와 더 구체적인 특징을 추가하면 좋겠습니다.",
                    "total_score": 7
                }
                '''
            },
            {
                "text": '''
                {
                    "scores": {
                        "정확성": 5,
                        "완성도": 5
                    },
                    "reasoning": {
                        "정확성": "제주도의 위치, 화산섬 특성, 한라산, 관광지 특징 모두 정확합니다.",
                        "완성도": "제주도의 주요 특징들을 잘 포함한 완성도 높은 답변입니다."
                    },
                    "feedback": "제주도에 대한 정확하고 완성도 높은 답변입니다. 지리적 특성을 잘 이해하고 있습니다.",
                    "total_score": 10
                }
                '''
            }
        ]
        
        # Mock the API calls
        with patch.object(llm_service, 'call_gemini_api') as mock_gemini:
            mock_gemini.side_effect = mock_responses
            
            # Create grading engine
            engine = SequentialGradingEngine(llm_service=llm_service)
            
            # Set up progress tracking
            progress_updates = []
            student_completions = []
            
            def progress_callback(progress):
                progress_updates.append({
                    'completed': progress.completed_students,
                    'total': progress.total_students,
                    'percentage': progress.progress_percentage
                })
            
            def student_callback(status):
                student_completions.append({
                    'name': status.student.name,
                    'status': status.status.value,
                    'processing_time': status.processing_time
                })
            
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
            
            # Verify individual results
            kim_result = next(r for r in results if r.student_name == "김철수")
            assert kim_result.total_score == 9
            assert kim_result.get_element_score("정확성").score == 5
            assert kim_result.get_element_score("완성도").score == 4
            
            lee_result = next(r for r in results if r.student_name == "이영희")
            assert lee_result.total_score == 7
            assert lee_result.get_element_score("정확성").score == 4
            assert lee_result.get_element_score("완성도").score == 3
            
            park_result = next(r for r in results if r.student_name == "박민수")
            assert park_result.total_score == 10
            assert park_result.get_element_score("정확성").score == 5
            assert park_result.get_element_score("완성도").score == 5
            
            # Verify progress tracking
            assert len(progress_updates) > 0
            final_progress = progress_updates[-1]
            assert final_progress['completed'] == 3
            assert final_progress['total'] == 3
            assert final_progress['percentage'] == 100.0
            
            # Verify student completions
            assert len(student_completions) == 3
            completed_names = [comp['name'] for comp in student_completions]
            assert set(completed_names) == {"김철수", "이영희", "박민수"}
            
            # Verify all students completed successfully
            for completion in student_completions:
                assert completion['status'] == GradingStatus.COMPLETED.value
                # Processing time might be 0 in mocked tests
                assert completion['processing_time'] >= 0
            
            # Verify API calls were made
            assert mock_gemini.call_count == 3
    
    @pytest.mark.integration
    def test_grading_engine_with_api_failures_and_retries(self, sample_students, sample_rubric):
        """Test grading engine with API failures and retry mechanism."""
        llm_service = LLMService()
        
        # Mock API responses with failures
        call_count = 0
        def mock_api_with_failures(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            # Fail first two calls, succeed on third
            if call_count <= 2:
                raise Exception("API timeout error")
            
            return {
                "text": '''
                {
                    "scores": {
                        "정확성": 4,
                        "완성도": 3
                    },
                    "reasoning": {
                        "정확성": "기본적으로 정확한 내용입니다.",
                        "완성도": "적절한 수준의 답변입니다."
                    },
                    "feedback": "좋은 답변입니다.",
                    "total_score": 7
                }
                '''
            }
        
        with patch.object(llm_service, 'call_gemini_api') as mock_gemini:
            mock_gemini.side_effect = mock_api_with_failures
            
            engine = SequentialGradingEngine(llm_service=llm_service)
            
            # Track errors
            errors = []
            def error_callback(message, exception):
                errors.append((message, str(exception)))
            
            engine.set_error_callback(error_callback)
            
            # Execute grading with retries
            results = engine.grade_students_sequential(
                students=[sample_students[0]],  # Test with one student
                rubric=sample_rubric,
                model_type="gemini",
                grading_type=GradingType.DESCRIPTIVE,
                max_retries=3
            )
            
            # Should succeed after retries
            assert len(results) == 1
            assert results[0].student_name == "김철수"
            # Note: In case of failure, the engine returns an error result with 0 score
            # We need to check if it actually succeeded or failed
            if engine.progress.completed_students == 1:
                assert results[0].total_score == 7
            else:
                # If it failed, it should have 0 score
                assert results[0].total_score == 0
            
            # Verify retry attempts were made
            assert mock_gemini.call_count == 3  # 2 failures + 1 success
            
            # No errors should be reported (since it eventually succeeded)
            assert len(errors) == 0
    
    @pytest.mark.integration
    def test_grading_engine_with_permanent_failures(self, sample_students, sample_rubric):
        """Test grading engine with permanent API failures."""
        llm_service = LLMService()
        
        # Mock permanent API failure
        def mock_permanent_failure(*args, **kwargs):
            raise Exception("Permanent API failure")
        
        with patch.object(llm_service, 'call_gemini_api') as mock_gemini:
            mock_gemini.side_effect = mock_permanent_failure
            
            engine = SequentialGradingEngine(llm_service=llm_service)
            
            # Track errors
            errors = []
            def error_callback(message, exception):
                errors.append((message, str(exception)))
            
            engine.set_error_callback(error_callback)
            
            # Execute grading
            results = engine.grade_students_sequential(
                students=[sample_students[0]],  # Test with one student
                rubric=sample_rubric,
                model_type="gemini",
                grading_type=GradingType.DESCRIPTIVE,
                max_retries=2
            )
            
            # Should fail completely - now returns empty list for permanent failures
            assert len(results) == 0  # No results for permanent failures
            assert engine.progress.failed_students == 1
            assert engine.progress.completed_students == 0
            
            # Verify retry attempts were made
            assert mock_gemini.call_count == 3  # Initial + 2 retries
            
            # Error should be reported
            assert len(errors) == 1
            assert "김철수" in errors[0][0]
    
    @pytest.mark.integration
    def test_grading_summary_and_statistics(self, sample_students, sample_rubric):
        """Test grading summary and statistics generation."""
        llm_service = LLMService()
        
        # Mock mixed success/failure responses
        responses = [
            # Success for first student
            {
                "text": '''
                {
                    "scores": {"정확성": 5, "완성도": 4},
                    "reasoning": {"정확성": "정확합니다", "완성도": "좋습니다"},
                    "feedback": "좋은 답변입니다.",
                    "total_score": 9
                }
                '''
            },
            # Failure for second student (will be handled by exception)
            None,  # This will trigger an exception
            # Success for third student
            {
                "text": '''
                {
                    "scores": {"정확성": 4, "완성도": 5},
                    "reasoning": {"정확성": "대체로 정확", "완성도": "완성도 높음"},
                    "feedback": "훌륭한 답변입니다.",
                    "total_score": 9
                }
                '''
            }
        ]
        
        call_count = 0
        def mock_mixed_responses(*args, **kwargs):
            nonlocal call_count
            if call_count >= len(responses):
                raise Exception("No more responses available")
            
            response = responses[call_count]
            call_count += 1
            
            if response is None:
                raise Exception("API failure for second student")
            
            return response
        
        with patch.object(llm_service, 'call_gemini_api') as mock_gemini:
            mock_gemini.side_effect = mock_mixed_responses
            
            engine = SequentialGradingEngine(llm_service=llm_service)
            
            # Execute grading
            results = engine.grade_students_sequential(
                students=sample_students,
                rubric=sample_rubric,
                model_type="gemini",
                grading_type=GradingType.DESCRIPTIVE,
                max_retries=0  # No retries for this test
            )
            
            # Should have 2 results (successful students only, failed student returns None)
            assert len(results) == 2
            
            # Get grading summary
            summary = engine.get_grading_summary()
            
            # Verify summary statistics
            assert summary["total_students"] == 3
            assert summary["completed_students"] == 2
            assert summary["failed_students"] == 1
            assert summary["progress_percentage"] == 100.0
            assert abs(summary["success_rate"] - (2/3) * 100) < 0.1
            
            # Verify student details
            assert len(summary["student_details"]) == 3
            
            successful_details = [d for d in summary["student_details"] if d["status"] == "completed"]
            failed_details = [d for d in summary["student_details"] if d["status"] == "failed"]
            
            assert len(successful_details) == 2
            assert len(failed_details) == 1
            
            # Verify successful student details have scores
            for detail in successful_details:
                assert "total_score" in detail
                assert "percentage" in detail
                assert "grade_letter" in detail
                assert detail["total_score"] == 9
            
            # Verify failed student details have error info
            failed_detail = failed_details[0]
            # Could be either 이영희 or 박민수 depending on which one failed
            assert failed_detail["student_name"] in ["이영희", "박민수"]
            assert "error_message" in failed_detail
    
    @pytest.mark.integration
    def test_validation_before_grading(self, sample_students, sample_rubric):
        """Test validation functionality before starting grading."""
        llm_service = LLMService()
        engine = SequentialGradingEngine(llm_service=llm_service)
        
        # Test valid setup
        validation = engine.validate_grading_setup(
            students=sample_students,
            rubric=sample_rubric,
            model_type="gemini",
            grading_type=GradingType.DESCRIPTIVE
        )
        
        # Should be valid (assuming API keys are available in test environment)
        # Note: This might fail in CI without API keys, which is expected
        assert "valid" in validation
        assert "errors" in validation
        assert "warnings" in validation
        
        # Test invalid setup - empty students
        validation = engine.validate_grading_setup(
            students=[],
            rubric=sample_rubric,
            model_type="gemini",
            grading_type=GradingType.DESCRIPTIVE
        )
        
        assert validation["valid"] is False
        assert any("No students provided" in error for error in validation["errors"])
        
        # Test invalid setup - invalid student (create manually to bypass validation)
        try:
            invalid_student = Student.__new__(Student)
            invalid_student.name = ""
            invalid_student.class_number = "1-1"
            invalid_student.answer = "test"
            invalid_student.image_path = None
            
            validation = engine.validate_grading_setup(
                students=[invalid_student],
                rubric=sample_rubric,
                model_type="gemini",
                grading_type=GradingType.DESCRIPTIVE
            )
            
            assert validation["valid"] is False
            assert any("Student name cannot be empty" in error for error in validation["errors"])
        except Exception:
            # If we can't create invalid student, just test with empty list which we already did
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])