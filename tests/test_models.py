"""
Tests for data models in the geography auto-grading system.
"""
import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime

from models import Student, EvaluationCriteria, EvaluationElement, Rubric, ElementScore, GradingResult, GradingTimer


class TestStudent:
    """Test cases for Student model."""
    
    def test_valid_student_with_text_answer(self):
        """Test creating a valid student with text answer."""
        student = Student(
            name="홍길동",
            class_number="1-1",
            answer="한국의 수도는 서울입니다."
        )
        
        assert student.name == "홍길동"
        assert student.class_number == "1-1"
        assert student.has_text_answer is True
        assert student.has_image_answer is False
        assert student.answer_type == "text"
    
    def test_valid_student_with_image_answer(self):
        """Test creating a valid student with image answer."""
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(b'fake image data')
            image_path = tmp_file.name
        
        try:
            student = Student(
                name="김철수",
                class_number="2-3",
                image_path=image_path
            )
            
            assert student.name == "김철수"
            assert student.has_text_answer is False
            assert student.has_image_answer is True
            assert student.answer_type == "image"
        finally:
            os.unlink(image_path)
    
    def test_student_validation_empty_name(self):
        """Test validation fails for empty name."""
        with pytest.raises(ValueError, match="Student name cannot be empty"):
            Student(name="", class_number="1-1", answer="답변")
    
    def test_student_validation_empty_class_number(self):
        """Test validation fails for empty class number."""
        with pytest.raises(ValueError, match="Class number cannot be empty"):
            Student(name="홍길동", class_number="", answer="답변")
    
    def test_student_validation_no_answer(self):
        """Test validation fails when no answer provided."""
        with pytest.raises(ValueError, match="Student must have either text answer or image path"):
            Student(name="홍길동", class_number="1-1")
    
    def test_student_validation_invalid_image_path(self):
        """Test validation fails for non-existent image file."""
        with pytest.raises(ValueError, match="Image file does not exist"):
            Student(
                name="홍길동",
                class_number="1-1",
                image_path="/non/existent/path.jpg"
            )


class TestEvaluationCriteria:
    """Test cases for EvaluationCriteria model."""
    
    def test_valid_criteria(self):
        """Test creating valid evaluation criteria."""
        criteria = EvaluationCriteria(score=5, description="완벽한 답변")
        
        assert criteria.score == 5
        assert criteria.description == "완벽한 답변"
    
    def test_criteria_validation_negative_score(self):
        """Test validation fails for negative score."""
        with pytest.raises(ValueError, match="Score cannot be negative"):
            EvaluationCriteria(score=-1, description="설명")
    
    def test_criteria_validation_empty_description(self):
        """Test validation fails for empty description."""
        with pytest.raises(ValueError, match="Criteria description cannot be empty"):
            EvaluationCriteria(score=5, description="")


class TestEvaluationElement:
    """Test cases for EvaluationElement model."""
    
    def test_valid_element(self):
        """Test creating valid evaluation element."""
        criteria1 = EvaluationCriteria(score=5, description="완벽")
        criteria2 = EvaluationCriteria(score=3, description="보통")
        
        element = EvaluationElement(
            name="내용 정확성",
            criteria=[criteria1, criteria2]
        )
        
        assert element.name == "내용 정확성"
        assert len(element.criteria) == 2
        assert element.max_score == 5
    
    def test_element_add_criteria(self):
        """Test adding criteria to element."""
        element = EvaluationElement(
            name="표현력",
            criteria=[EvaluationCriteria(score=3, description="기본")]
        )
        
        element.add_criteria(score=5, description="우수")
        
        assert len(element.criteria) == 2
        assert element.max_score == 5
    
    def test_element_validation_empty_name(self):
        """Test validation fails for empty element name."""
        with pytest.raises(ValueError, match="Evaluation element name cannot be empty"):
            EvaluationElement(name="", criteria=[])
    
    def test_element_validation_no_criteria(self):
        """Test element can be created with no criteria initially."""
        element = EvaluationElement(name="테스트", criteria=[])
        assert element.name == "테스트"
        assert len(element.criteria) == 0
        assert element.max_score == 0


class TestRubric:
    """Test cases for Rubric model."""
    
    def test_valid_rubric(self):
        """Test creating valid rubric."""
        element1 = EvaluationElement(
            name="내용",
            criteria=[EvaluationCriteria(score=10, description="완벽")]
        )
        element2 = EvaluationElement(
            name="표현",
            criteria=[EvaluationCriteria(score=5, description="우수")]
        )
        
        rubric = Rubric(
            name="지리 서술형 평가",
            elements=[element1, element2]
        )
        
        assert rubric.name == "지리 서술형 평가"
        assert len(rubric.elements) == 2
        assert rubric.total_max_score == 15
    
    def test_rubric_to_dict_and_from_dict(self):
        """Test converting rubric to/from dictionary."""
        element = EvaluationElement(
            name="정확성",
            criteria=[
                EvaluationCriteria(score=5, description="완벽"),
                EvaluationCriteria(score=3, description="보통")
            ]
        )
        
        original_rubric = Rubric(name="테스트 루브릭", elements=[element])
        
        # Convert to dict and back
        rubric_dict = original_rubric.to_dict()
        restored_rubric = Rubric.from_dict(rubric_dict)
        
        assert restored_rubric.name == original_rubric.name
        assert len(restored_rubric.elements) == len(original_rubric.elements)
        assert restored_rubric.total_max_score == original_rubric.total_max_score


class TestElementScore:
    """Test cases for ElementScore model."""
    
    def test_valid_element_score(self):
        """Test creating valid element score."""
        score = ElementScore(
            element_name="내용 정확성",
            score=8,
            max_score=10,
            feedback="좋은 답변입니다."
        )
        
        assert score.element_name == "내용 정확성"
        assert score.score == 8
        assert score.max_score == 10
        assert score.percentage == 80.0
    
    def test_element_score_validation_score_exceeds_max(self):
        """Test validation fails when score exceeds max score."""
        with pytest.raises(ValueError, match="Score cannot exceed max score"):
            ElementScore(
                element_name="테스트",
                score=15,
                max_score=10
            )


class TestGradingResult:
    """Test cases for GradingResult model."""
    
    def test_valid_grading_result(self):
        """Test creating valid grading result."""
        result = GradingResult(
            student_name="홍길동",
            student_class_number="1-1"
        )
        
        result.add_element_score("내용", 8, 10, "좋습니다")
        result.add_element_score("표현", 4, 5, "우수합니다")
        
        assert result.student_name == "홍길동"
        assert result.total_score == 12
        assert result.total_max_score == 15
        assert result.percentage == 80.0
        assert result.grade_letter == "B"
    
    def test_grading_result_to_dict_and_from_dict(self):
        """Test converting grading result to/from dictionary."""
        original_result = GradingResult(
            student_name="김철수",
            student_class_number="2-3",
            grading_time_seconds=1.5
        )
        original_result.add_element_score("내용", 9, 10)
        
        # Convert to dict and back
        result_dict = original_result.to_dict()
        restored_result = GradingResult.from_dict(result_dict)
        
        assert restored_result.student_name == original_result.student_name
        assert restored_result.total_score == original_result.total_score
        assert restored_result.grading_time_seconds == original_result.grading_time_seconds


class TestGradingTimer:
    """Test cases for GradingTimer."""
    
    def test_timer_context_manager(self):
        """Test timer as context manager."""
        import time
        
        with GradingTimer() as timer:
            time.sleep(0.1)  # Sleep for 100ms
        
        assert timer.elapsed_time >= 0.1
        assert timer.elapsed_time < 0.2  # Should be close to 0.1
    
    def test_timer_manual_start_stop(self):
        """Test manual timer start/stop."""
        import time
        
        timer = GradingTimer()
        timer.start()
        time.sleep(0.05)  # Sleep for 50ms
        elapsed = timer.stop()
        
        assert elapsed >= 0.05
        assert elapsed < 0.1
        assert timer.elapsed_time == elapsed