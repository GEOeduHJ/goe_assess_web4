"""
지리 자동 채점 시스템의 순차 채점 실행 엔진

이 모듈은 실시간 진행 상황 추적, 오류 처리, 재시도 메커니즘을 통해
여러 학생의 채점 프로세스를 조율하는 핵심 순차 채점 실행 엔진을 제공합니다.
"""

import time
import logging
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from models.student_model import Student
from models.rubric_model import Rubric
from models.result_model import GradingResult, GradingTimer
from services.llm_service import LLMService, GradingType
from services.rag_service import RAGService, format_retrieved_content
from config import config


# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GradingStatus(Enum):
    """채점 상태를 나타내는 열거형"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StudentGradingStatus:
    """
    개별 학생의 채점 상태를 나타냅니다.
    
    Attributes:
        student: 채점 중인 학생
        status: 현재 채점 상태
        result: 채점 결과 (완료된 경우)
        error_message: 오류 메시지 (실패한 경우)
        attempt_count: 채점 시도 횟수
        start_time: 채점 시작 시간
        end_time: 채점 완료/실패 시간
    """
    student: Student
    status: GradingStatus = GradingStatus.NOT_STARTED
    result: Optional[GradingResult] = None
    error_message: Optional[str] = None
    attempt_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def processing_time(self) -> float:
        """처리 시간을 초 단위로 가져옵니다."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


@dataclass
class GradingProgress:
    """
    전체 채점 진행 상황을 나타냅니다.
    
    Attributes:
        total_students: 채점할 총 학생 수
        completed_students: 완료된 학생 수
        failed_students: 실패한 학생 수
        current_student_index: 현재 처리 중인 학생 인덱스
        start_time: 배치 채점 시작 시간
        estimated_completion_time: 예상 완료 시간
        average_processing_time: 학생당 평균 처리 시간
    """
    total_students: int
    completed_students: int = 0
    failed_students: int = 0
    current_student_index: int = 0
    start_time: Optional[datetime] = None
    estimated_completion_time: Optional[datetime] = None
    average_processing_time: float = 0.0
    
    @property
    def progress_percentage(self) -> float:
        """진행률 퍼센트를 계산합니다."""
        if self.total_students == 0:
            return 0.0
        return ((self.completed_students + self.failed_students) / self.total_students) * 100
    
    @property
    def remaining_students(self) -> int:
        """남은 학생 수를 가져옵니다."""
        return self.total_students - self.completed_students - self.failed_students
    
    def update_estimates(self, processing_times: List[float]):
        """완료된 처리 시간을 기반으로 시간 추정치를 업데이트합니다."""
        if processing_times:
            self.average_processing_time = sum(processing_times) / len(processing_times)
            
            if self.remaining_students > 0:
                estimated_remaining_seconds = self.remaining_students * self.average_processing_time
                self.estimated_completion_time = datetime.now().timestamp() + estimated_remaining_seconds


class SequentialGradingEngine:
    """
    진행 상황 추적 및 오류 처리 기능이 있는 순차 채점 실행 엔진
    
    이 엔진은 여러 학생의 채점 프로세스를 조율하며,
    실시간 진행 상황 업데이트, 오류 복구, 상세 로깅을 제공합니다.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        채점 엔진을 초기화합니다.
        
        Args:
            llm_service: 선택적 LLM 서비스 인스턴스 (제공되지 않으면 새로 생성)
        """
        self.llm_service = llm_service or LLMService()
        self.is_cancelled = False
        self.current_batch_id = None
        
        # 진행 상황 추적
        self.student_statuses: List[StudentGradingStatus] = []
        self.progress: Optional[GradingProgress] = None
        
        # Callbacks
        self.progress_callback: Optional[Callable] = None
        self.student_completed_callback: Optional[Callable] = None
        self.grading_completed_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable[[GradingProgress], None]):
        """Set callback for progress updates."""
        self.progress_callback = callback
    
    def set_student_completed_callback(self, callback: Callable[[StudentGradingStatus], None]):
        """Set callback for individual student completion."""
        self.student_completed_callback = callback
    
    def set_grading_completed_callback(self, callback: Callable[[int], None]):
        """Set callback for overall grading completion."""
        self.grading_completed_callback = callback
    
    def set_error_callback(self, callback: Callable[[str, Exception], None]):
        """Set callback for error handling."""
        self.error_callback = callback
    
    def cancel_grading(self):
        """Cancel the current grading process."""
        self.is_cancelled = True
        logger.info("Grading process cancellation requested")
    
    def grade_students_sequential(
        self,
        students: List[Student],
        rubric: Rubric,
        model_type: str,
        grading_type: str,
        references: Optional[List[str]] = None,
        groq_model_name: str = "qwen/qwen3-32b",
        max_retries: Optional[int] = None,
        uploaded_files: Optional[List] = None  # New parameter for on-demand RAG processing
    ) -> List[GradingResult]:
        """
        Grade multiple students sequentially with comprehensive progress tracking.
        
        Args:
            students: List of students to grade
            rubric: Evaluation rubric
            model_type: LLM model to use
            grading_type: Type of grading (descriptive/map)
            references: Reference materials from RAG
            groq_model_name: Specific Groq model to use (default: qwen/qwen3-32b)
            max_retries: Maximum retry attempts per student
            uploaded_files: Uploaded reference files for on-demand RAG processing
            
        Returns:
            List of grading results
        """
        # Initialize grading session
        self.current_batch_id = f"batch_{int(time.time())}"
        self.is_cancelled = False
        max_retries = max_retries or config.MAX_RETRIES
        
        # Initialize progress tracking
        self._initialize_progress_tracking(students)
        
        logger.info(f"Starting sequential grading for {len(students)} students (batch: {self.current_batch_id})")
        
        results = []
        processing_times = []
        
        try:
            for i, student in enumerate(students):
                if self.is_cancelled:
                    logger.info("Grading cancelled by user")
                    break
                
                # Update current student index and info
                self.progress.current_student_index = i
                self.progress.current_student_name = student.name
                self.progress.current_student_class = student.class_number
                self._notify_progress_update()
                
                # Get student status
                student_status = self.student_statuses[i]
                
                # Grade individual student with retries
                result = self._grade_student_with_retries(
                    student_status=student_status,
                    rubric=rubric,
                    model_type=model_type,
                    grading_type=grading_type,
                    references=references,
                    groq_model_name=groq_model_name,
                    max_retries=max_retries,
                    uploaded_files=uploaded_files  # Pass uploaded files for on-demand processing
                )
                
                # Always append result (even error results)
                if result:
                    results.append(result)
                    processing_times.append(result.grading_time_seconds)
                    
                    # Check if this was a successful grading or an error result
                    if student_status.status == GradingStatus.COMPLETED:
                        self.progress.completed_students += 1
                    else:
                        self.progress.failed_students += 1
                else:
                    self.progress.failed_students += 1
                
                # Update time estimates
                self.progress.update_estimates(processing_times)
                
                # Notify callbacks
                self._notify_progress_update()
                if self.student_completed_callback:
                    self.student_completed_callback(student_status)
                
                logger.info(f"Completed {i + 1}/{len(students)} students")
        
        except Exception as e:
            logger.error(f"Critical error in grading process: {e}")
            if self.error_callback:
                self.error_callback("Critical grading error", e)
            raise
        
        finally:
            # Finalize progress and notify completion
            if self.progress:
                if not self.is_cancelled:
                    logger.info(f"Sequential grading completed. {len(results)}/{len(students)} students graded successfully")
                    # Only notify grading completion callback (not progress callback)
                    if self.grading_completed_callback:
                        logger.info(f"Calling grading completion callback with {len(results)} results")
                        self.grading_completed_callback(len(results))
                    else:
                        logger.warning("No grading completion callback set!")
                else:
                    logger.info(f"Sequential grading cancelled. {len(results)}/{len(students)} students completed before cancellation")
        
        return results
    
    def _initialize_progress_tracking(self, students: List[Student]):
        """Initialize progress tracking structures."""
        self.progress = GradingProgress(
            total_students=len(students),
            start_time=datetime.now()
        )
        
        self.student_statuses = [
            StudentGradingStatus(student=student)
            for student in students
        ]
    
    def _grade_student_with_retries(
        self,
        student_status: StudentGradingStatus,
        rubric: Rubric,
        model_type: str,
        grading_type: str,
        references: Optional[List[str]],
        max_retries: int,
        groq_model_name: str = "qwen/qwen3-32b",
        uploaded_files: Optional[List] = None  # New parameter for on-demand RAG processing
    ) -> Optional[GradingResult]:
        """
        Grade a single student with retry mechanism.
        
        Args:
            student_status: Student grading status object
            rubric: Evaluation rubric
            model_type: LLM model to use
            grading_type: Type of grading
            references: Reference materials
            max_retries: Maximum retry attempts
            groq_model_name: Specific Groq model to use (default: qwen/qwen3-32b)
            uploaded_files: Uploaded reference files for on-demand RAG processing
            
        Returns:
            Grading result if successful, None if failed
        """
        student = student_status.student
        
        for attempt in range(max_retries + 1):
            if self.is_cancelled:
                student_status.status = GradingStatus.CANCELLED
                return None
            
            student_status.attempt_count = attempt + 1
            student_status.status = GradingStatus.IN_PROGRESS
            student_status.start_time = datetime.now()
            
            try:
                logger.info(f"Grading student {student.name} (attempt {attempt + 1}/{max_retries + 1})")
                
                # For descriptive grading with uploaded files, process documents on-demand
                processed_references = references
                if grading_type == "descriptive" and uploaded_files and student.has_text_answer:
                    try:
                        rag_service = RAGService()
                        rag_result = rag_service.process_documents_for_student(
                            uploaded_files, 
                            student.answer
                        )
                        
                        if rag_result.success:
                            processed_references = rag_result.content
                        else:
                            logger.warning(f"RAG processing failed for student {student.name}: {rag_result.error_message}")
                    except Exception as e:
                        logger.warning(f"RAG processing error for student {student.name}: {e}")
                
                # Call LLM service for grading
                result = self.llm_service.grade_student_sequential(
                    student=student,
                    rubric=rubric,
                    model_type=model_type,
                    grading_type=grading_type,
                    references=processed_references,
                    groq_model_name=groq_model_name
                )
                
                # Check if this is an error result (total_score = 0 and error message in feedback)
                is_error_result = (
                    result.total_score == 0 and 
                    "채점 중 오류가 발생했습니다" in result.overall_feedback
                )
                
                if is_error_result:
                    # Treat as failure and retry
                    error_msg = result.overall_feedback
                    raise Exception(error_msg)
                
                # Success
                student_status.end_time = datetime.now()
                student_status.status = GradingStatus.COMPLETED
                student_status.result = result
                
                logger.info(f"Successfully graded student {student.name} in {result.grading_time_seconds:.2f}s")
                return result
                
            except Exception as e:
                student_status.end_time = datetime.now()
                error_msg = f"Attempt {attempt + 1} failed: {str(e)}"
                student_status.error_message = error_msg
                
                logger.warning(f"Failed to grade student {student.name} on attempt {attempt + 1}: {e}")
                
                if attempt < max_retries:
                    # Wait before retry with exponential backoff
                    retry_delay = config.RETRY_DELAY ** attempt
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    # Final failure
                    student_status.status = GradingStatus.FAILED
                    logger.error(f"Failed to grade student {student.name} after {max_retries + 1} attempts")
                    
                    if self.error_callback:
                        self.error_callback(f"Failed to grade student {student.name}", e)
                    
                    return None
        
        return None
    
    def _notify_progress_update(self):
        """Notify progress callback if set."""
        if self.progress_callback and self.progress:
            try:
                self.progress_callback(self.progress)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    def get_grading_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive grading summary.
        
        Returns:
            Dictionary with grading statistics and details
        """
        if not self.progress or not self.student_statuses:
            return {"error": "No grading session in progress"}
        
        # Calculate statistics
        successful_results = [s for s in self.student_statuses if s.status == GradingStatus.COMPLETED]
        failed_results = [s for s in self.student_statuses if s.status == GradingStatus.FAILED]
        
        processing_times = [s.result.grading_time_seconds for s in successful_results if s.result]
        
        summary = {
            "batch_id": self.current_batch_id,
            "total_students": self.progress.total_students,
            "completed_students": self.progress.completed_students,
            "failed_students": self.progress.failed_students,
            "progress_percentage": self.progress.progress_percentage,
            "average_processing_time": self.progress.average_processing_time,
            "total_processing_time": sum(processing_times) if processing_times else 0.0,
            "success_rate": (self.progress.completed_students / self.progress.total_students * 100) if self.progress.total_students > 0 else 0.0,
            "is_cancelled": self.is_cancelled,
            "start_time": self.progress.start_time.isoformat() if self.progress.start_time else None,
            "estimated_completion": self.progress.estimated_completion_time if self.progress.estimated_completion_time else None
        }
        
        # Add detailed student results
        summary["student_details"] = []
        for status in self.student_statuses:
            detail = {
                "student_name": status.student.name,
                "status": status.status.value,
                "attempt_count": status.attempt_count,
                "processing_time": status.processing_time,
                "error_message": status.error_message
            }
            
            if status.result:
                detail.update({
                    "total_score": status.result.total_score,
                    "total_max_score": status.result.total_max_score,
                    "percentage": status.result.percentage,
                    "grade_letter": status.result.grade_letter
                })
            
            summary["student_details"].append(detail)
        
        return summary
    
    def get_successful_results(self) -> List[GradingResult]:
        """Get all successful grading results."""
        return [
            status.result 
            for status in self.student_statuses 
            if status.status == GradingStatus.COMPLETED and status.result
        ]
    
    def get_failed_students(self) -> List[StudentGradingStatus]:
        """Get all failed student statuses."""
        return [
            status 
            for status in self.student_statuses 
            if status.status == GradingStatus.FAILED
        ]
    
    def retry_failed_students(
        self,
        rubric: Rubric,
        model_type: str,
        grading_type: str,
        references: Optional[List[str]] = None,
        groq_model_name: str = "qwen/qwen3-32b",
        max_retries: Optional[int] = None,
        uploaded_files: Optional[List] = None  # New parameter for on-demand RAG processing
    ) -> List[GradingResult]:
        """
        Retry grading for failed students only.
        
        Args:
            rubric: Evaluation rubric
            model_type: LLM model to use
            grading_type: Type of grading
            references: Reference materials
            groq_model_name: Specific Groq model to use (default: qwen/qwen3-32b)
            max_retries: Maximum retry attempts
            uploaded_files: Uploaded reference files for on-demand RAG processing
            
        Returns:
            List of newly successful results
        """
        failed_statuses = self.get_failed_students()
        if not failed_statuses:
            logger.info("No failed students to retry")
            return []
        
        logger.info(f"Retrying {len(failed_statuses)} failed students")
        
        new_results = []
        max_retries = max_retries or config.MAX_RETRIES
        
        for status in failed_statuses:
            # Reset status for retry
            status.status = GradingStatus.NOT_STARTED
            status.error_message = None
            status.attempt_count = 0
            
            result = self._grade_student_with_retries(
                student_status=status,
                rubric=rubric,
                model_type=model_type,
                grading_type=grading_type,
                references=references,
                groq_model_name=groq_model_name,
                max_retries=max_retries,
                uploaded_files=uploaded_files  # Pass uploaded files for on-demand processing
            )
            
            if result:
                new_results.append(result)
                self.progress.completed_students += 1
                self.progress.failed_students -= 1
        
        logger.info(f"Retry completed: {len(new_results)} additional students graded successfully")
        return new_results
    
    def validate_grading_setup(
        self,
        students: List[Student],
        rubric: Rubric,
        model_type: str,
        grading_type: str
    ) -> Dict[str, Any]:
        """
        Validate grading setup before starting.
        
        Args:
            students: List of students to validate
            rubric: Rubric to validate
            model_type: Model type to validate
            grading_type: Grading type to validate
            
        Returns:
            Validation results dictionary
        """
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Validate students
        if not students:
            validation_results["errors"].append("No students provided for grading")
            validation_results["valid"] = False
        
        for i, student in enumerate(students):
            try:
                student._validate_data()
            except ValueError as e:
                validation_results["errors"].append(f"Student {i+1} ({student.name}): {e}")
                validation_results["valid"] = False
        
        # Validate rubric
        try:
            if not rubric.elements:
                validation_results["errors"].append("Rubric has no evaluation elements")
                validation_results["valid"] = False
        except Exception as e:
            validation_results["errors"].append(f"Rubric validation failed: {e}")
            validation_results["valid"] = False
        
        # Validate model availability
        api_status = self.llm_service.validate_api_availability()
        
        if model_type == "gemini" and not api_status["gemini"]:
            validation_results["errors"].append("Gemini API not available")
            validation_results["valid"] = False
        
        if model_type == "groq" and not api_status["groq"]:
            validation_results["errors"].append("Groq API not available")
            validation_results["valid"] = False
        
        # Validate grading type compatibility
        if grading_type == GradingType.MAP and model_type == "groq":
            validation_results["errors"].append("Map grading requires Gemini API (image support)")
            validation_results["valid"] = False
        
        # Add warnings
        if len(students) > 50:
            validation_results["warnings"].append(f"Large batch size ({len(students)} students) may take significant time")
        
        if grading_type == GradingType.MAP:
            missing_images = [s.name for s in students if not s.has_image_answer]
            if missing_images:
                validation_results["warnings"].append(f"Students without images: {', '.join(missing_images[:5])}")
        
        return validation_results