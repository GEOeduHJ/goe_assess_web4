from dataclasses import dataclass, field
from typing import List, Dict
import json


@dataclass
class EvaluationCriteria:
    score: int
    description: str
    
    def __post_init__(self):
        if self.score < 0:
            raise ValueError("Score cannot be negative")
        if not self.description or not self.description.strip():
            raise ValueError("Criteria description cannot be empty")


@dataclass
class EvaluationElement:
    name: str
    criteria: List[EvaluationCriteria] = field(default_factory=list)
    max_score: int = 0
    
    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Evaluation element name cannot be empty")
        self._calculate_max_score()
    
    def _calculate_max_score(self):
        if self.criteria:
            self.max_score = max(criteria.score for criteria in self.criteria)
    
    def add_criteria(self, score: int, description: str):
        criteria = EvaluationCriteria(score=score, description=description)
        self.criteria.append(criteria)
        self._calculate_max_score()
    
    def update_criteria(self, index: int, score: int, description: str):
        """Update existing criteria and recalculate max score."""
        if 0 <= index < len(self.criteria):
            self.criteria[index].score = score
            self.criteria[index].description = description
            self._calculate_max_score()
    
    def remove_criteria(self, index: int):
        """Remove criteria and recalculate max score."""
        if 0 <= index < len(self.criteria):
            self.criteria.pop(index)
            self._calculate_max_score()


@dataclass
class Rubric:
    name: str
    elements: List[EvaluationElement] = field(default_factory=list)
    total_max_score: int = 0
    
    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Rubric name cannot be empty")
        self._calculate_total_max_score()
    
    def _calculate_total_max_score(self):
        self.total_max_score = sum(element.max_score for element in self.elements)
    
    def add_element(self, element: EvaluationElement):
        self.elements.append(element)
        self._calculate_total_max_score()
    
    def update_total_score(self):
        """Manually update total max score when elements are modified."""
        self._calculate_total_max_score()
    
    def remove_element(self, index: int):
        """Remove element and recalculate total max score."""
        if 0 <= index < len(self.elements):
            self.elements.pop(index)
            self._calculate_total_max_score()
    
    def to_dict(self) -> Dict:
        """Convert rubric to dictionary format."""
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
        """Create rubric from dictionary format."""
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