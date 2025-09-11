"""
Export service for generating Excel files and other export formats.
Handles result data formatting and file generation for download.
"""

import pandas as pd
import os
import tempfile
from typing import List, Dict, Any
from datetime import datetime
import logging

from models.result_model import GradingResult


class ExportService:
    """Service for exporting grading results to various formats."""
    
    def __init__(self):
        """Initialize the export service."""
        self.logger = logging.getLogger(__name__)
    
    def create_results_excel(self, results: List[GradingResult]) -> str:
        """
        Create Excel file with comprehensive grading results.
        Implements Requirements 6.3, 6.4 - Excel export with all result data
        
        Args:
            results: List of grading results to export
            
        Returns:
            str: Path to the created Excel file
            
        Raises:
            ValueError: If no results provided or invalid data
            PermissionError: If unable to write to temporary directory
            Exception: For other file creation errors
        """
        if not results:
            raise ValueError("채점 결과가 없어 Excel 파일을 생성할 수 없습니다.")
        
        # Validate results data
        for i, result in enumerate(results):
            if not isinstance(result, GradingResult):
                raise ValueError(f"결과 {i+1}번이 올바른 GradingResult 형식이 아닙니다.")
            
            if not result.student_name.strip():
                raise ValueError(f"결과 {i+1}번의 학생명이 비어있습니다.")
        
        try:
            # Create temporary file with error handling
            temp_dir = tempfile.gettempdir()
            
            # Check if temp directory is writable
            if not os.access(temp_dir, os.W_OK):
                raise PermissionError(f"임시 디렉토리에 쓰기 권한이 없습니다: {temp_dir}")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_path = os.path.join(temp_dir, f"grading_results_{timestamp}.xlsx")
            
            self.logger.info(f"Excel 파일 생성 시작: {excel_path}")
            
            # Create Excel writer with error handling
            try:
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    # Main results sheet
                    self._create_main_results_sheet(results, writer)
                    
                    # Element scores detail sheet
                    self._create_element_scores_sheet(results, writer)
                    
                    # Summary statistics sheet
                    self._create_summary_sheet(results, writer)
                    
                    # Feedback sheet
                    self._create_feedback_sheet(results, writer)
                    
            except PermissionError as e:
                raise PermissionError(f"Excel 파일 생성 권한이 없습니다: {e}")
            except Exception as e:
                raise Exception(f"Excel 파일 작성 중 오류가 발생했습니다: {e}")
            
            # Verify file was created successfully
            if not os.path.exists(excel_path):
                raise Exception("Excel 파일이 생성되지 않았습니다.")
            
            file_size = os.path.getsize(excel_path)
            if file_size == 0:
                raise Exception("Excel 파일이 비어있습니다.")
            
            self.logger.info(f"Excel 파일 생성 완료: {excel_path} (크기: {file_size} bytes)")
            return excel_path
            
        except (ValueError, PermissionError) as e:
            # Re-raise known exceptions
            self.logger.error(f"Excel 파일 생성 실패: {e}")
            raise
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Excel 파일 생성 중 예상치 못한 오류가 발생했습니다: {e}"
            self.logger.error(error_msg)
            raise Exception(error_msg)
    
    def _create_main_results_sheet(self, results: List[GradingResult], writer: pd.ExcelWriter):
        """Create the main results sheet with student overview."""
        try:
            main_data = []
            
            for result in results:
                # Safely handle potentially missing data
                row = {
                    '학생명': result.student_name or '',
                    '반': result.student_class_number or '',
                    '원본답안': result.original_answer or '[답안 없음]',
                    '총점': result.total_score,
                    '만점': result.total_max_score,
                    '백분율': round(result.percentage, 1),
                    '등급': result.grade_letter,
                    '채점시간(초)': round(result.grading_time_seconds, 1),
                    '채점완료시각': result.graded_at.strftime('%Y-%m-%d %H:%M:%S') if result.graded_at else '',
                    '전체피드백': result.overall_feedback or '[피드백 없음]'
                }
                
                # Add element scores as separate columns
                for element in result.element_scores:
                    element_name = element.element_name or '알수없음'
                    row[f'{element_name}_점수'] = element.score
                    row[f'{element_name}_만점'] = element.max_score
                    row[f'{element_name}_백분율'] = round(element.percentage, 1)
                
                main_data.append(row)
            
            if not main_data:
                raise ValueError("메인 결과 시트에 표시할 데이터가 없습니다.")
            
            df_main = pd.DataFrame(main_data)
            df_main.to_excel(writer, sheet_name='채점결과', index=False)
            
            # Format the worksheet
            worksheet = writer.sheets['채점결과']
            
            # Auto-adjust column widths with error handling
            for column in df_main:
                try:
                    column_length = max(df_main[column].astype(str).map(len).max(), len(column))
                    col_idx = df_main.columns.get_loc(column)
                    if col_idx < 26:  # Only handle A-Z columns for simplicity
                        worksheet.column_dimensions[chr(65 + col_idx)].width = min(column_length + 2, 50)
                except Exception as e:
                    self.logger.warning(f"열 너비 조정 실패 ({column}): {e}")
                    
        except Exception as e:
            raise Exception(f"메인 결과 시트 생성 실패: {e}")
    
    def _create_element_scores_sheet(self, results: List[GradingResult], writer: pd.ExcelWriter):
        """Create detailed element scores sheet."""
        try:
            element_data = []
            
            for result in results:
                for element in result.element_scores:
                    row = {
                        '학생명': result.student_name or '',
                        '반': result.student_class_number or '',
                        '원본답안': result.original_answer or '[답안 없음]',
                        '평가요소': element.element_name or '',
                        '획득점수': element.score,
                        '만점': element.max_score,
                        '백분율': round(element.percentage, 1),
                        '요소별피드백': element.feedback or '[피드백 없음]',
                        '채점시간(초)': round(result.grading_time_seconds, 1)
                    }
                    element_data.append(row)
            
            if element_data:
                df_elements = pd.DataFrame(element_data)
                df_elements.to_excel(writer, sheet_name='평가요소별상세', index=False)
                
                # Format the worksheet
                worksheet = writer.sheets['평가요소별상세']
                
                # Auto-adjust column widths with error handling
                for column in df_elements:
                    try:
                        column_length = max(df_elements[column].astype(str).map(len).max(), len(column))
                        col_idx = df_elements.columns.get_loc(column)
                        if col_idx < 26:  # Only handle A-Z columns
                            worksheet.column_dimensions[chr(65 + col_idx)].width = min(column_length + 2, 50)
                    except Exception as e:
                        self.logger.warning(f"열 너비 조정 실패 ({column}): {e}")
            else:
                self.logger.warning("평가요소별 상세 데이터가 없어 해당 시트를 생성하지 않습니다.")
                
        except Exception as e:
            raise Exception(f"평가요소별 상세 시트 생성 실패: {e}")
    
    def _create_summary_sheet(self, results: List[GradingResult], writer: pd.ExcelWriter):
        """Create summary statistics sheet."""
        import statistics
        
        # Overall statistics
        total_students = len(results)
        avg_score = statistics.mean([r.percentage for r in results])
        median_score = statistics.median([r.percentage for r in results])
        std_score = statistics.stdev([r.percentage for r in results]) if len(results) > 1 else 0
        avg_time = statistics.mean([r.grading_time_seconds for r in results])
        total_time = sum([r.grading_time_seconds for r in results])
        
        # Grade distribution
        grade_counts = {}
        for result in results:
            grade = result.grade_letter
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        # Create summary data
        summary_data = [
            ['전체 통계', ''],
            ['총 학생 수', total_students],
            ['평균 점수 (%)', round(avg_score, 1)],
            ['중앙값 (%)', round(median_score, 1)],
            ['표준편차', round(std_score, 1)],
            ['평균 채점시간 (초)', round(avg_time, 1)],
            ['총 채점시간 (초)', round(total_time, 1)],
            ['', ''],
            ['등급 분포', '학생 수'],
        ]
        
        for grade in ['A', 'B', 'C', 'D', 'F']:
            count = grade_counts.get(grade, 0)
            percentage = (count / total_students * 100) if total_students > 0 else 0
            summary_data.append([f'{grade}등급', f'{count}명 ({percentage:.1f}%)'])
        
        # Element performance statistics
        if results and results[0].element_scores:
            summary_data.extend([
                ['', ''],
                ['평가요소별 통계', '평균 점수 (%)']
            ])
            
            # Collect element performance data
            element_data = {}
            for result in results:
                for element in result.element_scores:
                    if element.element_name not in element_data:
                        element_data[element.element_name] = []
                    element_data[element.element_name].append(element.percentage)
            
            # Calculate element statistics
            for element_name, percentages in element_data.items():
                avg_element_score = statistics.mean(percentages)
                summary_data.append([element_name, round(avg_element_score, 1)])
        
        # Create DataFrame and save
        df_summary = pd.DataFrame(summary_data, columns=['항목', '값'])
        df_summary.to_excel(writer, sheet_name='요약통계', index=False)
        
        # Format the worksheet
        worksheet = writer.sheets['요약통계']
        worksheet.column_dimensions['A'].width = 25
        worksheet.column_dimensions['B'].width = 20
    
    def _create_feedback_sheet(self, results: List[GradingResult], writer: pd.ExcelWriter):
        """Create detailed feedback sheet."""
        try:
            feedback_data = []
            
            for result in results:
                # Overall feedback
                if result.overall_feedback and result.overall_feedback.strip():
                    feedback_data.append({
                        '학생명': result.student_name or '',
                        '반': result.student_class_number or '',
                        '원본답안': result.original_answer or '[답안 없음]',
                        '피드백유형': '전체피드백',
                        '평가요소': '전체',
                        '피드백내용': result.overall_feedback,
                        '점수': f'{result.total_score}/{result.total_max_score}',
                        '백분율': round(result.percentage, 1)
                    })
                
                # Element-specific feedback
                for element in result.element_scores:
                    if element.feedback and element.feedback.strip():
                        feedback_data.append({
                            '학생명': result.student_name or '',
                            '반': result.student_class_number or '',
                            '원본답안': result.original_answer or '[답안 없음]',
                            '피드백유형': '요소별피드백',
                            '평가요소': element.element_name or '',
                            '피드백내용': element.feedback,
                            '점수': f'{element.score}/{element.max_score}',
                            '백분율': round(element.percentage, 1)
                        })
            
            if feedback_data:
                df_feedback = pd.DataFrame(feedback_data)
                df_feedback.to_excel(writer, sheet_name='상세피드백', index=False)
                
                # Format the worksheet
                worksheet = writer.sheets['상세피드백']
                
                # Set column widths with error handling
                column_widths = {
                    'A': 15,  # 학생명
                    'B': 10,  # 반
                    'C': 40,  # 원본답안
                    'D': 15,  # 피드백유형
                    'E': 20,  # 평가요소
                    'F': 60,  # 피드백내용
                    'G': 15,  # 점수
                    'H': 10   # 백분율
                }
                
                for col, width in column_widths.items():
                    try:
                        worksheet.column_dimensions[col].width = width
                    except Exception as e:
                        self.logger.warning(f"열 너비 설정 실패 ({col}): {e}")
            else:
                self.logger.warning("피드백 데이터가 없어 상세피드백 시트를 생성하지 않습니다.")
                
        except Exception as e:
            raise Exception(f"상세피드백 시트 생성 실패: {e}")
    
    def format_results_for_export(self, results: List[GradingResult]) -> Dict[str, Any]:
        """
        Format results data for various export purposes.
        
        Args:
            results: List of grading results
            
        Returns:
            Dict containing formatted data for export
        """
        if not results:
            return {}
        
        import statistics
        
        # Calculate summary statistics
        total_students = len(results)
        percentages = [r.percentage for r in results]
        times = [r.grading_time_seconds for r in results]
        
        summary_stats = {
            'total_students': total_students,
            'average_score': statistics.mean(percentages),
            'median_score': statistics.median(percentages),
            'std_deviation': statistics.stdev(percentages) if len(percentages) > 1 else 0,
            'min_score': min(percentages),
            'max_score': max(percentages),
            'average_time': statistics.mean(times),
            'total_time': sum(times)
        }
        
        # Grade distribution
        grade_distribution = {}
        for result in results:
            grade = result.grade_letter
            grade_distribution[grade] = grade_distribution.get(grade, 0) + 1
        
        # Element performance
        element_performance = {}
        if results[0].element_scores:
            for result in results:
                for element in result.element_scores:
                    if element.element_name not in element_performance:
                        element_performance[element.element_name] = []
                    element_performance[element.element_name].append(element.percentage)
            
            # Calculate element statistics
            for element_name in element_performance:
                percentages = element_performance[element_name]
                element_performance[element_name] = {
                    'average': statistics.mean(percentages),
                    'median': statistics.median(percentages),
                    'std_deviation': statistics.stdev(percentages) if len(percentages) > 1 else 0,
                    'min': min(percentages),
                    'max': max(percentages)
                }
        
        # Student details
        student_details = []
        for result in results:
            student_detail = {
                'name': result.student_name,
                'class_number': result.student_class_number,
                'original_answer': result.original_answer,
                'total_score': result.total_score,
                'total_max_score': result.total_max_score,
                'percentage': result.percentage,
                'grade': result.grade_letter,
                'grading_time': result.grading_time_seconds,
                'graded_at': result.graded_at.isoformat() if result.graded_at else None,
                'overall_feedback': result.overall_feedback,
                'element_scores': [
                    {
                        'element_name': element.element_name,
                        'score': element.score,
                        'max_score': element.max_score,
                        'percentage': element.percentage,
                        'feedback': element.feedback
                    }
                    for element in result.element_scores
                ]
            }
            student_details.append(student_detail)
        
        return {
            'summary_statistics': summary_stats,
            'grade_distribution': grade_distribution,
            'element_performance': element_performance,
            'student_details': student_details,
            'export_timestamp': datetime.now().isoformat()
        }
    
    def generate_download_link(self, file_path: str) -> str:
        """
        Generate download link for exported file.
        
        Args:
            file_path: Path to the file to download
            
        Returns:
            str: Download link or file path
        """
        # In a real implementation, this would generate a proper download URL
        # For Streamlit, we'll return the file path for use with st.download_button
        return file_path


def create_export_service() -> ExportService:
    """
    Factory function to create ExportService instance.
    
    Returns:
        ExportService: Configured ExportService instance
    """
    return ExportService()