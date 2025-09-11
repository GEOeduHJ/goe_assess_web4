"""
Tests for results UI components.
"""

import pytest
import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch
import streamlit as st

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.results_ui import ResultsUI, create_results_ui
from models.result_model import GradingResult, ElementScore


class TestResultsUI:
    """Test cases for ResultsUI class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.results_ui = create_results_ui()
        
        # Create sample results for testing
        self.sample_results = self.create_sample_results()
    
    def create_sample_results(self):
        """Create sample grading results for testing."""
        results = []
        
        # Student 1 - High performer
        result1 = GradingResult(
            student_name="김철수",
            student_class_number="1반",
            grading_time_seconds=8.5,
            overall_feedback="전반적으로 우수한 답안입니다. 지리적 개념을 정확히 이해하고 있습니다."
        )
        result1.add_element_score("지리적 개념 이해", 18, 20, "지리적 개념을 정확히 설명했습니다.")
        result1.add_element_score("사례 분석", 16, 20, "적절한 사례를 들어 설명했습니다.")
        result1.add_element_score("논리적 구성", 17, 20, "논리적으로 잘 구성된 답안입니다.")
        results.append(result1)
        
        # Student 2 - Average performer
        result2 = GradingResult(
            student_name="이영희",
            student_class_number="2반",
            grading_time_seconds=7.2,
            overall_feedback="기본적인 이해는 있으나 더 구체적인 설명이 필요합니다."
        )
        result2.add_element_score("지리적 개념 이해", 14, 20, "개념 이해가 부족합니다.")
        result2.add_element_score("사례 분석", 12, 20, "사례가 부적절합니다.")
        result2.add_element_score("논리적 구성", 15, 20, "구성이 다소 산만합니다.")
        results.append(result2)
        
        # Student 3 - Low performer
        result3 = GradingResult(
            student_name="박민수",
            student_class_number="1반",
            grading_time_seconds=6.8,
            overall_feedback="기본 개념부터 다시 학습이 필요합니다."
        )
        result3.add_element_score("지리적 개념 이해", 8, 20, "개념 이해가 매우 부족합니다.")
        result3.add_element_score("사례 분석", 6, 20, "사례 분석이 잘못되었습니다.")
        result3.add_element_score("논리적 구성", 9, 20, "논리적 구성이 부족합니다.")
        results.append(result3)
        
        return results
    
    def test_create_results_ui(self):
        """Test results UI factory function."""
        ui = create_results_ui()
        assert isinstance(ui, ResultsUI)
    
    def test_initialize_session_state(self):
        """Test session state initialization."""
        with patch('streamlit.session_state', {}):
            self.results_ui.initialize_session_state()
            
            # Check if session state variables are initialized
            assert 'selected_student_result' in st.session_state
            assert 'results_view_mode' in st.session_state
            assert 'results_sort_by' in st.session_state
            assert 'results_filter_grade' in st.session_state
    
    def test_filter_and_sort_results(self):
        """Test results filtering and sorting functionality."""
        # Test sorting by total score (descending)
        sorted_results = self.results_ui.filter_and_sort_results(
            self.sample_results, "total_score", "desc", "all"
        )
        
        # Should be sorted by total score in descending order
        assert sorted_results[0].total_score >= sorted_results[1].total_score
        assert sorted_results[1].total_score >= sorted_results[2].total_score
        
        # Test sorting by student name (ascending)
        sorted_results = self.results_ui.filter_and_sort_results(
            self.sample_results, "student_name", "asc", "all"
        )
        
        # Should be sorted alphabetically
        names = [r.student_name for r in sorted_results]
        assert names == sorted(names)
        
        # Test grade filtering
        a_grade_results = self.results_ui.filter_and_sort_results(
            self.sample_results, "total_score", "desc", "A"
        )
        
        # Should only include A grade students
        for result in a_grade_results:
            assert result.grade_letter == "A"
    
    @patch('streamlit.markdown')
    @patch('streamlit.columns')
    @patch('streamlit.metric')
    def test_render_results_overview(self, mock_metric, mock_columns, mock_markdown):
        """Test results overview rendering."""
        # Mock streamlit columns
        mock_columns.return_value = [Mock() for _ in range(5)]
        
        # Test with sample results
        self.results_ui.render_results_overview(self.sample_results)
        
        # Verify that markdown and metrics were called
        assert mock_markdown.called
        assert mock_metric.called
    
    @patch('streamlit.info')
    def test_render_results_page_empty(self, mock_info):
        """Test rendering results page with empty results."""
        self.results_ui.render_results_page([])
        
        # Should show info message for empty results
        mock_info.assert_called_with("📋 아직 채점 결과가 없습니다.")
    
    @patch('streamlit.markdown')
    @patch('streamlit.radio')
    def test_render_view_mode_selector(self, mock_radio, mock_markdown):
        """Test view mode selector rendering."""
        mock_radio.return_value = "overview"
        
        self.results_ui.render_view_mode_selector()
        
        # Verify radio button was called with correct options
        mock_radio.assert_called_once()
        call_args = mock_radio.call_args
        assert "overview" in call_args[1]["options"]
        assert "individual" in call_args[1]["options"]
        assert "analytics" in call_args[1]["options"]
    
    def test_student_performance_insights(self):
        """Test student performance insights generation."""
        # Test with high-performing student
        high_performer = self.sample_results[0]  # 김철수
        
        # Calculate expected insights
        element_percentages = [e.percentage for e in high_performer.element_scores]
        avg_performance = sum(element_percentages) / len(element_percentages)
        
        # Should be high performance (>80%)
        assert avg_performance > 80
        
        # Test with low-performing student
        low_performer = self.sample_results[2]  # 박민수
        element_percentages = [e.percentage for e in low_performer.element_scores]
        avg_performance = sum(element_percentages) / len(element_percentages)
        
        # Should be low performance (<60%)
        assert avg_performance < 60
    
    @patch('services.export_service.ExportService')
    def test_export_to_excel(self, mock_export_service):
        """Test Excel export functionality."""
        # Mock export service
        mock_service = Mock()
        mock_service.create_results_excel.return_value = "/tmp/test_results.xlsx"
        mock_export_service.return_value = mock_service
        
        with patch('streamlit.success') as mock_success:
            with patch('builtins.open', create=True) as mock_open:
                with patch('streamlit.download_button') as mock_download:
                    mock_open.return_value.__enter__.return_value.read.return_value = b"test data"
                    
                    self.results_ui.export_to_excel(self.sample_results)
                    
                    # Verify export service was called
                    mock_service.create_results_excel.assert_called_once_with(self.sample_results)
                    
                    # Verify success message and download button
                    mock_success.assert_called_once()
                    mock_download.assert_called_once()
    
    def test_element_score_visualization_data(self):
        """Test data preparation for element score visualization."""
        result = self.sample_results[0]  # 김철수
        
        # Extract visualization data
        element_names = [e.element_name for e in result.element_scores]
        scores = [e.score for e in result.element_scores]
        max_scores = [e.max_score for e in result.element_scores]
        percentages = [e.percentage for e in result.element_scores]
        
        # Verify data structure
        assert len(element_names) == len(scores) == len(max_scores) == len(percentages)
        assert all(isinstance(name, str) for name in element_names)
        assert all(isinstance(score, (int, float)) for score in scores)
        assert all(0 <= percentage <= 100 for percentage in percentages)
    
    def test_grade_distribution_calculation(self):
        """Test grade distribution calculation."""
        # Calculate grade distribution
        grade_counts = {}
        for result in self.sample_results:
            grade = result.grade_letter
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        # Verify distribution
        total_students = len(self.sample_results)
        assert sum(grade_counts.values()) == total_students
        
        # Check that all grades are valid
        valid_grades = {'A', 'B', 'C', 'D', 'F'}
        for grade in grade_counts.keys():
            assert grade in valid_grades
    
    def test_time_analysis_data(self):
        """Test grading time analysis data preparation."""
        grading_times = [r.grading_time_seconds for r in self.sample_results]
        
        # Verify time data
        assert all(time > 0 for time in grading_times)
        assert len(grading_times) == len(self.sample_results)
        
        # Calculate statistics
        import statistics
        avg_time = statistics.mean(grading_times)
        total_time = sum(grading_times)
        
        assert avg_time > 0
        assert total_time > 0
        assert total_time >= max(grading_times)


class TestResultsUIIntegration:
    """Integration tests for results UI with other components."""
    
    def test_results_ui_with_export_service(self):
        """Test results UI integration with export service."""
        from services.export_service import create_export_service
        
        # Create services
        results_ui = create_results_ui()
        export_service = create_export_service()
        
        # Create sample results
        results = []
        result = GradingResult(
            student_name="테스트학생",
            student_class_number="1반",
            grading_time_seconds=5.0,
            overall_feedback="테스트 피드백"
        )
        result.add_element_score("테스트요소", 15, 20, "테스트 요소 피드백")
        results.append(result)
        
        # Test export functionality
        formatted_data = export_service.format_results_for_export(results)
        
        # Verify formatted data structure
        assert 'summary_statistics' in formatted_data
        assert 'grade_distribution' in formatted_data
        assert 'student_details' in formatted_data
        assert len(formatted_data['student_details']) == 1
    
    def test_results_ui_data_consistency(self):
        """Test data consistency across UI components."""
        results_ui = create_results_ui()
        
        # Create test results
        result = GradingResult(
            student_name="일관성테스트",
            student_class_number="1반",
            grading_time_seconds=7.5,
            overall_feedback="일관성 테스트 피드백"
        )
        result.add_element_score("요소1", 18, 20, "요소1 피드백")
        result.add_element_score("요소2", 16, 20, "요소2 피드백")
        
        results = [result]
        
        # Test filtering and sorting maintains data integrity
        filtered_results = results_ui.filter_and_sort_results(
            results, "total_score", "desc", "all"
        )
        
        # Verify data consistency
        assert len(filtered_results) == len(results)
        assert filtered_results[0].student_name == result.student_name
        assert filtered_results[0].total_score == result.total_score
        assert len(filtered_results[0].element_scores) == len(result.element_scores)


if __name__ == "__main__":
    pytest.main([__file__])