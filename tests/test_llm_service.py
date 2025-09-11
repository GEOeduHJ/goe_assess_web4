"""
Unit tests for LLM Service module.
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from services.llm_service import LLMService, LLMModelType, GradingType
from models.student_model import Student
from models.rubric_model import Rubric, EvaluationElement, EvaluationCriteria
from models.result_model import GradingResult


class TestLLMService:
    """Test cases for LLMService class."""
    
    @pytest.fixture
    def sample_rubric(self):
        """Create a sample rubric for testing."""
        rubric = Rubric(name="지리 서술형 평가")
        
        # Element 1: 개념 이해
        element1 = EvaluationElement(name="개념 이해")
        element1.add_criteria(5, "개념을 정확하고 완전하게 이해하고 설명함")
        element1.add_criteria(3, "개념을 대체로 이해하고 설명함")
        element1.add_criteria(1, "개념을 부분적으로 이해함")
        element1.add_criteria(0, "개념을 이해하지 못함")
        
        # Element 2: 사례 적용
        element2 = EvaluationElement(name="사례 적용")
        element2.add_criteria(5, "적절한 사례를 들어 정확하게 설명함")
        element2.add_criteria(3, "사례를 들어 설명하나 일부 부정확함")
        element2.add_criteria(1, "사례를 들었으나 부적절함")
        element2.add_criteria(0, "사례를 들지 못함")
        
        rubric.add_element(element1)
        rubric.add_element(element2)
        
        return rubric
    
    @pytest.fixture
    def sample_student(self):
        """Create a sample student for testing."""
        return Student(
            name="김지리",
            class_number="1-1",
            answer="기후변화는 지구 온난화로 인해 발생하는 현상입니다. 예를 들어 북극의 빙하가 녹고 있습니다."
        )
    
    @pytest.fixture
    def sample_student_with_image(self, tmp_path):
        """Create a sample student with image for testing."""
        # Create a dummy image file
        image_path = tmp_path / "student_map.jpg"
        image_path.write_bytes(b"dummy image content")
        
        return Student(
            name="박지도",
            class_number="1-2",
            answer="",
            image_path=str(image_path)
        )
    
    @pytest.fixture
    def llm_service(self):
        """Create LLM service instance for testing."""
        with patch('services.llm_service.config') as mock_config:
            mock_config.GOOGLE_API_KEY = "test_google_key"
            mock_config.GROQ_API_KEY = "test_groq_key"
            mock_config.MAX_RETRIES = 3
            mock_config.RETRY_DELAY = 1
            
            with patch('google.generativeai.configure'), \
                 patch('google.generativeai.GenerativeModel') as mock_gemini, \
                 patch('groq.Groq') as mock_groq:
                
                service = LLMService()
                service.gemini_client = Mock()
                service.groq_client = Mock()
                return service
    
    def test_initialization(self):
        """Test LLM service initialization."""
        with patch('services.llm_service.config') as mock_config:
            mock_config.GOOGLE_API_KEY = "test_key"
            mock_config.GROQ_API_KEY = "test_key"
            
            with patch('google.generativeai.configure'), \
                 patch('google.generativeai.GenerativeModel'), \
                 patch('groq.Groq'):
                
                service = LLMService()
                assert service.gemini_client is not None
                assert service.groq_client is not None
    
    def test_model_selection_descriptive(self, llm_service):
        """Test model selection for descriptive grading."""
        # Test Gemini selection
        model = llm_service.select_model(LLMModelType.GEMINI, GradingType.DESCRIPTIVE)
        assert model == LLMModelType.GEMINI
        
        # Test Groq selection
        model = llm_service.select_model(LLMModelType.GROQ, GradingType.DESCRIPTIVE)
        assert model == LLMModelType.GROQ
    
    def test_model_selection_map(self, llm_service):
        """Test model selection for map grading (only Gemini supported)."""
        model = llm_service.select_model(LLMModelType.GROQ, GradingType.MAP)
        assert model == LLMModelType.GEMINI  # Should fallback to Gemini
        
        model = llm_service.select_model(LLMModelType.GEMINI, GradingType.MAP)
        assert model == LLMModelType.GEMINI
    
    def test_model_selection_no_clients(self):
        """Test model selection when no clients are available."""
        service = LLMService()
        service.gemini_client = None
        service.groq_client = None
        
        with pytest.raises(ValueError, match="No LLM models available"):
            service.select_model(LLMModelType.GEMINI, GradingType.DESCRIPTIVE)
    
    def test_generate_prompt_descriptive(self, llm_service, sample_rubric):
        """Test prompt generation for descriptive grading."""
        references = ["참고자료 내용 1", "참고자료 내용 2"]
        student_answer = "학생의 답안입니다."
        
        prompt = llm_service.generate_prompt(
            rubric=sample_rubric,
            student_answer=student_answer,
            references=references,
            grading_type=GradingType.DESCRIPTIVE
        )
        
        # Check that all components are included
        assert "지리 교과목 전문 채점자" in prompt
        assert "참고자료 1: 참고자료 내용 1" in prompt
        assert "참고자료 2: 참고자료 내용 2" in prompt
        assert "개념 이해" in prompt
        assert "사례 적용" in prompt
        assert student_answer in prompt
        assert "JSON 형식" in prompt
    
    def test_generate_prompt_map(self, llm_service, sample_rubric):
        """Test prompt generation for map grading."""
        prompt = llm_service.generate_prompt(
            rubric=sample_rubric,
            grading_type=GradingType.MAP
        )
        
        # Check that map-specific content is included
        assert "백지도 답안" in prompt
        assert "이미지를 분석하여" in prompt
        assert "참고자료" not in prompt  # No references for map grading
        assert "JSON 형식" in prompt
    
    def test_call_gemini_api_success(self, llm_service):
        """Test successful Gemini API call."""
        # Mock successful response
        mock_response = Mock()
        mock_response.text = '{"scores": {"개념 이해": 5}, "reasoning": {"개념 이해": "완벽함"}, "feedback": "잘했습니다", "total_score": 5}'
        
        llm_service.gemini_client.generate_content.return_value = mock_response
        
        result = llm_service.call_gemini_api("test prompt")
        
        assert "text" in result
        assert "scores" in result["text"]
        llm_service.gemini_client.generate_content.assert_called_once()
    
    def test_call_gemini_api_with_image(self, llm_service, sample_student_with_image):
        """Test Gemini API call with image."""
        mock_response = Mock()
        mock_response.text = '{"scores": {"개념 이해": 3}, "reasoning": {"개념 이해": "보통"}, "feedback": "개선 필요", "total_score": 3}'
        
        llm_service.gemini_client.generate_content.return_value = mock_response
        
        result = llm_service.call_gemini_api("test prompt", sample_student_with_image.image_path)
        
        assert "text" in result
        llm_service.gemini_client.generate_content.assert_called_once()
        
        # Check that image was included in the call
        call_args = llm_service.gemini_client.generate_content.call_args[0][0]
        assert len(call_args) == 2  # prompt + image
    
    def test_call_groq_api_success(self, llm_service):
        """Test successful Groq API call."""
        # Mock successful response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"scores": {"개념 이해": 4}, "reasoning": {"개념 이해": "좋음"}, "feedback": "잘했습니다", "total_score": 4}'
        
        llm_service.groq_client.chat.completions.create.return_value = mock_response
        
        result = llm_service.call_groq_api("test prompt")
        
        assert "text" in result
        assert "scores" in result["text"]
        llm_service.groq_client.chat.completions.create.assert_called_once()
    
    def test_api_retry_mechanism(self, llm_service):
        """Test API retry mechanism on failure."""
        # Mock API to fail twice then succeed
        mock_response = Mock()
        mock_response.text = '{"scores": {"개념 이해": 5}, "reasoning": {"개념 이해": "완벽함"}, "feedback": "잘했습니다", "total_score": 5}'
        
        llm_service.gemini_client.generate_content.side_effect = [
            Exception("Network error"),
            Exception("Timeout"),
            mock_response
        ]
        
        with patch('time.sleep'):  # Speed up test
            result = llm_service.call_gemini_api("test prompt", max_retries=3)
        
        assert "text" in result
        assert llm_service.gemini_client.generate_content.call_count == 3
    
    def test_parse_response_success(self, llm_service, sample_rubric):
        """Test successful response parsing."""
        response_text = '''
        Here is the grading result:
        {
            "scores": {
                "개념 이해": 5,
                "사례 적용": 3
            },
            "reasoning": {
                "개념 이해": "완벽하게 이해함",
                "사례 적용": "적절한 사례 제시"
            },
            "feedback": "전반적으로 잘 작성되었습니다.",
            "total_score": 8
        }
        Additional text here.
        '''
        
        result = llm_service.parse_response(response_text, sample_rubric)
        
        assert result["scores"]["개념 이해"] == 5
        assert result["scores"]["사례 적용"] == 3
        assert "완벽하게 이해함" in result["reasoning"]["개념 이해"]
        assert result["total_score"] == 8
    
    def test_parse_response_invalid_json(self, llm_service, sample_rubric):
        """Test response parsing with invalid JSON."""
        response_text = "This is not JSON format"
        
        with pytest.raises(ValueError, match="No JSON found"):
            llm_service.parse_response(response_text, sample_rubric)
    
    def test_parse_response_missing_fields(self, llm_service, sample_rubric):
        """Test response parsing with missing required fields."""
        response_text = '{"scores": {"개념 이해": 5}}'  # Missing other fields
        
        with pytest.raises(ValueError, match="Missing required field"):
            llm_service.parse_response(response_text, sample_rubric)
    
    def test_grade_student_sequential_success(self, llm_service, sample_student, sample_rubric):
        """Test successful sequential grading of a student."""
        # Mock API response
        mock_response = {
            "text": '''
            {
                "scores": {
                    "개념 이해": 5,
                    "사례 적용": 3
                },
                "reasoning": {
                    "개념 이해": "개념을 정확하게 이해함",
                    "사례 적용": "적절한 사례를 제시함"
                },
                "feedback": "잘 작성되었습니다. 사례를 더 구체적으로 설명하면 좋겠습니다.",
                "total_score": 8
            }
            '''
        }
        
        llm_service.call_gemini_api = Mock(return_value=mock_response)
        
        result = llm_service.grade_student_sequential(
            student=sample_student,
            rubric=sample_rubric,
            model_type=LLMModelType.GEMINI,
            grading_type=GradingType.DESCRIPTIVE
        )
        
        assert isinstance(result, GradingResult)
        assert result.student_name == sample_student.name
        assert result.student_class_number == sample_student.class_number
        assert len(result.element_scores) == 2
        assert result.total_score == 8
        assert result.grading_time_seconds >= 0  # Should be non-negative
    
    def test_grade_student_sequential_error(self, llm_service, sample_student, sample_rubric):
        """Test sequential grading with API error."""
        # Mock API to raise exception
        llm_service.call_gemini_api = Mock(side_effect=Exception("API Error"))
        
        result = llm_service.grade_student_sequential(
            student=sample_student,
            rubric=sample_rubric,
            model_type=LLMModelType.GEMINI,
            grading_type=GradingType.DESCRIPTIVE
        )
        
        assert isinstance(result, GradingResult)
        assert result.student_name == sample_student.name
        assert result.total_score == 0  # Error result should have 0 score
        assert "오류가 발생했습니다" in result.overall_feedback
    
    def test_grade_students_batch(self, llm_service, sample_rubric):
        """Test batch grading of multiple students."""
        students = [
            Student(name="학생1", class_number="1-1", answer="답안1"),
            Student(name="학생2", class_number="1-2", answer="답안2")
        ]
        
        # Mock successful grading for each student
        def mock_grade_student(student, rubric, model_type, grading_type, references=None):
            return GradingResult(
                student_name=student.name,
                student_class_number=student.class_number,
                overall_feedback="테스트 피드백"
            )
        
        llm_service.grade_student_sequential = Mock(side_effect=mock_grade_student)
        
        # Mock progress callback
        progress_callback = Mock()
        
        results = llm_service.grade_students_batch(
            students=students,
            rubric=sample_rubric,
            model_type=LLMModelType.GEMINI,
            grading_type=GradingType.DESCRIPTIVE,
            progress_callback=progress_callback
        )
        
        assert len(results) == 2
        assert all(isinstance(r, GradingResult) for r in results)
        assert progress_callback.call_count == 2
        assert llm_service.grade_student_sequential.call_count == 2
    
    def test_validate_api_availability(self, llm_service):
        """Test API availability validation."""
        availability = llm_service.validate_api_availability()
        
        assert "gemini" in availability
        assert "groq" in availability
        assert availability["gemini"] is True  # Mocked as available
        assert availability["groq"] is True   # Mocked as available
    
    def test_validate_api_availability_no_clients(self):
        """Test API availability when clients are not initialized."""
        service = LLMService()
        service.gemini_client = None
        service.groq_client = None
        
        availability = service.validate_api_availability()
        
        assert availability["gemini"] is False
        assert availability["groq"] is False