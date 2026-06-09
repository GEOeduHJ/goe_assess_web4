"""Sequential grading engine for geography auto-grading."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from config import config
from models.result_model import GradingResult
from models.rubric_model import Rubric
from models.student_model import Student
from services.llm_service import GradingType, LLMService
from services.rag_service import RAGService

logger = logging.getLogger(__name__)


class GradingStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StudentGradingStatus:
    student: Student
    status: GradingStatus = GradingStatus.NOT_STARTED
    result: Optional[GradingResult] = None
    error_message: Optional[str] = None
    attempt_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def processing_time(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


@dataclass
class GradingProgress:
    total_students: int
    completed_students: int = 0
    failed_students: int = 0
    current_student_index: int = 0
    start_time: Optional[datetime] = None
    estimated_completion_time: Optional[float] = None
    average_processing_time: float = 0.0
    current_student_name: str = ""
    current_student_class: str = ""

    @property
    def progress_percentage(self) -> float:
        if self.total_students == 0:
            return 0.0
        return ((self.completed_students + self.failed_students) / self.total_students) * 100

    @property
    def remaining_students(self) -> int:
        return self.total_students - self.completed_students - self.failed_students

    def update_estimates(self, processing_times: List[float]) -> None:
        if processing_times:
            self.average_processing_time = sum(processing_times) / len(processing_times)
            if self.remaining_students > 0:
                self.estimated_completion_time = time.time() + self.remaining_students * self.average_processing_time


class SequentialGradingEngine:
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()
        self.is_cancelled = False
        self.current_batch_id = None
        self.student_statuses: List[StudentGradingStatus] = []
        self.progress: Optional[GradingProgress] = None
        self.progress_callback: Optional[Callable[[GradingProgress], None]] = None
        self.student_completed_callback: Optional[Callable[[StudentGradingStatus], None]] = None
        self.grading_completed_callback: Optional[Callable[[int], None]] = None
        self.error_callback: Optional[Callable[[str, Exception], None]] = None

    def set_progress_callback(self, callback: Callable[[GradingProgress], None]):
        self.progress_callback = callback

    def set_student_completed_callback(self, callback: Callable[[StudentGradingStatus], None]):
        self.student_completed_callback = callback

    def set_grading_completed_callback(self, callback: Callable[[int], None]):
        self.grading_completed_callback = callback

    def set_error_callback(self, callback: Callable[[str, Exception], None]):
        self.error_callback = callback

    def cancel_grading(self):
        self.is_cancelled = True
        logger.info("Grading cancellation requested")

    def grade_students_sequential(
        self,
        students: List[Student],
        rubric: Rubric,
        model_type: str,
        grading_type: str,
        references: Optional[List[str]] = None,
        max_retries: Optional[int] = None,
        uploaded_files: Optional[List] = None,
        reference_image_path: Optional[str] = None,
    ) -> List[GradingResult]:
        self.current_batch_id = f"batch_{int(time.time())}"
        self.is_cancelled = False
        max_retries = max_retries or config.MAX_RETRIES
        self._initialize_progress_tracking(students)

        rag_service = None
        if grading_type == GradingType.DESCRIPTIVE and uploaded_files:
            rag_service = RAGService()
            if not rag_service.process_documents(uploaded_files):
                rag_service = None

        results: List[GradingResult] = []
        processing_times: List[float] = []
        for index, student_status in enumerate(self.student_statuses):
            if self.is_cancelled:
                student_status.status = GradingStatus.CANCELLED
                break

            assert self.progress is not None
            self.progress.current_student_index = index
            self.progress.current_student_name = student_status.student.name
            self.progress.current_student_class = student_status.student.class_number
            self._notify_progress_update()

            result = self._grade_student_with_retries(
                student_status=student_status,
                rubric=rubric,
                model_type=model_type,
                grading_type=grading_type,
                references=references,
                max_retries=max_retries,
                uploaded_files=uploaded_files,
                rag_service=rag_service,
                reference_image_path=reference_image_path,
            )
            if result is None:
                result = self._create_failed_result(student_status.student, rubric, "No grading result was produced")
                student_status.result = result
                student_status.status = GradingStatus.FAILED

            results.append(result)
            processing_times.append(result.grading_time_seconds)
            if student_status.status == GradingStatus.COMPLETED and self._is_success_result(result):
                self.progress.completed_students += 1
            else:
                self.progress.failed_students += 1

            self.progress.update_estimates(processing_times)
            self._notify_progress_update()
            if self.student_completed_callback:
                self.student_completed_callback(student_status)

        if self.progress and not self.is_cancelled and self.grading_completed_callback:
            self.grading_completed_callback(len(results))
        return results

    def _initialize_progress_tracking(self, students: List[Student]):
        self.progress = GradingProgress(total_students=len(students), start_time=datetime.now())
        self.student_statuses = [StudentGradingStatus(student=student) for student in students]

    def _is_success_result(self, result: GradingResult) -> bool:
        if getattr(result, "status", "success") != "success":
            return False
        return "채점 중 오류가 발생했습니다" not in (result.overall_feedback or "")

    def _create_failed_result(self, student: Student, rubric: Rubric, error_message: str, elapsed: float = 0.0) -> GradingResult:
        result = GradingResult(
            student_name=student.name,
            student_class_number=student.class_number,
            original_answer=student.answer or student.image_path or "",
            grading_time_seconds=elapsed,
            overall_feedback=f"채점 중 오류가 발생했습니다: {error_message}",
            status="failed",
            error_message=error_message,
        )
        for element in rubric.elements:
            result.add_element_score(
                element_name=element.name,
                score=0,
                max_score=element.max_score,
                feedback="채점 오류로 인해 점수를 부여할 수 없습니다.",
                reasoning="최대 재시도 후에도 채점 처리 실패",
            )
        return result

    def _grade_student_with_retries(
        self,
        student_status: StudentGradingStatus,
        rubric: Rubric,
        model_type: str,
        grading_type: str,
        references: Optional[List[str]],
        max_retries: int,
        uploaded_files: Optional[List] = None,
        rag_service: Optional[RAGService] = None,
        reference_image_path: Optional[str] = None,
    ) -> Optional[GradingResult]:
        student = student_status.student
        for attempt in range(max_retries + 1):
            if self.is_cancelled:
                student_status.status = GradingStatus.CANCELLED
                return None
            student_status.attempt_count = attempt + 1
            student_status.status = GradingStatus.IN_PROGRESS
            student_status.start_time = datetime.now()
            try:
                processed_references = references
                if grading_type == GradingType.DESCRIPTIVE and student.has_text_answer:
                    if rag_service and rag_service.vector_store:
                        retrieved = rag_service.search_relevant_content(student.answer)
                        if retrieved:
                            processed_references = retrieved
                    elif uploaded_files:
                        fallback_rag = RAGService()
                        rag_result = fallback_rag.process_documents_for_student(uploaded_files, student.answer)
                        if rag_result.success:
                            processed_references = rag_result.content

                result = self.llm_service.grade_student_sequential(
                    student=student,
                    rubric=rubric,
                    model_type=model_type,
                    grading_type=grading_type,
                    references=processed_references,
                    reference_image_path=reference_image_path,
                )
                student_status.end_time = datetime.now()
                student_status.result = result
                if self._is_success_result(result):
                    student_status.status = GradingStatus.COMPLETED
                    return result
                raise Exception(result.error_message or result.overall_feedback)
            except Exception as exc:
                student_status.end_time = datetime.now()
                student_status.error_message = f"Attempt {attempt + 1} failed: {exc}"
                if attempt < max_retries:
                    time.sleep(config.RETRY_DELAY ** attempt)
                    continue
                student_status.status = GradingStatus.FAILED
                if self.error_callback:
                    self.error_callback(f"Failed to grade student {student.name}", exc)
                failed = self._create_failed_result(student, rubric, str(exc), student_status.processing_time)
                student_status.result = failed
                return failed
        return None

    def _notify_progress_update(self):
        if self.progress_callback and self.progress:
            self.progress_callback(self.progress)

    def get_grading_summary(self) -> Dict[str, Any]:
        if not self.progress or not self.student_statuses:
            return {"error": "No grading session in progress"}
        return {
            "batch_id": self.current_batch_id,
            "total_students": self.progress.total_students,
            "completed_students": self.progress.completed_students,
            "failed_students": self.progress.failed_students,
            "progress_percentage": self.progress.progress_percentage,
            "average_processing_time": self.progress.average_processing_time,
            "success_rate": (self.progress.completed_students / self.progress.total_students * 100) if self.progress.total_students > 0 else 0.0,
            "is_cancelled": self.is_cancelled,
            "start_time": self.progress.start_time.isoformat() if self.progress.start_time else None,
            "estimated_completion": self.progress.estimated_completion_time,
            "student_details": [
                {
                    "student_name": status.student.name,
                    "status": status.status.value,
                    "attempt_count": status.attempt_count,
                    "processing_time": status.processing_time,
                    "error_message": status.error_message,
                    "total_score": status.result.total_score if status.result else None,
                    "total_max_score": status.result.total_max_score if status.result else None,
                    "percentage": status.result.percentage if status.result else None,
                    "grade_letter": status.result.grade_letter if status.result else None,
                }
                for status in self.student_statuses
            ],
        }

    def get_successful_results(self) -> List[GradingResult]:
        return [status.result for status in self.student_statuses if status.status == GradingStatus.COMPLETED and status.result]

    def get_failed_students(self) -> List[StudentGradingStatus]:
        return [status for status in self.student_statuses if status.status == GradingStatus.FAILED]

    def retry_failed_students(
        self,
        rubric: Rubric,
        model_type: str,
        grading_type: str,
        references: Optional[List[str]] = None,
        max_retries: Optional[int] = None,
        uploaded_files: Optional[List] = None,
        reference_image_path: Optional[str] = None,
    ) -> List[GradingResult]:
        failed_statuses = self.get_failed_students()
        new_results: List[GradingResult] = []
        max_retries = max_retries or config.MAX_RETRIES
        for status in failed_statuses:
            status.status = GradingStatus.NOT_STARTED
            status.error_message = None
            status.attempt_count = 0
            result = self._grade_student_with_retries(
                student_status=status,
                rubric=rubric,
                model_type=model_type,
                grading_type=grading_type,
                references=references,
                max_retries=max_retries,
                uploaded_files=uploaded_files,
                rag_service=None,
                reference_image_path=reference_image_path,
            )
            if result:
                new_results.append(result)
                if self.progress and self._is_success_result(result):
                    self.progress.completed_students += 1
                    self.progress.failed_students = max(0, self.progress.failed_students - 1)
        return new_results

    def validate_grading_setup(self, students: List[Student], rubric: Rubric, model_type: str, grading_type: str) -> Dict[str, Any]:
        validation_results = {"valid": True, "errors": [], "warnings": []}
        if not students:
            validation_results["errors"].append("No students provided for grading")
            validation_results["valid"] = False
        for index, student in enumerate(students):
            try:
                student._validate_data()
            except ValueError as exc:
                validation_results["errors"].append(f"Student {index + 1} ({student.name}): {exc}")
                validation_results["valid"] = False
        if not rubric.elements:
            validation_results["errors"].append("Rubric has no evaluation elements")
            validation_results["valid"] = False
        api_status = self.llm_service.validate_api_availability()
        if model_type not in api_status:
            validation_results["errors"].append(f"Unsupported model type: {model_type}")
            validation_results["valid"] = False
        elif not api_status[model_type]:
            validation_results["errors"].append(f"{model_type} API not available")
            validation_results["valid"] = False
        if len(students) > 50:
            validation_results["warnings"].append(f"Large batch size ({len(students)} students) may take significant time")
        if grading_type == GradingType.MAP:
            missing_images = [student.name for student in students if not student.has_image_answer]
            if missing_images:
                validation_results["warnings"].append(f"Students without images: {', '.join(missing_images[:5])}")
        return validation_results
