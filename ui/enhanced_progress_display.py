"""
Enhanced Progress Display UI Components

This module provides advanced UI components for displaying detailed
real-time progress information during grading operations.
"""

import streamlit as st
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from models.enhanced_progress_model import (
    EnhancedGradingProgress, StudentProgressDetail, BatchProgressTracker,
    OperationType
)
from services.grading_engine import GradingStatus


class EnhancedProgressDisplay:
    """
    Enhanced UI component for displaying detailed grading progress.
    """
    
    def __init__(self):
        """Initialize the enhanced progress display."""
        self.last_update_time = datetime.now()
        self.update_interval = 1.0  # seconds
    
    def render_enhanced_progress(self, progress: EnhancedGradingProgress, container=None):
        """Render enhanced progress display with current operation details."""
        if container is None:
            container = st.container()
        
        with container:
            # Main progress header
            st.markdown("### 📈 실시간 채점 진행 상황")
            
            # Current operation status
            self._render_current_operation(progress)
            
            # Progress metrics grid
            self._render_progress_metrics(progress)
            
            # Progress bar with detailed info
            self._render_detailed_progress_bar(progress)
            
            # Warnings and errors summary
            if progress.has_warnings or progress.has_errors:
                self._render_alerts_summary(progress)
    
    def _render_current_operation(self, progress: EnhancedGradingProgress):
        """Render current operation information."""
        if not progress.current_student_name:
            return
        
        # Operation status card
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Current student and operation
                operation_text = self._get_operation_text(progress.current_operation)
                st.markdown(f"**현재 처리 중:** {progress.current_student_name} ({progress.current_student_class})")
                st.markdown(f"**현재 작업:** {operation_text}")
                
                # Operation duration
                if progress.current_operation_duration > 0:
                    duration_text = f"{progress.current_operation_duration:.1f}초 경과"
                    st.caption(f"⏱️ {duration_text}")
            
            with col2:
                # Operation icon and status
                operation_icon = self._get_operation_icon(progress.current_operation)
                st.markdown(f"<div style='text-align: center; font-size: 3em;'>{operation_icon}</div>", 
                           unsafe_allow_html=True)
    
    def _render_progress_metrics(self, progress: EnhancedGradingProgress):
        """Render progress metrics in a grid layout."""
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "전체 진행률",
                f"{progress.completed_students + progress.failed_students}/{progress.total_students}",
                delta=f"{progress.progress_percentage:.1f}%"
            )
        
        with col2:
            if progress.failed_students > 0:
                st.metric("실패", progress.failed_students, delta="⚠️")
            else:
                st.metric("실패", progress.failed_students)
        
        with col3:
            if progress.average_processing_time > 0:
                st.metric("평균 시간", f"{progress.average_processing_time:.1f}초")
            else:
                st.metric("평균 시간", "계산 중...")
        
        with col4:
            if progress.average_rag_time > 0:
                st.metric("평균 RAG 시간", f"{progress.average_rag_time:.1f}초")
            else:
                st.metric("평균 RAG 시간", "N/A")
        
        with col5:
            if progress.estimated_completion_time:
                remaining_time = progress.estimated_completion_time - datetime.now().timestamp()
                if remaining_time > 0:
                    minutes, seconds = divmod(int(remaining_time), 60)
                    st.metric("예상 완료", f"{minutes}분 {seconds}초")
                else:
                    st.metric("예상 완료", "곧 완료")
            else:
                st.metric("예상 완료", "계산 중...")
    
    def _render_detailed_progress_bar(self, progress: EnhancedGradingProgress):
        """Render detailed progress bar with segments."""
        # Calculate progress segments
        completed_ratio = progress.completed_students / progress.total_students if progress.total_students > 0 else 0
        failed_ratio = progress.failed_students / progress.total_students if progress.total_students > 0 else 0
        in_progress_ratio = 1 / progress.total_students if progress.total_students > 0 else 0
        
        # Main progress bar
        total_processed = progress.completed_students + progress.failed_students
        overall_progress = total_processed / progress.total_students if progress.total_students > 0 else 0
        
        st.progress(
            overall_progress,
            text=f"전체 진행률: {progress.progress_percentage:.1f}% "
                 f"(완료: {progress.completed_students}, 실패: {progress.failed_students}, "
                 f"남은 학생: {progress.remaining_students})"
        )
        
        # Detailed breakdown
        if progress.total_students > 0:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                success_rate = (progress.completed_students / progress.total_students) * 100
                st.metric("성공률", f"{success_rate:.1f}%", delta="✅")
            
            with col2:
                if progress.failed_students > 0:
                    failure_rate = (progress.failed_students / progress.total_students) * 100
                    st.metric("실패율", f"{failure_rate:.1f}%", delta="❌")
                else:
                    st.metric("실패율", "0%")
            
            with col3:
                remaining_rate = (progress.remaining_students / progress.total_students) * 100
                st.metric("남은 비율", f"{remaining_rate:.1f}%", delta="⏳")
    
    def _render_alerts_summary(self, progress: EnhancedGradingProgress):
        """Render warnings and errors summary."""
        st.markdown("#### ⚠️ 알림 요약")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if progress.has_warnings:
                st.warning(f"⚠️ RAG 처리 경고: {len(progress.rag_warnings)}건")
                with st.expander("경고 상세 보기"):
                    for warning in progress.rag_warnings[-5:]:  # Show last 5
                        st.text(warning)
        
        with col2:
            if progress.has_errors:
                st.error(f"❌ 처리 오류: {len(progress.processing_errors)}건")
                with st.expander("오류 상세 보기"):
                    for error in progress.processing_errors[-5:]:  # Show last 5
                        st.text(error)
    
    def render_student_progress_table(self, student_details: List[StudentProgressDetail], container=None):
        """Render detailed student progress table."""
        if container is None:
            container = st.container()
        
        if not student_details:
            return
        
        with container:
            st.markdown("#### 👥 학생별 상세 진행 상황")
            
            # Prepare table data
            table_data = []
            for detail in student_details:
                status_emoji = self._get_status_emoji(detail.status)
                
                row = {
                    "상태": f"{status_emoji} {detail.status.value}",
                    "학생명": f"{detail.student.name} ({detail.student.class_number})",
                    "총 시간": f"{detail.total_processing_time:.1f}초" if detail.total_processing_time > 0 else "-",
                    "RAG 시간": f"{detail.rag_processing_time:.1f}초" if detail.rag_processing_time > 0 else "-",
                    "채점 시간": f"{detail.grading_processing_time:.1f}초" if detail.grading_processing_time > 0 else "-",
                    "점수": f"{detail.final_score:.1f}/{detail.max_score}" if detail.final_score is not None else "-",
                    "등급": detail.grade_letter or "-"
                }
                
                # Add error information if present
                if detail.rag_error or detail.grading_error:
                    error_msg = detail.rag_error or detail.grading_error
                    row["오류"] = error_msg[:30] + "..." if len(error_msg) > 30 else error_msg
                else:
                    row["오류"] = "-"
                
                table_data.append(row)
            
            # Display table
            st.dataframe(table_data, use_container_width=True)
    
    def render_operation_timeline(self, progress: EnhancedGradingProgress, container=None):
        """Render operation timeline."""
        if container is None:
            container = st.container()
        
        recent_operations = progress.get_recent_operations(count=10)
        
        if not recent_operations:
            return
        
        with container:
            st.markdown("#### ⏰ 최근 작업 타임라인")
            
            for operation in reversed(recent_operations):  # Show newest first
                timestamp = operation.get("timestamp", datetime.now())
                student_name = operation.get("student_name", "")
                op_type = operation.get("operation", "")
                details = operation.get("details", "")
                
                # Format timestamp
                time_str = timestamp.strftime("%H:%M:%S")
                
                # Choose icon and color based on operation type
                if op_type == "rag_processing":
                    icon = "📚"
                    color = "blue"
                elif op_type == "grading":
                    icon = "🤖"
                    color = "green"
                elif op_type == "completed":
                    icon = "✅"
                    color = "green"
                elif op_type == "error":
                    icon = "❌"
                    color = "red"
                elif op_type == "rag_warning":
                    icon = "⚠️"
                    color = "orange"
                else:
                    icon = "ℹ️"
                    color = "gray"
                
                # Display operation
                col1, col2, col3 = st.columns([1, 2, 4])
                
                with col1:
                    st.markdown(f"{icon} {time_str}")
                
                with col2:
                    st.markdown(f"**{student_name}**")
                
                with col3:
                    if details:
                        st.markdown(f"{op_type}: {details}")
                    else:
                        st.markdown(op_type)
    
    def render_performance_metrics(self, progress: EnhancedGradingProgress, container=None):
        """Render performance metrics and statistics."""
        if container is None:
            container = st.container()
        
        with container:
            st.markdown("#### 📊 성능 지표")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**처리 시간 분석**")
                
                if progress.average_processing_time > 0:
                    st.metric("전체 평균 시간", f"{progress.average_processing_time:.1f}초")
                
                if progress.average_rag_time > 0:
                    st.metric("RAG 평균 시간", f"{progress.average_rag_time:.1f}초")
                    rag_percentage = (progress.average_rag_time / progress.average_processing_time * 100) if progress.average_processing_time > 0 else 0
                    st.caption(f"전체 시간의 {rag_percentage:.1f}%")
                
                if progress.average_grading_time > 0:
                    st.metric("채점 평균 시간", f"{progress.average_grading_time:.1f}초")
                    grading_percentage = (progress.average_grading_time / progress.average_processing_time * 100) if progress.average_processing_time > 0 else 0
                    st.caption(f"전체 시간의 {grading_percentage:.1f}%")
            
            with col2:
                st.markdown("**품질 지표**")
                
                if progress.total_students > 0:
                    success_rate = (progress.completed_students / progress.total_students) * 100
                    st.metric("성공률", f"{success_rate:.1f}%")
                    
                    if progress.rag_processing_times:
                        rag_success_rate = ((len(progress.rag_processing_times) - len(progress.rag_warnings)) / len(progress.rag_processing_times)) * 100
                        st.metric("RAG 성공률", f"{rag_success_rate:.1f}%")
                    
                    if progress.has_warnings:
                        st.metric("경고 발생률", f"{len(progress.rag_warnings)} 건")
                    
                    if progress.has_errors:
                        st.metric("오류 발생률", f"{len(progress.processing_errors)} 건")
    
    def _get_operation_text(self, operation: OperationType) -> str:
        """Get human-readable operation text."""
        operation_texts = {
            OperationType.INITIALIZING: "초기화 중",
            OperationType.RAG_PROCESSING: "참고 자료 처리 중",
            OperationType.GRADING: "AI 채점 중",
            OperationType.COMPLETED: "완료",
            OperationType.FAILED: "실패",
            OperationType.PAUSED: "일시정지"
        }
        return operation_texts.get(operation, "알 수 없음")
    
    def _get_operation_icon(self, operation: OperationType) -> str:
        """Get operation icon."""
        operation_icons = {
            OperationType.INITIALIZING: "🔄",
            OperationType.RAG_PROCESSING: "📚",
            OperationType.GRADING: "🤖",
            OperationType.COMPLETED: "✅",
            OperationType.FAILED: "❌",
            OperationType.PAUSED: "⏸️"
        }
        return operation_icons.get(operation, "❓")
    
    def _get_status_emoji(self, status: GradingStatus) -> str:
        """Get status emoji."""
        status_emojis = {
            GradingStatus.NOT_STARTED: "⏳",
            GradingStatus.IN_PROGRESS: "🔄",
            GradingStatus.COMPLETED: "✅",
            GradingStatus.FAILED: "❌",
            GradingStatus.CANCELLED: "⏹️"
        }
        return status_emojis.get(status, "❓")


class ProgressDashboard:
    """
    Comprehensive progress dashboard combining all progress components.
    """
    
    def __init__(self):
        """Initialize the progress dashboard."""
        self.enhanced_display = EnhancedProgressDisplay()
    
    def render_full_dashboard(self, batch_tracker: BatchProgressTracker):
        """Render complete progress dashboard."""
        if not batch_tracker.overall_progress:
            st.warning("진행 상황 정보가 없습니다.")
            return
        
        # Main progress display
        self.enhanced_display.render_enhanced_progress(batch_tracker.overall_progress)
        
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["📊 요약", "👥 학생 상세", "⏰ 타임라인", "📈 성능"])
        
        with tab1:
            # Summary metrics
            self._render_summary_tab(batch_tracker)
        
        with tab2:
            # Student details table
            student_details = list(batch_tracker.student_details.values())
            self.enhanced_display.render_student_progress_table(student_details)
        
        with tab3:
            # Operation timeline
            self.enhanced_display.render_operation_timeline(batch_tracker.overall_progress)
        
        with tab4:
            # Performance metrics
            self.enhanced_display.render_performance_metrics(batch_tracker.overall_progress)
    
    def _render_summary_tab(self, batch_tracker: BatchProgressTracker):
        """Render summary tab content."""
        progress = batch_tracker.overall_progress
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("배치 ID", batch_tracker.batch_id)
        
        with col2:
            st.metric("총 학생 수", len(batch_tracker.students))
        
        with col3:
            if progress.start_time:
                elapsed = (datetime.now() - progress.start_time).total_seconds()
                minutes, seconds = divmod(int(elapsed), 60)
                st.metric("경과 시간", f"{minutes}분 {seconds}초")
        
        with col4:
            completion_rate = (progress.completed_students / progress.total_students * 100) if progress.total_students > 0 else 0
            st.metric("완료율", f"{completion_rate:.1f}%")
        
        # Progress breakdown chart
        if progress.total_students > 0:
            st.markdown("#### 진행 상황 분석")
            
            # Create progress data for visualization
            progress_data = {
                "완료": progress.completed_students,
                "실패": progress.failed_students,
                "남은 학생": progress.remaining_students
            }
            
            # Simple bar chart using Streamlit
            st.bar_chart(progress_data)