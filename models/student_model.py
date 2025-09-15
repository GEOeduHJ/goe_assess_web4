"""
지리 자동 채점 시스템의 학생 데이터 모델
"""
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class Student:
    """
    답안 데이터가 포함된 학생을 나타냅니다.
    
    Attributes:
        name: 학생 이름
        class_number: 학생 반 번호
        answer: 학생의 텍스트 답안 (서술형 문제용)
        image_path: 학생의 이미지 답안 경로 (지도 문제용)
    """
    name: str
    class_number: str
    answer: str = ""
    image_path: Optional[str] = None
    
    def __post_init__(self):
        """초기화 후 학생 데이터 검증"""
        self._validate_data()
    
    def _validate_data(self):
        """학생 데이터 필드 검증"""
        if not self.name or not self.name.strip():
            raise ValueError("Student name cannot be empty")
        
        if not self.class_number or not self.class_number.strip():
            raise ValueError("Class number cannot be empty")
        
        # 서술형 문제의 경우 답안이 비어있으면 안됨
        # 지도 문제의 경우 image_path가 유효해야 함
        if not self.answer.strip() and not self.image_path:
            raise ValueError("Student must have either text answer or image path")
        
        # 처리 중에는 이미지 경로 존재 검증을 건너뜀
        # 파일 서비스가 이미지 파일 검증을 별도로 처리함
        # if self.image_path and not Path(self.image_path).exists():
        #     raise ValueError(f"Image file does not exist: {self.image_path}")
    
    @property
    def has_text_answer(self) -> bool:
        """학생이 텍스트 답안을 가지고 있는지 확인"""
        return bool(self.answer and self.answer.strip())
    
    @property
    def has_image_answer(self) -> bool:
        """학생이 이미지 답안을 가지고 있는지 확인"""
        return bool(self.image_path and Path(self.image_path).exists())
    
    @property
    def answer_type(self) -> str:
        """답안 유형을 가져옵니다 (text, image, 또는 both)"""
        if self.has_text_answer and self.has_image_answer:
            return "both"
        elif self.has_text_answer:
            return "text"
        elif self.has_image_answer:
            return "image"
        else:
            return "none"