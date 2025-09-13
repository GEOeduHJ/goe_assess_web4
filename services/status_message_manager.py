"""
Status Message Manager for Real-time UI Communication

This module manages status messages, error notifications, and progress updates
between the grading engine and UI components using thread-safe queues.
"""

import queue
import threading
import time
from typing import List, Optional, Callable
from datetime import datetime, timedelta

from models.status_message_model import (
    StatusMessage, ErrorNotification, ProgressUpdate, 
    MessageType, ErrorSeverity
)


class StatusMessageManager:
    """
    Manages status messages and communication between grading threads and UI.
    
    Provides thread-safe message queuing, automatic message cleanup,
    and callback-based UI updates.
    """
    
    def __init__(self):
        """Initialize the status message manager."""
        self.status_queue = queue.Queue()
        self.error_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        
        # Message storage for UI access
        self.active_messages: List[StatusMessage] = []
        self.error_notifications: List[ErrorNotification] = []
        self.current_progress: Optional[ProgressUpdate] = None
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Callbacks for UI updates
        self._status_callbacks: List[Callable] = []
        self._error_callbacks: List[Callable] = []
        self._progress_callbacks: List[Callable] = []
        
        # Auto-cleanup settings
        self.max_messages = 50
        self.max_errors = 20
        self.cleanup_interval = 30  # seconds
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def add_status_callback(self, callback: Callable[[StatusMessage], None]):
        """Add callback for status message updates."""
        self._status_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[ErrorNotification], None]):
        """Add callback for error notification updates."""
        self._error_callbacks.append(callback)
    
    def add_progress_callback(self, callback: Callable[[ProgressUpdate], None]):
        """Add callback for progress updates."""
        self._progress_callbacks.append(callback)
    
    def show_grading_started(self, total_students: int):
        """Show grading started message."""
        message = StatusMessage(
            message_type=MessageType.INFO,
            title="채점 시작",
            content=f"총 {total_students}명의 학생에 대한 채점을 시작합니다.",
            auto_dismiss=False
        )
        self._send_status_message(message)
    
    def show_student_grading_start(self, student_name: str, student_index: int, total_students: int):
        """Show student grading start message."""
        message = StatusMessage(
            message_type=MessageType.INFO,
            title=f"채점 진행 중 ({student_index + 1}/{total_students})",
            content=f"{student_name} 학생을 채점하고 있습니다...",
            student_name=student_name,
            auto_dismiss=True,
            dismiss_after=10
        )
        self._send_status_message(message)
    
    def show_student_grading_complete(self, student_name: str, success: bool, score: Optional[str] = None):
        """Show student grading completion message."""
        if success:
            title = "채점 완료"
            content = f"{student_name} 학생 채점이 완료되었습니다."
            if score:
                content += f" (점수: {score})"
            message_type = MessageType.SUCCESS
        else:
            title = "채점 실패"
            content = f"{student_name} 학생 채점에 실패했습니다."
            message_type = MessageType.ERROR
        
        message = StatusMessage(
            message_type=message_type,
            title=title,
            content=content,
            student_name=student_name,
            auto_dismiss=True,
            dismiss_after=5
        )
        self._send_status_message(message)
    
    def show_grading_completed(self, total_completed: int, total_failed: int):
        """Show grading completion summary."""
        total_students = total_completed + total_failed
        
        if total_failed == 0:
            message_type = MessageType.SUCCESS
            title = "채점 완료"
            content = f"모든 학생({total_students}명)의 채점이 성공적으로 완료되었습니다."
        else:
            message_type = MessageType.WARNING
            title = "채점 완료 (일부 실패)"
            content = f"채점이 완료되었습니다. 성공: {total_completed}명, 실패: {total_failed}명"
        
        message = StatusMessage(
            message_type=message_type,
            title=title,
            content=content,
            auto_dismiss=False
        )
        self._send_status_message(message)
    
    def show_rag_warning(self, student_name: str, error_message: str):
        """Show RAG processing failure warning."""
        message = StatusMessage(
            message_type=MessageType.WARNING,
            title=f"RAG 처리 실패: {student_name}",
            content=f"참고 자료 처리에 실패했습니다. RAG 없이 채점을 계속 진행합니다.",
            student_name=student_name,
            auto_dismiss=False
        )
        self._send_status_message(message)
        
        # Also create error notification
        error = ErrorNotification(
            error_type="rag_failure",
            student_name=student_name,
            error_message="RAG 처리 실패",
            error_details=error_message,
            severity=ErrorSeverity.WARNING,
            suggested_actions=[
                "채점은 RAG 없이 계속 진행됩니다",
                "참고 자료 파일을 확인해주세요",
                "필요시 해당 학생만 다시 채점할 수 있습니다"
            ]
        )
        self._send_error_notification(error)
    
    def show_grading_error(self, student_name: str, error_message: str, error_details: str):
        """Show grading failure error."""
        message = StatusMessage(
            message_type=MessageType.ERROR,
            title=f"채점 실패: {student_name}",
            content=f"채점 중 오류가 발생했습니다: {error_message}",
            student_name=student_name,
            auto_dismiss=False
        )
        self._send_status_message(message)
        
        # Create error notification with recovery suggestions
        error = ErrorNotification(
            error_type="grading_failure",
            student_name=student_name,
            error_message=error_message,
            error_details=error_details,
            severity=ErrorSeverity.ERROR,
            suggested_actions=[
                "다른 AI 모델로 재시도",
                "해당 학생만 개별 재채점",
                "오류 무시하고 다음 학생 계속 진행"
            ]
        )
        self._send_error_notification(error)
    
    def update_progress(self, progress: ProgressUpdate):
        """Update grading progress."""
        with self._lock:
            self.current_progress = progress
        
        self.progress_queue.put(progress)
        
        # Notify callbacks
        for callback in self._progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                print(f"Progress callback error: {e}")
    
    def _send_status_message(self, message: StatusMessage):
        """Send status message to queue and storage."""
        with self._lock:
            self.active_messages.append(message)
            # Keep only recent messages
            if len(self.active_messages) > self.max_messages:
                self.active_messages = self.active_messages[-self.max_messages:]
        
        self.status_queue.put(message)
        
        # Notify callbacks
        for callback in self._status_callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"Status callback error: {e}")
    
    def _send_error_notification(self, error: ErrorNotification):
        """Send error notification to queue and storage."""
        with self._lock:
            self.error_notifications.append(error)
            # Keep only recent errors
            if len(self.error_notifications) > self.max_errors:
                self.error_notifications = self.error_notifications[-self.max_errors:]
        
        self.error_queue.put(error)
        
        # Notify callbacks
        for callback in self._error_callbacks:
            try:
                callback(error)
            except Exception as e:
                print(f"Error callback error: {e}")
    
    def get_recent_messages(self, count: int = 10) -> List[StatusMessage]:
        """Get recent status messages."""
        with self._lock:
            return self.active_messages[-count:] if self.active_messages else []
    
    def get_recent_errors(self, count: int = 5) -> List[ErrorNotification]:
        """Get recent error notifications."""
        with self._lock:
            return self.error_notifications[-count:] if self.error_notifications else []
    
    def get_current_progress(self) -> Optional[ProgressUpdate]:
        """Get current progress update."""
        with self._lock:
            return self.current_progress
    
    def clear_messages(self):
        """Clear all stored messages."""
        with self._lock:
            self.active_messages.clear()
    
    def clear_errors(self):
        """Clear all stored error notifications."""
        with self._lock:
            self.error_notifications.clear()
    
    def process_queue_updates(self) -> dict:
        """Process all pending queue updates and return them."""
        updates = {
            'status_messages': [],
            'error_notifications': [],
            'progress_updates': []
        }
        
        # Process status messages
        try:
            while True:
                message = self.status_queue.get_nowait()
                updates['status_messages'].append(message)
        except queue.Empty:
            pass
        
        # Process error notifications
        try:
            while True:
                error = self.error_queue.get_nowait()
                updates['error_notifications'].append(error)
        except queue.Empty:
            pass
        
        # Process progress updates
        try:
            while True:
                progress = self.progress_queue.get_nowait()
                updates['progress_updates'].append(progress)
        except queue.Empty:
            pass
        
        return updates
    
    def _cleanup_loop(self):
        """Background cleanup loop for old messages."""
        while True:
            try:
                time.sleep(self.cleanup_interval)
                self._cleanup_old_messages()
            except Exception as e:
                print(f"Cleanup loop error: {e}")
    
    def _cleanup_old_messages(self):
        """Remove old auto-dismiss messages."""
        current_time = datetime.now()
        
        with self._lock:
            # Clean up old status messages
            self.active_messages = [
                msg for msg in self.active_messages
                if not msg.auto_dismiss or 
                (current_time - msg.timestamp).total_seconds() < msg.dismiss_after * 2
            ]
            
            # Clean up old error notifications (keep for longer)
            cutoff_time = current_time - timedelta(hours=1)
            self.error_notifications = [
                error for error in self.error_notifications
                if error.timestamp > cutoff_time
            ]