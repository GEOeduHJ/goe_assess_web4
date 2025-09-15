"""
루브릭 관련 데이터 모델들
평가 기준, 평가 요소, 루브릭 클래스를 정의합니다.
"""
from dataclasses import dataclass, field
from typing import List, Dict
import json


@dataclass
class EvaluationCriteria:
    """평가 기준을 나타내는 클래스"""
    score: int  # 점수
    description: str  # 기준 설명
    
    def __post_init__(self):
        if self.score < 0:
            raise ValueError("Score cannot be negative")
        if not self.description or not self.description.strip():
            raise ValueError("Criteria description cannot be empty")


@dataclass
class EvaluationElement:
    """평가 요소를 나타내는 클래스"""
    name: str  # 요소명
    criteria: List[EvaluationCriteria] = field(default_factory=list)  # 기준 목록
    max_score: int = 0  # 최대 점수
    
    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Evaluation element name cannot be empty")
        self._calculate_max_score()
    
    def _calculate_max_score(self):
        """최대 점수 계산"""
        if self.criteria:
            self.max_score = max(criteria.score for criteria in self.criteria)
    
    def add_criteria(self, score: int, description: str):
        """평가 기준 추가"""
        criteria = EvaluationCriteria(score=score, description=description)
        self.criteria.append(criteria)
        self._calculate_max_score()
    
    def update_criteria(self, index: int, score: int, description: str):
        """기존 기준 업데이트 및 최대 점수 재계산"""
        if 0 <= index < len(self.criteria):
            self.criteria[index].score = score
            self.criteria[index].description = description
            self._calculate_max_score()
    
    def remove_criteria(self, index: int):
        """기준 제거 및 최대 점수 재계산"""
        if 0 <= index < len(self.criteria):
            self.criteria.pop(index)
            self._calculate_max_score()


@dataclass
class Rubric:
    """루브릭 클래스"""
    name: str  # 루브릭 이름
    elements: List[EvaluationElement] = field(default_factory=list)  # 평가 요소 목록
    total_max_score: int = 0  # 총 최대 점수
    
    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Rubric name cannot be empty")
        self._calculate_total_max_score()
    
    def _calculate_total_max_score(self):
        """총 최대 점수 계산"""
        self.total_max_score = sum(element.max_score for element in self.elements)
    
    def add_element(self, element: EvaluationElement):
        """평가 요소 추가"""
        self.elements.append(element)
        self._calculate_total_max_score()
    
    def update_total_score(self):
        """요소가 수정되었을 때 총 최대 점수를 수동으로 업데이트"""
        self._calculate_total_max_score()
    
    def remove_element(self, index: int):
        """요소 제거 및 총 최대 점수 재계산"""
        if 0 <= index < len(self.elements):
            self.elements.pop(index)
            self._calculate_total_max_score()
    
    def to_dict(self) -> Dict:
        """루브릭을 딕셔너리 형식으로 변환"""
        return {
            "name": self.name,
            "elements": [
                {
                    "name": element.name,
                    "max_score": element.max_score,
                    "criteria": [
                        {
                            "score": criteria.score,
                            "description": criteria.description
                        }
                        for criteria in element.criteria
                    ]
                }
                for element in self.elements
            ],
            "total_max_score": self.total_max_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Rubric':
        """딕셔너리 형식에서 루브릭 생성"""
        rubric = cls(name=data["name"])
        
        for element_data in data["elements"]:
            element = EvaluationElement(name=element_data["name"])
            
            for criteria_data in element_data["criteria"]:
                element.add_criteria(
                    score=criteria_data["score"],
                    description=criteria_data["description"]
                )
            
            rubric.add_element(element)
        
        return rubric