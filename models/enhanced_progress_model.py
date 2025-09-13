"""
Enhanced Progress Models for Real-time Grading Feedback

This module extends the existing progress tracking models with enhanced
real-time feedback capabilities, current operation tracking, and detailed
student-level progress information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from models.student_model import Student
from services.grading_engine import GradingProgress, StudentGradingStatus, GradingStatus


class OperationType(Enum):
    """Enumeration for current operation types."""
    INITIALIZING = "initializing"
    RAG_PROCESSING = "rag_processing"
    GRADING = "grading"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class EnhancedGradingProgress(GradingProgress):
    """
    Enhanced grading progress with detailed operation tracking.
    
    Extends the base GradingProgress with current student information,
    operation tracking, and enhanced time estimates.
    """
    current_student_name: str = ""
    current_student_class: str = ""
    current_operation: OperationType = OperationType.INITIALIZING
    operation_start_time: Optional[datetime] = None
    
    # Enhanced tracking
    rag_warnings: List[str] = field(default_factory=list)
    processing_errors: List[str] = field(default_factory=list)
    operation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance metrics
    rag_processing_times: List[float] = field(default_factory=list)
    grading_times: List[float] = field(default_factory=list)
    
    def update_current_student(self, student: Student, operation: OperationType):
        """Update current student and operation information."""
        self.current_student_name = student.name
        self.current_student_class = student.class_number
        self.current_operation = operation
        self.operation_start_time = datetime.now()
        
        # Add to operation history
        self.operation_history.append({
            "timestamp": self.operation_start_time,
            "student_name": student.name,
            "operation": operation.value,
            "student_index": self.current_student_index
        })
    
    def add_rag_warning(self, student_name: str, warning_message: str):
        """Add RAG processing warning."""
        warning = f"{student_name}: {warning_message}"
        self.rag_warnings.append(warning)
        
        # Add to operation history
        self.operation_history.append({
            "timestamp": datetime.now(),
            "student_name": student_name,
            "operation": "rag_warning",
            "details": warning_message
        })
    
    def add_processing_error(self, student_name: str, error_message: str):
        """Add processing error."""
        error = f"{student_name}: {error_message}"
        self.processing_errors.append(error)
        
        # Add to operation history
        self.operation_history.append({
            "timestamp": datetime.now(),
            "student_name": student_name,
            "operation": "error",
            "details": error_message
        })
    
    def record_rag_time(self, processing_time: float):
        """Record RAG processing time."""
        self.rag_processing_times.append(processing_time)
    
    def record_grading_time(self, grading_time: float):
        """Record grading time."""
        self.grading_times.append(grading_time)
    
    @property
    def average_rag_time(self) -> float:
        """Calculate average RAG processing time."""
        if not self.rag_processing_times:
            return 0.0
        return sum(self.rag_processing_times) / len(self.rag_processing_times)
    
    @property
    def average_grading_time(self) -> float:
        """Calculate average grading time."""
        if not self.grading_times:
            return 0.0
        return sum(self.grading_times) / len(self.grading_times)
    
    @property
    def current_operation_duration(self) -> float:
        """Get current operation duration in seconds."""
        if not self.operation_start_time:
            return 0.0
        return (datetime.now() - self.operation_start_time).total_seconds()
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.rag_warnings) > 0
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.processing_errors) > 0
    
    def get_recent_operations(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent operations from history."""
        return self.operation_history[-count:] if self.operation_history else []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        base_dict = {
            'total_students': self.total_students,
            'completed_students': self.completed_students,
            'failed_students': self.failed_students,
            'current_student_index': self.current_student_index,
            'progress_percentage': self.progress_percentage,
            'remaining_students': self.remaining_students,
            'current_student_name': self.current_student_name,
            'current_student_class': self.current_student_class,
            'current_operation': self.current_operation.value,
            'current_operation_duration': self.current_operation_duration,
            'average_processing_time': self.average_processing_time,
            'average_rag_time': self.average_rag_time,
            'average_grading_time': self.average_grading_time,
            'has_warnings': self.has_warnings,
            'has_errors': self.has_errors,
            'rag_warnings_count': len(self.rag_warnings),
            'processing_errors_count': len(self.processing_errors)
        }
        
        if self.start_time:
            base_dict['start_time'] = self.start_time.isoformat()
        
        if self.estimated_completion_time:
            base_dict['estimated_completion_time'] = self.estimated_completion_time.isoformat()
        
        return base_dict


@dataclass
class StudentProgressDetail:
    """
    Detailed progress information for individual students.
    """
    student: Student
    status: GradingStatus = GradingStatus.NOT_STARTED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Operation tracking
    rag_start_time: Optional[datetime] = None
    rag_end_time: Optional[datetime] = None
    rag_success: bool = False
    rag_error: Optional[str] = None
    
    grading_start_time: Optional[datetime] = None
    grading_end_time: Optional[datetime] = None
    grading_success: bool = False
    grading_error: Optional[str] = None
    
    # Results
    final_score: Optional[float] = None
    max_score: Optional[float] = None
    grade_letter: Optional[str] = None
    
    @property
    def total_processing_time(self) -> float:
        """Get total processing time in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def rag_processing_time(self) -> float:
        """Get RAG processing time in seconds."""
        if self.rag_start_time and self.rag_end_time:
            return (self.rag_end_time - self.rag_start_time).total_seconds()
        return 0.0
    
    @property
    def grading_processing_time(self) -> float:
        """Get grading processing time in seconds."""
        if self.grading_start_time and self.grading_end_time:
            return (self.grading_end_time - self.grading_start_time).total_seconds()
        return 0.0
    
    @property
    def percentage_score(self) -> float:
        """Get percentage score."""
        if self.final_score is not None and self.max_score and self.max_score > 0:
            return (self.final_score / self.max_score) * 100
        return 0.0
    
    def start_rag_processing(self):
        """Mark RAG processing start."""
        self.rag_start_time = datetime.now()
        if not self.start_time:
            self.start_time = self.rag_start_time
    
    def complete_rag_processing(self, success: bool, error: Optional[str] = None):
        """Mark RAG processing completion."""
        self.rag_end_time = datetime.now()
        self.rag_success = success
        self.rag_error = error
    
    def start_grading(self):
        """Mark grading start."""
        self.grading_start_time = datetime.now()
        if not self.start_time:
            self.start_time = self.grading_start_time
    
    def complete_grading(self, success: bool, error: Optional[str] = None, 
                        score: Optional[float] = None, max_score: Optional[float] = None,
                        grade_letter: Optional[str] = None):
        """Mark grading completion."""
        self.grading_end_time = datetime.now()
        self.end_time = self.grading_end_time
        self.grading_success = success
        self.grading_error = error
        self.final_score = score
        self.max_score = max_score
        self.grade_letter = grade_letter
        
        if success:
            self.status = GradingStatus.COMPLETED
        else:
            self.status = GradingStatus.FAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'student_name': self.student.name,
            'student_class': self.student.class_number,
            'status': self.status.value,
            'total_processing_time': self.total_processing_time,
            'rag_processing_time': self.rag_processing_time,
            'grading_processing_time': self.grading_processing_time,
            'rag_success': self.rag_success,
            'rag_error': self.rag_error,
            'grading_success': self.grading_success,
            'grading_error': self.grading_error,
            'final_score': self.final_score,
            'max_score': self.max_score,
            'percentage_score': self.percentage_score,
            'grade_letter': self.grade_letter,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }


@dataclass
class BatchProgressTracker:
    """
    Tracks progress for a batch of students with detailed metrics.
    """
    batch_id: str
    students: List[Student]
    student_details: Dict[str, StudentProgressDetail] = field(default_factory=dict)
    overall_progress: Optional[EnhancedGradingProgress] = None
    
    def __post_init__(self):
        """Initialize student details."""
        for student in self.students:
            self.student_details[student.name] = StudentProgressDetail(student=student)
        
        # Initialize overall progress
        self.overall_progress = EnhancedGradingProgress(
            total_students=len(self.students)
        )
    
    def get_student_detail(self, student_name: str) -> Optional[StudentProgressDetail]:
        """Get student detail by name."""
        return self.student_details.get(student_name)
    
    def update_student_status(self, student_name: str, status: GradingStatus):
        """Update student status."""
        if student_name in self.student_details:
            self.student_details[student_name].status = status
            self._update_overall_progress()
    
    def start_student_rag(self, student_name: str):
        """Mark student RAG processing start."""
        detail = self.student_details.get(student_name)
        if detail:
            detail.start_rag_processing()
            detail.status = GradingStatus.IN_PROGRESS
            self._update_overall_progress()
    
    def complete_student_rag(self, student_name: str, success: bool, error: Optional[str] = None):
        """Mark student RAG processing completion."""
        detail = self.student_details.get(student_name)
        if detail:
            detail.complete_rag_processing(success, error)
            if not success and self.overall_progress:
                self.overall_progress.add_rag_warning(student_name, error or "RAG processing failed")
    
    def start_student_grading(self, student_name: str):
        """Mark student grading start."""
        detail = self.student_details.get(student_name)
        if detail:
            detail.start_grading()
            detail.status = GradingStatus.IN_PROGRESS
            self._update_overall_progress()
    
    def complete_student_grading(self, student_name: str, success: bool, 
                               error: Optional[str] = None, score: Optional[float] = None,
                               max_score: Optional[float] = None, grade_letter: Optional[str] = None):
        """Mark student grading completion."""
        detail = self.student_details.get(student_name)
        if detail:
            detail.complete_grading(success, error, score, max_score, grade_letter)
            if not success and self.overall_progress:
                self.overall_progress.add_processing_error(student_name, error or "Grading failed")
            self._update_overall_progress()
    
    def _update_overall_progress(self):
        """Update overall progress based on student details."""
        if not self.overall_progress:
            return
        
        completed = sum(1 for detail in self.student_details.values() 
                       if detail.status == GradingStatus.COMPLETED)
        failed = sum(1 for detail in self.student_details.values() 
                    if detail.status == GradingStatus.FAILED)
        
        self.overall_progress.completed_students = completed
        self.overall_progress.failed_students = failed
        
        # Update processing times
        completed_details = [detail for detail in self.student_details.values() 
                           if detail.status == GradingStatus.COMPLETED]
        
        if completed_details:
            total_times = [detail.total_processing_time for detail in completed_details]
            rag_times = [detail.rag_processing_time for detail in completed_details 
                        if detail.rag_processing_time > 0]
            grading_times = [detail.grading_processing_time for detail in completed_details 
                           if detail.grading_processing_time > 0]
            
            if total_times:
                self.overall_progress.average_processing_time = sum(total_times) / len(total_times)
            
            if rag_times:
                self.overall_progress.rag_processing_times = rag_times
            
            if grading_times:
                self.overall_progress.grading_times = grading_times
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get comprehensive progress summary."""
        return {
            'batch_id': self.batch_id,
            'overall_progress': self.overall_progress.to_dict() if self.overall_progress else None,
            'student_details': [detail.to_dict() for detail in self.student_details.values()],
            'completion_rate': (self.overall_progress.completed_students / len(self.students) * 100) 
                             if self.overall_progress and self.students else 0,
            'failure_rate': (self.overall_progress.failed_students / len(self.students) * 100) 
                          if self.overall_progress and self.students else 0
        }