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
    """
    단일 평가 요소의 점수를 나타냅니다.
    
    Attributes:
        element_name: 평가 요소의 이름
        score: 이 요소에 부여된 점수
        max_score: 이 요소의 최대 가능 점수
        feedback: 이 요소에 대한 상세 피드백
        reasoning: 부여된 점수의 근거
    """
    element_name: str
    score: int
    max_score: int
    feedback: str = ""
    reasoning: str = ""
    
    def __post_init__(self):
        """초기화 후 요소 점수 데이터 검증"""
        self._validate_data()
    
    def _validate_data(self):
        """요소 점수 데이터 필드 검증"""
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
        """이 요소의 백분율 점수를 계산합니다."""
        if self.max_score == 0:
            return 0.0
        return (self.score / self.max_score) * 100


@dataclass
class GradingResult:
    """
    학생의 완전한 채점 결과를 나타냅니다.
    
    Attributes:
        student_name: 학생 이름
        student_class_number: 학생의 반 번호
        original_answer: 학생의 원본 답안 (텍스트 또는 이미지 경로)
        element_scores: 각 평가 요소의 점수 목록
        total_score: 총 획득 점수
        total_max_score: 총 최대 가능 점수
        grading_time_seconds: 채점에 소요된 시간(초)
        graded_at: 채점이 완료된 타임스탬프
        overall_feedback: 학생에 대한 전체 피드백
    """
    student_name: str
    student_class_number: str
    original_answer: str = ""
    element_scores: List[ElementScore] = field(default_factory=list)
    total_score: int = 0
    total_max_score: int = 0
    grading_time_seconds: float = 0.0
    graded_at: Optional[datetime] = None
    overall_feedback: str = ""
    
    def __post_init__(self):
        """결과 데이터 검증 및 총합 계산"""
        self._validate_data()
        self._calculate_totals()
        if self.graded_at is None:
            self.graded_at = datetime.now()
    
    def _validate_data(self):
        """채점 결과 데이터 필드 검증"""
        if not self.student_name or not self.student_name.strip():
            raise ValueError("Student name cannot be empty")
        
        if not self.student_class_number or not self.student_class_number.strip():
            raise ValueError("Student class number cannot be empty")
        
        if self.grading_time_seconds < 0:
            raise ValueError("Grading time cannot be negative")
        
        # 참고: original_answer는 일부 경우에 비어있을 수 있음 (예: 이미지 전용 답안)
        
        # 모든 요소 점수 검증
        for element_score in self.element_scores:
            if not isinstance(element_score, ElementScore):
                raise ValueError("All element scores must be ElementScore instances")
    
    def _calculate_totals(self):
        """요소 점수들로부터 총점 계산"""
        self.total_score = sum(element.score for element in self.element_scores)
        self.total_max_score = sum(element.max_score for element in self.element_scores)
    
    def add_element_score(self, element_name: str, score: int, max_score: int, feedback: str = "", reasoning: str = ""):
        """평가 요소에 대한 점수를 추가합니다."""
        element_score = ElementScore(
            element_name=element_name,
            score=score,
            max_score=max_score,
            feedback=feedback,
            reasoning=reasoning
        )
        self.element_scores.append(element_score)
        self._calculate_totals()
    
    def update_element_score(self, element_name: str, score: int, feedback: str = "", reasoning: str = ""):
        """특정 요소의 점수를 업데이트합니다."""
        for element_score in self.element_scores:
            if element_score.element_name == element_name:
                element_score.score = score
                if feedback:
                    element_score.feedback = feedback
                if reasoning:
                    element_score.reasoning = reasoning
                element_score._validate_data()  # 업데이트 후 재검증
                self._calculate_totals()
                return
        
        raise ValueError(f"Element '{element_name}' not found in scores")
    
    def get_element_score(self, element_name: str) -> ElementScore:
        """특정 요소의 점수를 가져옵니다."""
        for element_score in self.element_scores:
            if element_score.element_name == element_name:
                return element_score
        
        raise ValueError(f"Element '{element_name}' not found in scores")
    
    @property
    def percentage(self) -> float:
        """전체 백분율 점수를 계산합니다."""
        if self.total_max_score == 0:
            return 0.0
        return (self.total_score / self.total_max_score) * 100
    
    @property
    def grade_letter(self) -> str:
        """백분율을 기준으로 문자 등급을 가져옵니다."""
        percentage = self.percentage
        if percentage >= 90:
            return "A"
        elif percentage >= 80:
            return "B"
        elif percentage >= 70:
            return "C"
        elif percentage >= 60:
            return "D"
        else:
            return "F"
    
    def to_dict(self) -> Dict:
        """채점 결과를 딕셔너리 형식으로 변환합니다."""
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
                    "percentage": element.percentage
                }
                for element in self.element_scores
            ],
            "total_score": self.total_score,
            "total_max_score": self.total_max_score,
            "percentage": self.percentage,
            "grade_letter": self.grade_letter,
            "grading_time_seconds": self.grading_time_seconds,
            "graded_at": self.graded_at.isoformat() if self.graded_at else None,
            "overall_feedback": self.overall_feedback
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GradingResult':
        """딕셔너리 형식에서 채점 결과를 생성합니다."""
        result = cls(
            student_name=data["student_name"],
            student_class_number=data["student_class_number"],
            original_answer=data.get("original_answer", ""),
            grading_time_seconds=data.get("grading_time_seconds", 0.0),
            overall_feedback=data.get("overall_feedback", "")
        )
        
        # graded_at 타임스탬프 파싱
        if data.get("graded_at"):
            result.graded_at = datetime.fromisoformat(data["graded_at"])
        
        # 요소 점수 추가
        for element_data in data.get("element_scores", []):
            result.add_element_score(
                element_name=element_data["element_name"],
                score=element_data["score"],
                max_score=element_data["max_score"],
                feedback=element_data.get("feedback", "")
            )
        
        return result
    
    def to_json(self) -> str:
        """채점 결과를 JSON 문자열로 변환합니다."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'GradingResult':
        """JSON 문자열에서 채점 결과를 생성합니다."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class GradingTimer:
    """
    채점 시간 측정을 위한 컨텍스트 매니저
    
    사용법:
        with GradingTimer() as timer:
            # 채점 작업 수행
            pass
        
        grading_time = timer.elapsed_time
    """
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed_time = 0.0
    
    def __enter__(self):
        """컨텍스트 진입 시 타이밍 시작"""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 종료 시 타이밍 정지"""
        self.end_time = time.time()
        if self.start_time:
            self.elapsed_time = self.end_time - self.start_time
    
    def start(self):
        """수동으로 타이밍 시작"""
        self.start_time = time.time()
    
    def stop(self):
        """수동으로 타이밍 정지하고 경과 시간 반환"""
        if self.start_time:
            self.end_time = time.time()
            self.elapsed_time = self.end_time - self.start_time
            return self.elapsed_time
        return 0.0
    
    def reset(self):
        """타이머 리셋"""
        self.start_time = None
        self.end_time = None
        self.elapsed_time = 0.0