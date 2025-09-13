"""
Student data model for geography auto-grading system.
"""
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class Student:
    """
    Represents a student with their answer data.
    
    Attributes:
        name: Student's name
        class_number: Student's class number
        answer: Student's text answer (for descriptive questions)
        image_path: Path to student's image answer (for map questions)
    """
    name: str
    class_number: str
    answer: str = ""
    image_path: Optional[str] = None
    
    def __post_init__(self):
        """Validate student data after initialization."""
        self._validate_data()
    
    def _validate_data(self):
        """Validate student data fields."""
        if not self.name or not self.name.strip():
            raise ValueError("Student name cannot be empty")
        
        if not self.class_number or not self.class_number.strip():
            raise ValueError("Class number cannot be empty")
        
        # For descriptive questions, answer should not be empty
        # For map questions, image_path should be valid
        if not self.answer.strip() and not self.image_path:
            raise ValueError("Student must have either text answer or image path")
        
        # Skip image path existence validation during processing
        # The file service will handle image file validation separately
        # if self.image_path and not Path(self.image_path).exists():
        #     raise ValueError(f"Image file does not exist: {self.image_path}")
    
    @property
    def has_text_answer(self) -> bool:
        """Check if student has a text answer."""
        return bool(self.answer and self.answer.strip())
    
    @property
    def has_image_answer(self) -> bool:
        """Check if student has an image answer."""
        return bool(self.image_path and Path(self.image_path).exists())
    
    @property
    def answer_type(self) -> str:
        """Get the type of answer (text, image, or both)."""
        if self.has_text_answer and self.has_image_answer:
            return "both"
        elif self.has_text_answer:
            return "text"
        elif self.has_image_answer:
            return "image"
        else:
            return "none"