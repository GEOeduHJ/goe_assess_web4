"""
지리 자동 채점 시스템의 채점 결과 데이터 모델
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import time
import json


@dataclass
class ElementScore:
    """단일 평가 요소의 점수와 근거를 나타냅니다."""

    element_name: str
    score: int
    max_score: int
    feedback: str = ""
    reasoning: str = ""

    def __post_init__(self):
        self._validate_data()

    def _validate_data(self):
        if not self.element_name or not self.element_name.strip():
            raise ValueError("Element name cannot be empty")
        if self.score < 0:
            raise ValueError("Score cannot be negative")
        if self.max_score < 0:
            raise ValueError("Max score cannot be negative")
        if self.score > self.max_score:
            raise ValueError("Score cannot exceed max score")

    @property
    def percentage(self) -> float:
        if self.max_score == 0:
            return 0.0
        return (self.score / self.max_score) * 100


@dataclass
class GradingResult:
    """학생의 완전한 채점 결과를 나타냅니다."""

    student_name: str
    student_class_number: str
    original_answer: str = ""
    element_scores: List[ElementScore] = field(default_factory=list)
    total_score: int = 0
    total_max_score: int = 0
    grading_time_seconds: float = 0.0
    graded_at: Optional[datetime] = None
    overall_feedback: str = ""
    status: str = "success"  # success | failed
    error_message: str = ""

    def __post_init__(self):
        self._validate_data()
        self._calculate_totals()
        if self.graded_at is None:
            self.graded_at = datetime.now()

    def _validate_data(self):
        if not self.student_name or not self.student_name.strip():
            raise ValueError("Student name cannot be empty")
        if not self.student_class_number or not self.student_class_number.strip():
            raise ValueError("Student class number cannot be empty")
        if self.grading_time_seconds < 0:
            raise ValueError("Grading time cannot be negative")
        if self.status not in {"success", "failed"}:
            raise ValueError("Status must be either 'success' or 'failed'")
        for element_score in self.element_scores:
            if not isinstance(element_score, ElementScore):
                raise ValueError("All element scores must be ElementScore instances")

    def _calculate_totals(self):
        self.total_score = sum(element.score for element in self.element_scores)
        self.total_max_score = sum(element.max_score for element in self.element_scores)

    def add_element_score(self, element_name: str, score: int, max_score: int, feedback: str = "", reasoning: str = ""):
        element_score = ElementScore(
            element_name=element_name,
            score=score,
            max_score=max_score,
            feedback=feedback,
            reasoning=reasoning,
        )
        self.element_scores.append(element_score)
        self._calculate_totals()

    def update_element_score(self, element_name: str, score: int, feedback: str = "", reasoning: str = ""):
        for element_score in self.element_scores:
            if element_score.element_name == element_name:
                element_score.score = score
                if feedback:
                    element_score.feedback = feedback
                if reasoning:
                    element_score.reasoning = reasoning
                element_score._validate_data()
                self._calculate_totals()
                return
        raise ValueError(f"Element '{element_name}' not found in scores")

    def get_element_score(self, element_name: str) -> ElementScore:
        for element_score in self.element_scores:
            if element_score.element_name == element_name:
                return element_score
        raise ValueError(f"Element '{element_name}' not found in scores")

    @property
    def percentage(self) -> float:
        if self.total_max_score == 0:
            return 0.0
        return (self.total_score / self.total_max_score) * 100

    @property
    def grade_letter(self) -> str:
        return self.get_relative_grade()

    def to_dict(self) -> Dict:
        return {
            "student_name": self.student_name,
            "student_class_number": self.student_class_number,
            "original_answer": self.original_answer,
            "element_scores": [
                {
                    "element_name": element.element_name,
                    "score": element.score,
                    "max_score": element.max_score,
                    "feedback": element.feedback,
                    "reasoning": element.reasoning,
                    "percentage": element.percentage,
                }
                for element in self.element_scores
            ],
            "total_score": self.total_score,
            "total_max_score": self.total_max_score,
            "percentage": self.percentage,
            "grade_letter": self.get_relative_grade(),
            "grading_time_seconds": self.grading_time_seconds,
            "graded_at": self.graded_at.isoformat() if self.graded_at else None,
            "overall_feedback": self.overall_feedback,
            "status": self.status,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'GradingResult':
        result = cls(
            student_name=data["student_name"],
            student_class_number=data["student_class_number"],
            original_answer=data.get("original_answer", ""),
            grading_time_seconds=data.get("grading_time_seconds", 0.0),
            overall_feedback=data.get("overall_feedback", ""),
            status=data.get("status", "success"),
            error_message=data.get("error_message", ""),
        )
        if data.get("graded_at"):
            result.graded_at = datetime.fromisoformat(data["graded_at"])
        for element_data in data.get("element_scores", []):
            result.add_element_score(
                element_name=element_data["element_name"],
                score=element_data["score"],
                max_score=element_data["max_score"],
                feedback=element_data.get("feedback", ""),
                reasoning=element_data.get("reasoning", ""),
            )
        return result

    @staticmethod
    def calculate_relative_grades(results: List['GradingResult']) -> Dict[str, str]:
        if not results:
            return {}
        sorted_results = sorted(results, key=lambda x: x.percentage, reverse=True)
        total_students = len(sorted_results)
        grade_mapping = {}
        i = 0
        while i < len(sorted_results):
            current_percentage = sorted_results[i].percentage
            same_score_group = []
            j = i
            while j < len(sorted_results) and sorted_results[j].percentage == current_percentage:
                same_score_group.append(sorted_results[j])
                j += 1
            start_rank = i + 1
            percentile_start = ((start_rank - 1) / total_students) * 100
            if percentile_start < 10:
                grade = "1"
            elif percentile_start < 34:
                grade = "2"
            elif percentile_start < 66:
                grade = "3"
            elif percentile_start < 87:
                grade = "4"
            else:
                grade = "5"
            for result in same_score_group:
                key = f"{result.student_name}_{result.student_class_number}"
                grade_mapping[key] = grade
            i = j
        return grade_mapping

    def set_relative_grade(self, grade: str):
        self._relative_grade = grade

    def get_relative_grade(self) -> str:
        return getattr(self, '_relative_grade', '미정')

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'GradingResult':
        return cls.from_dict(json.loads(json_str))


class GradingTimer:
    """채점 시간 측정을 위한 컨텍스트 매니저"""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed_time = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        if self.start_time:
            self.elapsed_time = self.end_time - self.start_time

    def start(self):
        self.start_time = time.time()

    def stop(self):
        if self.start_time:
            self.end_time = time.time()
            self.elapsed_time = self.end_time - self.start_time
        return self.elapsed_time
