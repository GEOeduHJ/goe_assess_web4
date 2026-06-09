"""
Structured grading response schema and validation helpers.

This module keeps provider-specific JSON handling out of the grading flow.
The LLM must return element-level scores only; totals are computed from
`GradingResult` after validation.
"""
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class ElementGrade(BaseModel):
    """A single rubric element score returned by an LLM."""

    model_config = ConfigDict(extra="forbid")

    element_name: str = Field(..., description="Exact rubric element name")
    score: int = Field(..., description="Score assigned to this rubric element")
    reasoning: str = Field(..., description="Reason for the assigned score")


class GradeResponse(BaseModel):
    """Validated LLM grading response."""

    model_config = ConfigDict(extra="forbid")

    elements: List[ElementGrade] = Field(..., description="Scores for all rubric elements")
    feedback: str = Field(..., description="Overall feedback for the student")


GRADE_RESPONSE_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "elements": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "element_name": {"type": "string"},
                    "score": {"type": "integer"},
                    "reasoning": {"type": "string"},
                },
                "required": ["element_name", "score", "reasoning"],
            },
        },
        "feedback": {"type": "string"},
    },
    "required": ["elements", "feedback"],
}


def normalize_raw_response(raw: Dict[str, Any]) -> GradeResponse:
    """
    Normalize a provider response into `GradeResponse`.

    The primary schema is:
    {"elements": [{"element_name": ..., "score": ..., "reasoning": ...}], "feedback": ...}

    A legacy fallback is kept to parse older responses with `scores` and `reasoning`
    dictionaries, but validation still enforces the current rubric.
    """
    if "elements" in raw:
        return GradeResponse.model_validate(raw)

    if "scores" in raw and isinstance(raw.get("scores"), dict):
        reasoning = raw.get("reasoning") if isinstance(raw.get("reasoning"), dict) else {}
        elements = [
            {
                "element_name": str(element_name),
                "score": score,
                "reasoning": str(reasoning.get(element_name, "")),
            }
            for element_name, score in raw["scores"].items()
        ]
        return GradeResponse.model_validate(
            {
                "elements": elements,
                "feedback": str(raw.get("feedback", "")),
            }
        )

    return GradeResponse.model_validate(raw)


def validate_against_rubric(response: GradeResponse, rubric: Any) -> Dict[str, Any]:
    """
    Validate a structured response against the rubric.

    Returns the internal dict shape expected by the rest of the application:
    {"scores": {name: score}, "reasoning": {name: reasoning}, "feedback": str}
    """
    expected = {element.name: element for element in rubric.elements}
    scores: Dict[str, int] = {}
    reasoning: Dict[str, str] = {}

    for item in response.elements:
        if item.element_name not in expected:
            raise ValueError(f"Unknown rubric element in model response: {item.element_name}")
        if item.element_name in scores:
            raise ValueError(f"Duplicate rubric element in model response: {item.element_name}")
        if not item.reasoning.strip():
            raise ValueError(f"Missing reasoning for rubric element: {item.element_name}")

        rubric_element = expected[item.element_name]
        valid_scores = [criteria.score for criteria in rubric_element.criteria]
        if not valid_scores:
            valid_scores = [0, rubric_element.max_score]

        if item.score not in valid_scores:
            raise ValueError(
                f"Invalid score {item.score} for '{item.element_name}'. "
                f"Allowed scores: {valid_scores}"
            )

        scores[item.element_name] = item.score
        reasoning[item.element_name] = item.reasoning.strip()

    missing = [name for name in expected if name not in scores]
    if missing:
        raise ValueError(f"Missing rubric elements in model response: {missing}")

    if not response.feedback.strip():
        raise ValueError("Missing overall feedback in model response")

    return {
        "scores": scores,
        "reasoning": reasoning,
        "feedback": response.feedback.strip(),
    }
