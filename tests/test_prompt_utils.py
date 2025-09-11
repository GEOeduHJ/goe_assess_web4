"""
Unit tests for prompt utilities module.
"""

import pytest
import json

from utils.prompt_utils import (
    format_references, format_rubric, generate_json_fields,
    clean_text, validate_prompt_length, extract_json_from_response,
    validate_response_structure, create_fallback_response,
    optimize_prompt_for_model, estimate_token_count, truncate_prompt_if_needed
)
from models.rubric_model import Rubric, EvaluationElement, EvaluationCriteria


class TestPromptUtils:
    """Test cases for prompt utility functions."""
    
    @pytest.fixture
    def sample_rubric(self):
        """Create a sample rubric for testing."""
        rubric = Rubric(name="테스트 루브릭")
        
        element1 = EvaluationElement(name="이해도")
        element1.add_criteria(5, "완전히 이해함")
        element1.add_criteria(3, "부분적으로 이해함")
        element1.add_criteria(0, "이해하지 못함")
        
        element2 = EvaluationElement(name="적용능력")
        element2.add_criteria(5, "정확하게 적용함")
        element2.add_criteria(3, "대체로 적용함")
        element2.add_criteria(0, "적용하지 못함")
        
        rubric.add_element(element1)
        rubric.add_element(element2)
        
        return rubric
    
    def test_format_references(self):
        """Test reference formatting."""
        references = ["첫 번째 참고자료", "두 번째 참고자료"]
        formatted = format_references(references)
        
        assert "참고자료 1: 첫 번째 참고자료" in formatted
        assert "참고자료 2: 두 번째 참고자료" in formatted
    
    def test_format_references_empty(self):
        """Test reference formatting with empty list."""
        formatted = format_references([])
        assert formatted == ""
        
        formatted = format_references(None)
        assert formatted == ""
    
    def test_format_references_long_text(self):
        """Test reference formatting with long text."""
        long_ref = "a" * 600  # Longer than 500 chars
        formatted = format_references([long_ref])
        
        assert "..." in formatted
        assert len(formatted) < len(long_ref) + 50  # Should be truncated
    
    def test_format_rubric(self, sample_rubric):
        """Test rubric formatting."""
        formatted = format_rubric(sample_rubric)
        
        assert "평가요소: 이해도" in formatted
        assert "평가요소: 적용능력" in formatted
        assert "5점: 완전히 이해함" in formatted
        assert "3점: 부분적으로 이해함" in formatted
        assert "0점: 이해하지 못함" in formatted
    
    def test_generate_json_fields(self, sample_rubric):
        """Test JSON field generation."""
        score_fields, reasoning_fields = generate_json_fields(sample_rubric)
        
        assert '"이해도": 점수' in score_fields
        assert '"적용능력": 점수' in score_fields
        assert '"이해도": "점수 부여 근거"' in reasoning_fields
        assert '"적용능력": "점수 부여 근거"' in reasoning_fields
    
    def test_clean_text(self):
        """Test text cleaning."""
        dirty_text = '  이것은\n\t"더러운"\r텍스트입니다...  '
        clean = clean_text(dirty_text)
        
        assert clean == "이것은 더러운 텍스트입니다."
        assert "\n" not in clean
        assert "\t" not in clean
        assert '"' not in clean
    
    def test_clean_text_empty(self):
        """Test text cleaning with empty input."""
        assert clean_text("") == ""
        assert clean_text(None) == ""
    
    def test_validate_prompt_length(self):
        """Test prompt length validation."""
        short_prompt = "짧은 프롬프트"
        long_prompt = "a" * 10000
        
        assert validate_prompt_length(short_prompt) is True
        assert validate_prompt_length(long_prompt) is False
        assert validate_prompt_length(long_prompt, max_length=15000) is True
    
    def test_extract_json_from_response(self):
        """Test JSON extraction from response."""
        response_with_json = '''
        여기는 추가 텍스트입니다.
        {
            "scores": {"이해도": 5},
            "reasoning": {"이해도": "완벽함"},
            "feedback": "잘했습니다",
            "total_score": 5
        }
        여기도 추가 텍스트입니다.
        '''
        
        json_str = extract_json_from_response(response_with_json)
        assert json_str is not None
        
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["scores"]["이해도"] == 5
    
    def test_extract_json_from_response_no_json(self):
        """Test JSON extraction when no JSON present."""
        response_no_json = "이것은 JSON이 없는 응답입니다."
        json_str = extract_json_from_response(response_no_json)
        assert json_str is None
    
    def test_validate_response_structure_valid(self, sample_rubric):
        """Test response structure validation with valid response."""
        valid_response = {
            "scores": {"이해도": 5, "적용능력": 3},
            "reasoning": {"이해도": "완벽함", "적용능력": "보통"},
            "feedback": "잘했습니다",
            "total_score": 8
        }
        
        errors = validate_response_structure(valid_response, sample_rubric)
        
        # Should have no errors
        assert all(len(error_list) == 0 for error_list in errors.values())
    
    def test_validate_response_structure_missing_fields(self, sample_rubric):
        """Test response structure validation with missing fields."""
        invalid_response = {
            "scores": {"이해도": 5}
            # Missing reasoning, feedback, total_score
        }
        
        errors = validate_response_structure(invalid_response, sample_rubric)
        
        assert len(errors["missing_fields"]) > 0
        assert "reasoning" in errors["missing_fields"]
        assert "feedback" in errors["missing_fields"]
        assert "total_score" in errors["missing_fields"]
    
    def test_validate_response_structure_invalid_scores(self, sample_rubric):
        """Test response structure validation with invalid scores."""
        invalid_response = {
            "scores": {"이해도": 7, "적용능력": "invalid"},  # 7 not in rubric, string score
            "reasoning": {"이해도": "완벽함", "적용능력": "보통"},
            "feedback": "잘했습니다",
            "total_score": 8
        }
        
        errors = validate_response_structure(invalid_response, sample_rubric)
        
        assert len(errors["invalid_scores"]) > 0
        assert len(errors["type_errors"]) > 0
    
    def test_create_fallback_response(self, sample_rubric):
        """Test fallback response creation."""
        error_msg = "API 오류"
        fallback = create_fallback_response(sample_rubric, error_msg)
        
        assert fallback["scores"]["이해도"] == 0
        assert fallback["scores"]["적용능력"] == 0
        assert error_msg in fallback["reasoning"]["이해도"]
        assert error_msg in fallback["feedback"]
        assert fallback["total_score"] == 0
    
    def test_optimize_prompt_for_model(self):
        """Test prompt optimization for different models."""
        base_prompt = "기본 프롬프트입니다."
        
        gemini_prompt = optimize_prompt_for_model(base_prompt, "gemini")
        groq_prompt = optimize_prompt_for_model(base_prompt, "groq")
        
        assert gemini_prompt == base_prompt  # No change for Gemini
        assert len(groq_prompt) > len(base_prompt)  # Additional instructions for Groq
        assert "JSON" in groq_prompt
    
    def test_estimate_token_count(self):
        """Test token count estimation."""
        text = "이것은 테스트 텍스트입니다."
        tokens = estimate_token_count(text)
        
        assert tokens > 0
        assert tokens == len(text) // 4  # Rough estimation
    
    def test_truncate_prompt_if_needed(self):
        """Test prompt truncation."""
        short_prompt = "짧은 프롬프트"
        long_prompt = "a" * 30000  # Very long prompt
        
        # Short prompt should not be truncated
        result_short = truncate_prompt_if_needed(short_prompt, max_tokens=1000)
        assert result_short == short_prompt
        
        # Long prompt should be truncated
        result_long = truncate_prompt_if_needed(long_prompt, max_tokens=1000)
        assert len(result_long) < len(long_prompt)
        assert "생략되었습니다" in result_long
        