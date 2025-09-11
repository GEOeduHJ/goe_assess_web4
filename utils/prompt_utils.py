"""
Prompt engineering utilities for the Geography Auto-Grading System.

This module provides utility functions for creating structured prompts,
validating responses, and handling prompt templates.
"""

import json
import re
from typing import Dict, List, Optional, Any
from models.rubric_model import Rubric, EvaluationElement


class PromptTemplate:
    """Template class for structured prompt generation."""
    
    # System role templates
    SYSTEM_ROLES = {
        "descriptive": "당신은 지리 교과목 전문 채점자입니다. 학생의 서술형 답안을 분석하여 채점해주세요.",
        "map": "당신은 지리 교과목 전문 채점자입니다. 학생이 작성한 백지도 답안을 분석하여 채점해주세요."
    }
    
    # Reference section template
    REFERENCE_TEMPLATE = """
다음은 채점 참고 자료입니다:
{references}
"""
    
    # Rubric section template
    RUBRIC_TEMPLATE = """
다음은 평가 루브릭입니다:
{rubric_details}
"""
    
    # Answer section templates
    ANSWER_TEMPLATES = {
        "descriptive": """
다음은 학생 답안입니다:
{student_answer}
""",
        "map": """
다음은 학생이 작성한 백지도 답안입니다. 이미지를 분석하여 채점해주세요.
"""
    }
    
    # Output format template
    OUTPUT_FORMAT_TEMPLATE = """
다음 JSON 형식으로 채점 결과를 제공해주세요:
{{
  "scores": {{
    {score_fields}
  }},
  "reasoning": {{
    {reasoning_fields}
  }},
  "feedback": "학생을 위한 개선 피드백",
  "total_score": 총점
}}

중요: 반드시 위의 JSON 형식을 정확히 따라주세요. 각 평가요소에 대해 루브릭에 명시된 점수만 부여하세요.
"""


def format_references(references: List[str]) -> str:
    """
    Format reference materials for prompt inclusion.
    
    Args:
        references: List of reference text chunks
        
    Returns:
        Formatted reference string
    """
    if not references:
        return ""
    
    formatted_refs = []
    for i, ref in enumerate(references, 1):
        # Clean and truncate reference if too long
        clean_ref = clean_text(ref)
        if len(clean_ref) > 500:
            clean_ref = clean_ref[:500] + "..."
        
        formatted_refs.append(f"참고자료 {i}: {clean_ref}")
    
    return "\n".join(formatted_refs)


def format_rubric(rubric: Rubric) -> str:
    """
    Format rubric for prompt inclusion.
    
    Args:
        rubric: Evaluation rubric
        
    Returns:
        Formatted rubric string
    """
    rubric_parts = []
    
    for element in rubric.elements:
        element_part = f"\n평가요소: {element.name} (최대 {element.max_score}점)"
        
        # Sort criteria by score (descending)
        sorted_criteria = sorted(element.criteria, key=lambda x: x.score, reverse=True)
        
        for criteria in sorted_criteria:
            element_part += f"\n  {criteria.score}점: {criteria.description}"
        
        rubric_parts.append(element_part)
    
    return "\n".join(rubric_parts)


def generate_json_fields(rubric: Rubric) -> tuple[str, str]:
    """
    Generate JSON field templates for scores and reasoning.
    
    Args:
        rubric: Evaluation rubric
        
    Returns:
        Tuple of (score_fields, reasoning_fields) strings
    """
    score_fields = []
    reasoning_fields = []
    
    for element in rubric.elements:
        score_fields.append(f'"{element.name}": 점수')
        reasoning_fields.append(f'"{element.name}": "점수 부여 근거"')
    
    return (
        ",\n    ".join(score_fields),
        ",\n    ".join(reasoning_fields)
    )


def clean_text(text: str) -> str:
    """
    Clean text for better prompt quality.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove special characters that might interfere with JSON
    text = re.sub(r'["\\\n\r\t]', ' ', text)
    
    # Remove multiple consecutive punctuation
    text = re.sub(r'[.,!?]{2,}', '.', text)
    
    return text.strip()


def validate_prompt_length(prompt: str, max_length: int = 8000) -> bool:
    """
    Validate that prompt is within acceptable length limits.
    
    Args:
        prompt: Generated prompt
        max_length: Maximum allowed length
        
    Returns:
        True if prompt is within limits
    """
    return len(prompt) <= max_length


def extract_json_from_response(response_text: str) -> Optional[str]:
    """
    Extract JSON content from LLM response.
    
    Args:
        response_text: Raw response from LLM
        
    Returns:
        Extracted JSON string or None if not found
    """
    if not response_text:
        return None
    
    # Try to find JSON block
    json_start = response_text.find('{')
    json_end = response_text.rfind('}') + 1
    
    if json_start == -1 or json_end == 0:
        return None
    
    return response_text[json_start:json_end]


def validate_response_structure(response_dict: Dict[str, Any], rubric: Rubric) -> Dict[str, List[str]]:
    """
    Validate the structure of parsed response against rubric.
    
    Args:
        response_dict: Parsed response dictionary
        rubric: Evaluation rubric
        
    Returns:
        Dictionary with validation errors (empty if valid)
    """
    errors = {
        "missing_fields": [],
        "invalid_scores": [],
        "missing_reasoning": [],
        "type_errors": []
    }
    
    # Check required top-level fields
    required_fields = ['scores', 'reasoning', 'feedback', 'total_score']
    for field in required_fields:
        if field not in response_dict:
            errors["missing_fields"].append(field)
    
    if errors["missing_fields"]:
        return errors
    
    # Validate scores
    if not isinstance(response_dict['scores'], dict):
        errors["type_errors"].append("scores must be a dictionary")
    else:
        for element in rubric.elements:
            element_name = element.name
            
            # Check if score exists
            if element_name not in response_dict['scores']:
                errors["missing_fields"].append(f"score for {element_name}")
                continue
            
            score = response_dict['scores'][element_name]
            
            # Check score type
            if not isinstance(score, (int, float)):
                errors["type_errors"].append(f"score for {element_name} must be numeric")
                continue
            
            # Check if score is valid according to rubric
            valid_scores = [criteria.score for criteria in element.criteria]
            if score not in valid_scores:
                errors["invalid_scores"].append(
                    f"{element_name}: {score} (valid: {valid_scores})"
                )
    
    # Validate reasoning
    if not isinstance(response_dict['reasoning'], dict):
        errors["type_errors"].append("reasoning must be a dictionary")
    else:
        for element in rubric.elements:
            element_name = element.name
            if element_name not in response_dict['reasoning']:
                errors["missing_reasoning"].append(element_name)
    
    # Validate feedback
    if not isinstance(response_dict['feedback'], str):
        errors["type_errors"].append("feedback must be a string")
    
    # Validate total_score
    if not isinstance(response_dict['total_score'], (int, float)):
        errors["type_errors"].append("total_score must be numeric")
    
    return errors


def create_fallback_response(rubric: Rubric, error_message: str) -> Dict[str, Any]:
    """
    Create a fallback response when parsing fails.
    
    Args:
        rubric: Evaluation rubric
        error_message: Error description
        
    Returns:
        Fallback response dictionary
    """
    scores = {}
    reasoning = {}
    
    for element in rubric.elements:
        scores[element.name] = 0
        reasoning[element.name] = f"채점 오류로 인해 점수를 부여할 수 없습니다: {error_message}"
    
    return {
        "scores": scores,
        "reasoning": reasoning,
        "feedback": f"채점 중 오류가 발생했습니다: {error_message}",
        "total_score": 0
    }


def optimize_prompt_for_model(prompt: str, model_type: str) -> str:
    """
    Optimize prompt based on specific model characteristics.
    
    Args:
        prompt: Base prompt
        model_type: Target model type (gemini/groq)
        
    Returns:
        Optimized prompt
    """
    if model_type == "gemini":
        # Gemini works well with structured prompts
        return prompt
    
    elif model_type == "groq":
        # Groq may benefit from more explicit instructions
        optimization_note = """
참고: 정확한 JSON 형식으로 응답해주세요. 추가적인 설명이나 텍스트 없이 JSON만 반환해주세요.
"""
        return prompt + "\n" + optimization_note
    
    return prompt


def estimate_token_count(text: str) -> int:
    """
    Rough estimation of token count for prompt length management.
    
    Args:
        text: Text to estimate
        
    Returns:
        Estimated token count
    """
    # Rough estimation: 1 token ≈ 4 characters for Korean/English mixed text
    return len(text) // 4


def truncate_prompt_if_needed(prompt: str, max_tokens: int = 6000) -> str:
    """
    Truncate prompt if it exceeds token limits.
    
    Args:
        prompt: Original prompt
        max_tokens: Maximum allowed tokens
        
    Returns:
        Truncated prompt if necessary
    """
    estimated_tokens = estimate_token_count(prompt)
    
    if estimated_tokens <= max_tokens:
        return prompt
    
    # Calculate target length
    target_length = max_tokens * 4  # Rough conversion back to characters
    
    # Try to truncate at sentence boundaries
    sentences = prompt.split('.')
    truncated = ""
    
    for sentence in sentences:
        if len(truncated + sentence + ".") > target_length:
            break
        truncated += sentence + "."
    
    # Add truncation notice
    truncated += "\n\n[프롬프트가 길이 제한으로 인해 일부 생략되었습니다.]"
    
    return truncated