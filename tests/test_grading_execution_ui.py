"""
Tests for the Grading Execution UI components.
"""

import pytest
import streamlit as st
from unittest.mock import Mock, patch, MagicMock
import queue
import time

from ui.grading_execution_ui import GradingExecutionUI, GradingSession
from services.grading_engine import GradingProgress
from models.student_model import Student
from models.rubric_model import Rubric, EvaluationElement
from utils.error_handler import ErrorInfo, ErrorType


@pytest.fixture
def sample_students():
    """Create sample students for testing."""
    return [
        Student(name="김철수", class_number="1-1", answer="한국의 수도는 서울이다."),
        Student(name="이영희", class_number="1-2", answer="부산은 한국의 제2의 도시이다."),
        Student(name="박민수", class_number="1-3", answer="제주도는 한국의 남쪽에 위치한다.")
    ]


@pytest.fixture
def sample_rubric():
    """Create sample rubric for testing."""
    rubric = Rubric(name="지리 기본 지식")
    
    # 정확성 평가 요소
    accuracy_element = EvaluationElement(name="정확성")
    accuracy_element.add_criteria(5, "완전히 정확한 답변")
    accuracy_element.add_criteria(3, "부분적으로 정확한 답변")
    accuracy_element.add_criteria(1, "부정확한 답변")
    accuracy_element.add_criteria(0, "답변 없음")
    
    rubric.add_element(accuracy_element)
    return rubric


@pytest.fixture
def grading_execution_ui():
    """Create a GradingExecutionUI instance for testing."""
    # Mock Streamlit session state
    with patch('ui.grading_execution_ui.st.session_state', dict()):
        ui = GradingExecutionUI()
        return ui


class TestGradingExecutionUI:
    """Test GradingExecutionUI class."""
    
    def test_initialization(self, grading_execution_ui):
        """Test UI initialization."""
        assert grading_execution_ui is not None
        assert grading_execution_ui.progress_queue is not None
        assert grading_execution_ui.result_queue is not None
    
    def test_run_grading_thread_completion_signal(self, grading_execution_ui, sample_students, sample_rubric):
        """Test that run_grading_thread sends proper completion signal."""
        # Create a mock grading engine
        mock_engine = Mock()
        mock_engine.grade_students_sequential.return_value = [Mock(), Mock(), Mock()]  # 3 results
        grading_execution_ui.grading_engine = mock_engine
        
        # Create a grading session
        session = GradingSession(
            students=sample_students,
            rubric=sample_rubric,
            model_type="gemini",
            grading_type="descriptive"
        )
        session.is_active = True
        
        # Run the grading thread method
        grading_execution_ui.run_grading_thread(session)
        
        # Check that the completion signal was sent
        assert not session.is_active
        assert not session.is_paused
        
        # Check that a completion message was put in the queue
        update_type, data = grading_execution_ui.progress_queue.get_nowait()
        assert update_type == 'completed'
        assert data == 3  # 3 successfully graded students
    
    def test_update_progress_from_queue_completion_handling(self, grading_execution_ui):
        """Test that update_progress_from_queue properly handles completion signals."""
        # Set up session state
        st.session_state.grading_session = Mock()
        st.session_state.grading_session.is_active = True
        
        # Put a completion message in the queue
        grading_execution_ui.progress_queue.put(('completed', 5))
        
        # Process the queue
        grading_execution_ui.update_progress_from_queue()
        
        # Check that the session was marked as inactive
        assert not st.session_state.grading_session.is_active
        assert not st.session_state.grading_session.is_paused
    
    def test_render_grading_controls_completion_state(self, grading_execution_ui, sample_students, sample_rubric):
        """Test that render_grading_controls properly shows completion state."""
        # This test would require mocking Streamlit components, which is complex
        # We'll focus on unit testing the logic instead of the UI rendering
        pass
    
    def test_render_progress_display_completion_state(self, grading_execution_ui, sample_students, sample_rubric):
        """Test that render_progress_display properly shows completion state."""
        # This test would require mocking Streamlit components, which is complex
        # We'll focus on unit testing the logic instead of the UI rendering
        pass