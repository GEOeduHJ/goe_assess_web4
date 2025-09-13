"""
Grading result data model for geography auto-grading system.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import time
import json


@dataclass
class ElementScore:
    """
    Represents the score for a single evaluation element.
    
    Attributes:
        element_name: Name of the evaluation element
        score: Points awarded for this element
        max_score: Maximum possible points for this element
        feedback: Detailed feedback for this element
        reasoning: Reasoning for the score given
    """
    element_name: str
    score: int
    max_score: int
    feedback: str = ""
    reasoning: str = ""
    
    def __post_init__(self):
        """Validate element score data after initialization."""
        self._validate_data()
    
    def _validate_data(self):
        """Validate element score data fields."""
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
        """Calculate percentage score for this element."""
        if self.max_score == 0:
            return 0.0
        return (self.score / self.max_score) * 100


@dataclass
class GradingResult:
    """
    Represents the complete grading result for a student.
    
    Attributes:
        student_name: Name of the student
        student_class_number: Student's class number
        original_answer: Student's original answer (text or image path)
        element_scores: List of scores for each evaluation element
        total_score: Total points awarded
        total_max_score: Total maximum possible points
        grading_time_seconds: Time taken to grade in seconds
        graded_at: Timestamp when grading was completed
        overall_feedback: Overall feedback for the student
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
        """Validate result data and calculate totals."""
        self._validate_data()
        self._calculate_totals()
        if self.graded_at is None:
            self.graded_at = datetime.now()
    
    def _validate_data(self):
        """Validate grading result data fields."""
        if not self.student_name or not self.student_name.strip():
            raise ValueError("Student name cannot be empty")
        
        if not self.student_class_number or not self.student_class_number.strip():
            raise ValueError("Student class number cannot be empty")
        
        if self.grading_time_seconds < 0:
            raise ValueError("Grading time cannot be negative")
        
        # Note: original_answer can be empty for some cases (e.g., image-only answers)
        
        # Validate all element scores
        for element_score in self.element_scores:
            if not isinstance(element_score, ElementScore):
                raise ValueError("All element scores must be ElementScore instances")
    
    def _calculate_totals(self):
        """Calculate total scores from element scores."""
        self.total_score = sum(element.score for element in self.element_scores)
        self.total_max_score = sum(element.max_score for element in self.element_scores)
    
    def add_element_score(self, element_name: str, score: int, max_score: int, feedback: str = "", reasoning: str = ""):
        """Add a score for an evaluation element."""
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
        """Update the score for a specific element."""
        for element_score in self.element_scores:
            if element_score.element_name == element_name:
                element_score.score = score
                if feedback:
                    element_score.feedback = feedback
                if reasoning:
                    element_score.reasoning = reasoning
                element_score._validate_data()  # Re-validate after update
                self._calculate_totals()
                return
        
        raise ValueError(f"Element '{element_name}' not found in scores")
    
    def get_element_score(self, element_name: str) -> ElementScore:
        """Get the score for a specific element."""
        for element_score in self.element_scores:
            if element_score.element_name == element_name:
                return element_score
        
        raise ValueError(f"Element '{element_name}' not found in scores")
    
    @property
    def percentage(self) -> float:
        """Calculate overall percentage score."""
        if self.total_max_score == 0:
            return 0.0
        return (self.total_score / self.total_max_score) * 100
    
    @property
    def grade_letter(self) -> str:
        """Get letter grade based on percentage."""
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
        """Convert grading result to dictionary format."""
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
        """Create grading result from dictionary format."""
        result = cls(
            student_name=data["student_name"],
            student_class_number=data["student_class_number"],
            original_answer=data.get("original_answer", ""),
            grading_time_seconds=data.get("grading_time_seconds", 0.0),
            overall_feedback=data.get("overall_feedback", "")
        )
        
        # Parse graded_at timestamp
        if data.get("graded_at"):
            result.graded_at = datetime.fromisoformat(data["graded_at"])
        
        # Add element scores
        for element_data in data.get("element_scores", []):
            result.add_element_score(
                element_name=element_data["element_name"],
                score=element_data["score"],
                max_score=element_data["max_score"],
                feedback=element_data.get("feedback", "")
            )
        
        return result
    
    def to_json(self) -> str:
        """Convert grading result to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'GradingResult':
        """Create grading result from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class GradingTimer:
    """
    Context manager for measuring grading time.
    
    Usage:
        with GradingTimer() as timer:
            # Perform grading operations
            pass
        
        grading_time = timer.elapsed_time
    """
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed_time = 0.0
    
    def __enter__(self):
        """Start timing when entering context."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing when exiting context."""
        self.end_time = time.time()
        if self.start_time:
            self.elapsed_time = self.end_time - self.start_time
    
    def start(self):
        """Manually start timing."""
        self.start_time = time.time()
    
    def stop(self):
        """Manually stop timing and return elapsed time."""
        if self.start_time:
            self.end_time = time.time()
            self.elapsed_time = self.end_time - self.start_time
            return self.elapsed_time
        return 0.0
    
    def reset(self):
        """Reset the timer."""
        self.start_time = None
        self.end_time = None
        self.elapsed_time = 0.0