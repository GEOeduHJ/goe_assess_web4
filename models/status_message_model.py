"""
Status Message Models for Real-time UI Feedback

This module defines data models for status messages, error notifications,
and communication between grading threads and UI components.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class MessageType(Enum):
    """Enumeration for message types."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class ErrorSeverity(Enum):
    """Enumeration for error severity levels."""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class StatusMessage:
    """
    Represents a status message for UI display.
    
    Attributes:
        message_type: Type of message (info, success, warning, error)
        title: Message title
        content: Message content
        timestamp: When the message was created
        student_name: Associated student name (optional)
        auto_dismiss: Whether message should auto-dismiss
        dismiss_after: Seconds after which to auto-dismiss
    """
    message_type: MessageType
    title: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    student_name: Optional[str] = None
    auto_dismiss: bool = True
    dismiss_after: int = 5  # seconds
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'message_type': self.message_type.value,
            'title': self.title,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'student_name': self.student_name,
            'auto_dismiss': self.auto_dismiss,
            'dismiss_after': self.dismiss_after
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'StatusMessage':
        """Create from dictionary."""
        return cls(
            message_type=MessageType(data['message_type']),
            title=data['title'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            student_name=data.get('student_name'),
            auto_dismiss=data.get('auto_dismiss', True),
            dismiss_after=data.get('dismiss_after', 5)
        )


@dataclass
class ErrorNotification:
    """
    Represents an error notification with recovery suggestions.
    
    Attributes:
        error_type: Type of error (rag_failure, grading_failure, system_error)
        student_name: Name of student associated with error
        error_message: Brief error message
        error_details: Detailed error information
        timestamp: When the error occurred
        severity: Error severity level
        suggested_actions: List of suggested recovery actions
    """
    error_type: str
    student_name: str
    error_message: str
    error_details: str
    timestamp: datetime = field(default_factory=datetime.now)
    severity: ErrorSeverity = ErrorSeverity.ERROR
    suggested_actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'error_type': self.error_type,
            'student_name': self.student_name,
            'error_message': self.error_message,
            'error_details': self.error_details,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity.value,
            'suggested_actions': self.suggested_actions
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ErrorNotification':
        """Create from dictionary."""
        return cls(
            error_type=data['error_type'],
            student_name=data['student_name'],
            error_message=data['error_message'],
            error_details=data['error_details'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            severity=ErrorSeverity(data.get('severity', 'error')),
            suggested_actions=data.get('suggested_actions', [])
        )


@dataclass
class ProgressUpdate:
    """
    Represents a progress update message.
    
    Attributes:
        current_student_name: Name of currently processing student
        current_student_index: Index of current student
        current_operation: Current operation being performed
        completed_count: Number of completed students
        total_count: Total number of students
        failed_count: Number of failed students
        estimated_completion: Estimated completion time
        average_time: Average processing time per student
    """
    current_student_name: str
    current_student_index: int
    current_operation: str
    completed_count: int
    total_count: int
    failed_count: int = 0
    estimated_completion: Optional[float] = None
    average_time: float = 0.0
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_count == 0:
            return 0.0
        return ((self.completed_count + self.failed_count) / self.total_count) * 100
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'current_student_name': self.current_student_name,
            'current_student_index': self.current_student_index,
            'current_operation': self.current_operation,
            'completed_count': self.completed_count,
            'total_count': self.total_count,
            'failed_count': self.failed_count,
            'estimated_completion': self.estimated_completion,
            'average_time': self.average_time,
            'progress_percentage': self.progress_percentage
        }