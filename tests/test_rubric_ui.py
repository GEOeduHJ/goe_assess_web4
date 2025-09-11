"""
Tests for rubric UI components.
"""

import pytest
from ui.rubric_ui import Rubric, EvaluationElement, EvaluationCriteria


class TestEvaluationCriteria:
    """Test cases for EvaluationCriteria class."""
    
    def test_criteria_creation(self):
        """Test creating evaluation criteria."""
        criteria = EvaluationCriteria(score=5, description="Excellent work")
        assert criteria.score == 5
        assert criteria.description == "Excellent work"


class TestEvaluationElement:
    """Test cases for EvaluationElement class."""
    
    def test_element_creation(self):
        """Test creating evaluation element."""
        element = EvaluationElement(name="Content Accuracy")
        assert element.name == "Content Accuracy"
        assert element.criteria == []
        assert element.max_score == 0
    
    def test_element_max_score(self):
        """Test max score calculation."""
        element = EvaluationElement(name="Test Element")
        element.criteria = [
            EvaluationCriteria(score=5, description="Excellent"),
            EvaluationCriteria(score=3, description="Good"),
            EvaluationCriteria(score=1, description="Poor")
        ]
        assert element.max_score == 5


class TestRubric:
    """Test cases for Rubric class."""
    
    def test_empty_rubric(self):
        """Test empty rubric creation."""
        rubric = Rubric()
        assert rubric.elements == []
        assert rubric.total_max_score == 0
    
    def test_rubric_total_score(self):
        """Test total max score calculation."""
        rubric = Rubric()
        
        # Add first element
        element1 = EvaluationElement(name="Content")
        element1.criteria = [
            EvaluationCriteria(score=5, description="Excellent"),
            EvaluationCriteria(score=0, description="Poor")
        ]
        
        # Add second element
        element2 = EvaluationElement(name="Quality")
        element2.criteria = [
            EvaluationCriteria(score=3, description="Good"),
            EvaluationCriteria(score=0, description="Poor")
        ]
        
        rubric.elements = [element1, element2]
        assert rubric.total_max_score == 8  # 5 + 3
    
    def test_rubric_to_dict(self):
        """Test rubric serialization to dictionary."""
        rubric = Rubric()
        element = EvaluationElement(name="Test Element")
        element.criteria = [
            EvaluationCriteria(score=3, description="Good work")
        ]
        rubric.elements = [element]
        
        rubric_dict = rubric.to_dict()
        
        assert "elements" in rubric_dict
        assert "total_max_score" in rubric_dict
        assert rubric_dict["total_max_score"] == 3
        assert len(rubric_dict["elements"]) == 1
        assert rubric_dict["elements"][0]["name"] == "Test Element"
    
    def test_rubric_from_dict(self):
        """Test rubric deserialization from dictionary."""
        rubric_data = {
            "elements": [
                {
                    "name": "Content Accuracy",
                    "criteria": [
                        {"score": 5, "description": "Excellent"},
                        {"score": 3, "description": "Good"}
                    ],
                    "max_score": 5
                }
            ],
            "total_max_score": 5
        }
        
        rubric = Rubric.from_dict(rubric_data)
        
        assert len(rubric.elements) == 1
        assert rubric.elements[0].name == "Content Accuracy"
        assert len(rubric.elements[0].criteria) == 2
        assert rubric.elements[0].criteria[0].score == 5
        assert rubric.total_max_score == 5


if __name__ == "__main__":
    pytest.main([__file__])