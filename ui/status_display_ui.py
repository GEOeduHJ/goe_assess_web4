"""
Status Display UI Components for Real-time Feedback

This module provides Streamlit UI components for displaying real-time
status messages, error notifications, and progress updates during grading.
"""

import streamlit as st
from typing import List, Optional
from datetime import datetime, timedelta

from models.status_message_model import (
    StatusMessage, ErrorNotification, ProgressUpdate,
    MessageType, ErrorSeverity
)
from services.status_message_manager import StatusMessageManager


class StatusDisplayUI:
    """
    UI component for displaying real-time status messages and notifications.
    """
    
    def __init__(self, status_manager: StatusMessageManager):
        """Initialize with status message manager."""
        self.status_manager = status_manager
    
    def render_status_messages(self, container=None):
        """Render active status messages."""
        if container is None:
            container = st.container()
        
        messages = self.status_manager.get_recent_messages(count=5)
        
        if not messages:
            return
        
        with container:
            st.markdown("### 📢 상태 메시지")
            
            for message in reversed(messages):  # Show newest first
                self._render_single_message(message)
    
    def _render_single_message(self, message: StatusMessage):
        """Render a single status message."""
        # Choose appropriate Streamlit function based on message type
        if message.message_type == MessageType.SUCCESS:
            st.success(f"**{message.title}** - {message.content}")
        elif message.message_type == MessageType.WARNING:
            st.warning(f"**{message.title}** - {message.content}")
        elif message.message_type == MessageType.ERROR:
            st.error(f"**{message.title}** - {message.content}")
        else:  # INFO
            st.info(f"**{message.title}** - {message.content}")
        
        # Show timestamp for non-auto-dismiss messages
        if not message.auto_dismiss:
            st.caption(f"시간: {message.timestamp.strftime('%H:%M:%S')}")
    
    def render_current_progress(self, container=None):
        """Render current grading progress."""
        if container is None:
            container = st.container()
        
        progress = self.status_manager.get_current_progress()
        
        if not progress:
            return
        
        with container:
            st.markdown("### 📈 진행 상황")
            
            # Progress metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "진행률",
                    f"{progress.completed_count}/{progress.total_count}",
                    delta=f"{progress.progress_percentage:.1f}%"
                )
            
            with col2:
                if progress.failed_count > 0:
                    st.metric("실패", progress.failed_count, delta="오류")
                else:
                    st.metric("실패", progress.failed_count)
            
            with col3:
                if progress.average_time > 0:
                    st.metric("평균 시간", f"{progress.average_time:.1f}초")
                else:
                    st.metric("평균 시간", "계산 중...")
            
            with col4:
                if progress.estimated_completion:
                    remaining_time = progress.estimated_completion - datetime.now().timestamp()
                    if remaining_time > 0:
                        minutes, seconds = divmod(int(remaining_time), 60)
                        st.metric("예상 완료", f"{minutes}분 {seconds}초")
                    else:
                        st.metric("예상 완료", "곧 완료")
                else:
                    st.metric("예상 완료", "계산 중...")
            
            # Current student and operation
            if progress.current_student_name:
                st.markdown(f"**현재 처리 중:** {progress.current_student_name}")
                st.markdown(f"**현재 작업:** {progress.current_operation}")
            
            # Progress bar
            progress_value = progress.progress_percentage / 100
            st.progress(
                progress_value,
                text=f"전체 진행률: {progress.progress_percentage:.1f}% "
                     f"({progress.completed_count + progress.failed_count}/{progress.total_count})"
            )
    
    def render_error_notifications(self, container=None):
        """Render error notifications with recovery options."""
        if container is None:
            container = st.container()
        
        errors = self.status_manager.get_recent_errors(count=3)
        
        if not errors:
            return
        
        with container:
            st.markdown("### ⚠️ 오류 알림")
            
            for error in reversed(errors):  # Show newest first
                self._render_single_error(error)
    
    def _render_single_error(self, error: ErrorNotification):
        """Render a single error notification."""
        # Choose color based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            alert_type = "error"
        elif error.severity == ErrorSeverity.ERROR:
            alert_type = "error"
        else:  # WARNING
            alert_type = "warning"
        
        with st.expander(
            f"🚨 {error.error_message} - {error.student_name}",
            expanded=(error.severity == ErrorSeverity.CRITICAL)
        ):
            st.markdown(f"**학생:** {error.student_name}")
            st.markdown(f"**오류 유형:** {error.error_type}")
            st.markdown(f"**시간:** {error.timestamp.strftime('%H:%M:%S')}")
            st.markdown(f"**심각도:** {error.severity.value}")
            
            if error.error_details:
                st.markdown("**상세 정보:**")
                st.code(error.error_details, language="text")
            
            if error.suggested_actions:
                st.markdown("**권장 조치:**")
                for i, action in enumerate(error.suggested_actions, 1):
                    st.markdown(f"{i}. {action}")
    
    def render_live_status_area(self):
        """Render live status area that updates automatically."""
        # Create containers for different types of updates
        status_container = st.container()
        progress_container = st.container()
        error_container = st.container()
        
        # Process any pending updates
        updates = self.status_manager.process_queue_updates()
        
        # Render components
        self.render_current_progress(progress_container)
        self.render_status_messages(status_container)
        self.render_error_notifications(error_container)
        
        return updates
    
    def render_grading_summary(self, total_students: int, completed: int, failed: int):
        """Render grading completion summary."""
        st.markdown("### 📊 채점 완료 요약")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("총 학생 수", total_students)
        
        with col2:
            success_rate = (completed / total_students * 100) if total_students > 0 else 0
            st.metric("성공", completed, delta=f"{success_rate:.1f}%")
        
        with col3:
            if failed > 0:
                failure_rate = (failed / total_students * 100) if total_students > 0 else 0
                st.metric("실패", failed, delta=f"{failure_rate:.1f}%")
            else:
                st.metric("실패", failed)
        
        with col4:
            if failed == 0:
                st.metric("상태", "완료", delta="성공")
            else:
                st.metric("상태", "부분 완료", delta="주의")
        
        # Success/failure breakdown
        if total_students > 0:
            success_ratio = completed / total_students
            st.progress(success_ratio, text=f"성공률: {success_ratio * 100:.1f}%")
        
        # Show action buttons based on results
        if failed > 0:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 실패한 학생 재시도", type="primary"):
                    return "retry_failed"
            
            with col2:
                if st.button("🤖 다른 모델로 재시도"):
                    return "switch_model"
            
            with col3:
                if st.button("📊 결과 보기"):
                    return "view_results"
        else:
            if st.button("📊 결과 보기", type="primary"):
                return "view_results"
        
        return None


class ProgressIndicator:
    """
    Specialized component for showing detailed progress indicators.
    """
    
    @staticmethod
    def render_student_progress_list(students_status: List[dict]):
        """Render a list showing each student's progress status."""
        st.markdown("#### 👥 학생별 진행 상황")
        
        # Create status summary
        status_counts = {"completed": 0, "failed": 0, "in_progress": 0, "not_started": 0}
        
        for student in students_status:
            status = student.get("status", "not_started")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Show summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("✅ 완료", status_counts["completed"])
        with col2:
            st.metric("❌ 실패", status_counts["failed"])
        with col3:
            st.metric("🔄 진행 중", status_counts["in_progress"])
        with col4:
            st.metric("⏳ 대기 중", status_counts["not_started"])
        
        # Show detailed list
        for student in students_status:
            status = student.get("status", "not_started")
            name = student.get("name", "Unknown")
            
            # Choose emoji and color based on status
            if status == "completed":
                emoji = "✅"
                color = "green"
            elif status == "failed":
                emoji = "❌"
                color = "red"
            elif status == "in_progress":
                emoji = "🔄"
                color = "blue"
            else:
                emoji = "⏳"
                color = "gray"
            
            # Show student status
            col1, col2, col3 = st.columns([1, 3, 2])
            
            with col1:
                st.markdown(f"{emoji}")
            
            with col2:
                st.markdown(f"**{name}**")
            
            with col3:
                processing_time = student.get("processing_time", 0)
                if processing_time > 0:
                    st.caption(f"{processing_time:.1f}초")
                else:
                    st.caption(status)
    
    @staticmethod
    def render_operation_timeline(operations: List[dict]):
        """Render timeline of grading operations."""
        st.markdown("#### ⏰ 작업 타임라인")
        
        for operation in operations[-10:]:  # Show last 10 operations
            timestamp = operation.get("timestamp", datetime.now())
            operation_type = operation.get("type", "unknown")
            student_name = operation.get("student_name", "")
            details = operation.get("details", "")
            
            # Format timestamp
            time_str = timestamp.strftime("%H:%M:%S")
            
            # Choose icon based on operation type
            if operation_type == "start":
                icon = "🚀"
            elif operation_type == "rag_processing":
                icon = "📚"
            elif operation_type == "grading":
                icon = "🤖"
            elif operation_type == "completed":
                icon = "✅"
            elif operation_type == "failed":
                icon = "❌"
            else:
                icon = "ℹ️"
            
            st.markdown(f"{icon} **{time_str}** - {student_name}: {details}")