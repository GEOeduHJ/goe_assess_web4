"""
Grading execution and progress display UI components.
Handles real-time progress tracking, student result updates, and grading control.
"""

import streamlit as st
import time
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import threading
import queue

from models.student_model import Student
from models.rubric_model import Rubric
from models.result_model import GradingResult
from services.grading_engine import SequentialGradingEngine, GradingProgress, StudentGradingStatus, GradingStatus
from services.llm_service import LLMService
from services.rag_service import RAGService, format_retrieved_content
from utils.error_handler import handle_error, ErrorType, ErrorInfo
from ui.error_display_ui import display_error, display_api_error, display_progress_with_error_handling
# Performance optimization imports removed as part of system monitoring cleanup
from config import config


@dataclass
class GradingSession:
    """Represents an active grading session."""
    students: List[Student]
    rubric: Rubric
    model_type: str
    grading_type: str
    references: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    is_active: bool = False
    is_paused: bool = False
    results: List[GradingResult] = field(default_factory=list)
    # Store uploaded reference files for on-demand processing
    uploaded_files: Optional[List] = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = []


class GradingExecutionUI:
    """UI controller for grading execution and progress display."""
    
    def __init__(self):
        """Initialize the grading execution UI with performance optimization."""
        self.initialize_session_state()
        self.grading_engine = None
        
        # Use session state to maintain queue instances across UI refreshes
        if 'progress_queue' not in st.session_state:
            st.session_state.progress_queue = queue.Queue()
        if 'result_queue' not in st.session_state:
            st.session_state.result_queue = queue.Queue()
            
        self.progress_queue = st.session_state.progress_queue
        self.result_queue = st.session_state.result_queue
        
        # Performance optimization
        self.ui_update_interval = 1.0  # seconds
        self.last_ui_update = 0
        self.batch_size = config.BATCH_PROCESSING_SIZE
    
    def initialize_session_state(self):
        """Initialize Streamlit session state for grading execution."""
        session_vars = {
            'grading_session': None,
            'grading_progress': None,
            'student_results': [],  # Initialize as empty list
            'grading_thread': None,
            'show_detailed_progress': False,
            'grading_errors': [],
            'error_recovery_options': {}
        }
        
        for var_name, default_value in session_vars.items():
            if var_name not in st.session_state:
                st.session_state[var_name] = default_value
    
    def render_grading_execution_page(
        self,
        students: List[Student],
        rubric: Rubric,
        model_type: str,
        grading_type: str,
        references: Optional[List[str]] = None
    ):
        """
        Render the main grading execution page.
        
        Args:
            students: List of students to grade
            rubric: Evaluation rubric
            model_type: Selected LLM model
            grading_type: Type of grading (descriptive/map)
            references: Reference materials from RAG
        """
        st.markdown("## 🚀 채점 실행")
        st.markdown("---")
        
        # Initialize or update grading session
        if not st.session_state.grading_session or not st.session_state.grading_session.students:
            st.session_state.grading_session = GradingSession(
                students=students,
                rubric=rubric,
                model_type=model_type,
                grading_type=grading_type,
                references=references,
                uploaded_files=st.session_state.get('uploaded_reference_files', None)  # Pass uploaded files
            )
            print(f"DEBUG: Created new grading session with {len(students) if students else 0} students")
        else:
            # Update existing session with new data
            st.session_state.grading_session.students = students
            st.session_state.grading_session.rubric = rubric
            st.session_state.grading_session.model_type = model_type
            st.session_state.grading_type = grading_type
            st.session_state.grading_session.references = references
            if st.session_state.get('uploaded_reference_files'):
                st.session_state.grading_session.uploaded_files = st.session_state.uploaded_reference_files
            print(f"DEBUG: Updated grading session with {len(students) if students else 0} students")
        
        # Render grading overview
        self.render_grading_overview()
        
        # Render grading controls
        self.render_grading_controls()
        
        # Render progress display
        if st.session_state.grading_session.is_active or st.session_state.grading_progress:
            self.render_progress_display()
        
        # Check for completion first
        if st.session_state.get('grading_completed', False):
            st.success("✅ 채점이 완료되었습니다!")
            
            # Clean up temporary directories
            self._cleanup_temp_directories()
            
            if st.session_state.student_results:
                self.render_realtime_results()
        # Render real-time results
        elif st.session_state.student_results:
            self.render_realtime_results()
        elif not st.session_state.grading_session.is_active and not st.session_state.student_results:
            st.info("채점을 시작하려면 위의 '채점 시작' 버튼을 클릭하세요.")
        
        # Update progress from background thread
        print(f"DEBUG: Calling update_progress_from_queue")
        self.update_progress_from_queue()
        
        # Auto-refresh only if grading is active and no completion detected
        if (st.session_state.grading_session and 
            st.session_state.grading_session.is_active and 
            not st.session_state.get('grading_completed', False)):
            print(f"DEBUG: Grading active, scheduling auto-refresh")
            import time
            time.sleep(0.5)  # Shorter delay
            st.rerun()
    
    def render_grading_overview(self):
        """Render grading session overview."""
        session = st.session_state.grading_session
        
        st.markdown("### 📊 채점 개요")
        
        # Check if basic setup is complete
        if not session.rubric:
            st.warning("⚠️ 루브릭이 설정되지 않았습니다. 먼저 루브릭을 설정해주세요.")
            if st.button("📋 루브릭 설정하러 가기", type="primary"):
                st.session_state.current_page = "rubric"
                st.rerun()
            return
        
        if not session.students:
            st.warning("⚠️ 학생 데이터가 없습니다. 먼저 학생 답안을 업로드해주세요.")
            if st.button("🏠 메인 페이지로 돌아가기", type="primary"):
                st.session_state.current_page = "main"
                st.rerun()
            st.info("💡 메인 페이지에서 Excel 파일을 업로드하여 학생 답안을 추가할 수 있습니다.")
            return
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("총 학생 수", len(session.students))
        
        with col2:
            grading_type_name = "서술형" if session.grading_type == "descriptive" else "백지도형"
            st.metric("채점 유형", grading_type_name)
        
        with col3:
            model_name = "Gemini 2.5 Flash" if session.model_type == "gemini" else "Groq Qwen3"
            st.metric("AI 모델", model_name)
        
        with col4:
            rubric_elements_count = len(session.rubric.elements) if session.rubric else 0
            st.metric("평가 요소", rubric_elements_count)
        
        # Show detailed information in expander
        with st.expander("📋 상세 정보"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**학생 목록 (처음 10명):**")
                for i, student in enumerate(session.students[:10]):
                    st.write(f"{i+1}. {student.name} ({student.class_number})")
                
                if len(session.students) > 10:
                    st.write(f"... 외 {len(session.students) - 10}명")
            
            with col2:
                st.markdown("**평가 루브릭:**")
                if session.rubric:
                    st.write(f"**루브릭명:** {session.rubric.name}")
                    st.write(f"**총 만점:** {session.rubric.total_max_score}점")
                    
                    for element in session.rubric.elements:
                        st.write(f"- {element.name}: {element.max_score}점")
                else:
                    st.write("⚠️ 루브릭이 설정되지 않았습니다.")
                
                if session.references:
                    st.markdown("**참고 자료:**")
                    st.write(f"✅ {len(session.references)}개 문서 활용")
                elif session.uploaded_files:
                    st.markdown("**참고 자료:**")
                    st.write(f"✅ {len(session.uploaded_files)}개 문서 업로드됨 (채점 시 처리)")
    
    def render_grading_controls(self):
        """Render grading control buttons."""
        session = st.session_state.grading_session
        
        st.markdown("### 🎮 채점 제어")
        
        # Check for completion - multiple detection methods
        grading_completed = False
        
        # Method 1: Direct completion flag from queue processing
        if st.session_state.get('grading_completed', False):
            grading_completed = True
            print("DEBUG: Grading completed detected via completion flag")
        
        # Method 2: Progress-based completion detection
        elif (session and not session.is_active and 
              st.session_state.grading_progress and
              st.session_state.grading_progress.total_students > 0 and
              (st.session_state.grading_progress.completed_students + 
               st.session_state.grading_progress.failed_students) >= 
               st.session_state.grading_progress.total_students):
            grading_completed = True
            print("DEBUG: Grading completed detected via progress metrics")
        
        # Method 3: Results-based completion detection
        elif (session and not session.is_active and 
              st.session_state.student_results and 
              len(st.session_state.student_results) >= len(session.students)):
            grading_completed = True
            print("DEBUG: Grading completed detected via result count")
        
        # Debug current state
        print(f"DEBUG: Session active: {session.is_active if session else 'No session'}")
        print(f"DEBUG: Grading completed flag: {st.session_state.get('grading_completed', False)}")
        print(f"DEBUG: Student results count: {len(st.session_state.get('student_results', []))}")
        print(f"DEBUG: Total students: {len(session.students) if session else 0}")
        
        if grading_completed:
            print("DEBUG: Showing completion UI")
            st.success("✅ 채점이 완료되었습니다!")
            
            # Clean up temporary directories
            self._cleanup_temp_directories()
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📊 결과 보기", type="primary", use_container_width=True, key="view_results_btn"):
                    st.session_state.current_page = "results"
                    st.rerun()
            with col2:
                if st.button("🔄 새 채점 시작", use_container_width=True, key="new_grading_btn"):
                    # Reset completion flags for new grading
                    st.session_state.grading_completed = False
                    st.session_state.student_results = []
                    st.session_state.grading_progress = None
                    st.rerun()
            return
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Start grading button
            session_active = session and session.is_active
            if not session_active:
                if st.button(
                    "🚀 채점 시작",
                    key="start_grading",
                    type="primary",
                    use_container_width=True,
                    help="모든 학생에 대한 순차 채점을 시작합니다"
                ):
                    # Immediately mark as active to prevent double-click
                    if session:
                        session.is_active = True
                    self.start_grading()
            else:
                st.button(
                    "⏳ 채점 진행 중...",
                    key="grading_in_progress",
                    disabled=True,
                    use_container_width=True
                )
        
        with col2:
            # Pause/Resume button
            if session and session.is_active:
                if not session.is_paused:
                    if st.button(
                        "⏸️ 일시정지",
                        key="pause_grading",
                        use_container_width=True,
                        help="현재 학생 채점 완료 후 일시정지합니다"
                    ):
                        self.pause_grading()
                else:
                    if st.button(
                        "▶️ 재시작",
                        key="resume_grading",
                        use_container_width=True,
                        help="일시정지된 채점을 재시작합니다"
                    ):
                        self.resume_grading()
        
        with col3:
            # Stop grading button
            if session and session.is_active:
                if st.button(
                    "⏹️ 채점 중단",
                    key="stop_grading",
                    use_container_width=True,
                    help="채점을 완전히 중단합니다"
                ):
                    self.stop_grading()
        
        with col4:
            # Retry failed button (only show if there are failed students)
            if (session and not session.is_active and 
                st.session_state.grading_progress and 
                st.session_state.grading_progress.failed_students > 0):
                if st.button(
                    "🔄 실패 재시도",
                    key="retry_failed",
                    use_container_width=True,
                    help="실패한 학생들만 다시 채점합니다"
                ):
                    self.retry_failed_students()
        
        # Show current status (only if not completed)
        if session and session.is_active:
            if session.is_paused:
                st.warning("⏸️ 채점이 일시정지되었습니다. 재시작 버튼을 눌러 계속 진행하세요.")
            else:
                st.info("🔄 채점이 진행 중입니다. 실시간으로 결과가 업데이트됩니다.")
    
    def render_progress_display(self):
        """Render real-time progress display with error handling."""
        progress = st.session_state.grading_progress
        session = st.session_state.grading_session
        
        if not progress:
            return
        
        # Don't show duplicate completion message - it's handled in render_grading_controls
        
        st.markdown("### 📈 진행 상황")
        
        # Progress metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "완료된 학생",
                f"{progress.completed_students}/{progress.total_students}",
                delta=f"{progress.progress_percentage:.1f}%"
            )
        
        with col2:
            if progress.failed_students > 0:
                st.metric("실패한 학생", progress.failed_students, delta="오류")
            else:
                st.metric("실패한 학생", progress.failed_students)
        
        with col3:
            if progress.average_processing_time > 0:
                st.metric(
                    "평균 소요시간",
                    f"{progress.average_processing_time:.1f}초"
                )
            else:
                st.metric("평균 소요시간", "계산 중...")
        
        with col4:
            if progress.estimated_completion_time:
                remaining_time = progress.estimated_completion_time - time.time()
                if remaining_time > 0:
                    minutes, seconds = divmod(int(remaining_time), 60)
                    st.metric("예상 완료시간", f"{minutes}분 {seconds}초")
                else:
                    st.metric("예상 완료시간", "곧 완료")
            else:
                st.metric("예상 완료시간", "계산 중...")
        
        # Enhanced progress display with error handling
        current_student_name = ""
        # Use current_student_name from progress if available
        if hasattr(progress, 'current_student_name') and progress.current_student_name:
            current_student_name = progress.current_student_name
            if hasattr(progress, 'current_student_class') and progress.current_student_class:
                current_student_name = f"{progress.current_student_name} ({progress.current_student_class})"
            print(f"DEBUG: Displaying current student: {current_student_name}")
        elif (session and session.students and 
              hasattr(progress, 'current_student_index') and
              0 <= progress.current_student_index < len(session.students)):
            # Fallback to session student list
            current_student = session.students[progress.current_student_index]
            current_student_name = f"{current_student.name} ({current_student.class_number})"
            print(f"DEBUG: Fallback current student: {current_student_name}")
        else:
            print(f"DEBUG: No current student info available. Progress attributes: {[attr for attr in dir(progress) if not attr.startswith('_')]}")
        
        # Use error-aware progress display
        display_progress_with_error_handling(
            current=progress.completed_students,
            total=progress.total_students,
            current_item=current_student_name,
            recent_errors=st.session_state.grading_errors[-5:]  # Show last 5 errors
        )
        
        # Show error recovery options if there are errors
        if st.session_state.grading_errors:
            self.render_error_recovery_section()
        
        # Detailed progress toggle
        if st.checkbox("상세 진행 상황 보기", key="show_detailed_progress"):
            self.render_detailed_progress()
    
    def render_error_recovery_section(self):
        """Render error recovery options for failed operations."""
        st.markdown("#### 🔧 오류 복구 옵션")
        
        recent_errors = st.session_state.grading_errors[-3:]  # Show last 3 errors
        
        if not recent_errors:
            return
        
        # Show error summary
        error_types = {}
        for error in st.session_state.grading_errors:
            error_type = error.error_type.value
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button(
                "🔄 실패한 학생만 재시도",
                key="retry_failed_students",
                help="오류가 발생한 학생들만 다시 채점합니다"
            ):
                self.retry_failed_students()
        
        with col2:
            if st.button(
                "🤖 다른 AI 모델로 재시도",
                key="switch_model_retry",
                help="다른 AI 모델을 사용하여 실패한 학생들을 재시도합니다"
            ):
                self.switch_model_and_retry()
        
        with col3:
            if st.button(
                "⏹️ 오류 무시하고 계속",
                key="ignore_errors_continue",
                help="현재 오류를 무시하고 다음 학생부터 계속 진행합니다"
            ):
                self.ignore_errors_and_continue()
        
        # Show recent error details
        with st.expander(f"최근 오류 상세 정보 ({len(recent_errors)}개)"):
            for i, error in enumerate(recent_errors, 1):
                st.markdown(f"**오류 {i}:**")
                display_error(error, show_details=True)
                st.markdown("---")
    
    def switch_model_and_retry(self):
        """Switch to alternative AI model and retry failed students."""
        session = st.session_state.grading_session
        
        # Switch model
        if session.model_type == "gemini":
            new_model = "groq"
            st.info("🔄 Groq 모델로 전환하여 재시도합니다...")
        else:
            new_model = "gemini"
            st.info("🔄 Gemini 모델로 전환하여 재시도합니다...")
        
        # Update session model
        session.model_type = new_model
        
        # If switching to Groq, set default Groq model if not already set
        if new_model == "groq" and not hasattr(st.session_state, 'selected_groq_model'):
            st.session_state.selected_groq_model = "qwen/qwen3-32b"
        
        # Retry failed students
        self.retry_failed_students()
    
    def ignore_errors_and_continue(self):
        """Ignore current errors and continue with next students."""
        # Clear current errors
        st.session_state.grading_errors = []
        
        # Resume grading if paused
        session = st.session_state.grading_session
        if session.is_paused:
            self.resume_grading()
        
        st.info("⏭️ 오류를 무시하고 다음 학생부터 계속 진행합니다.")
    
    def render_detailed_progress(self):
        """Render detailed progress information."""
        if not self.grading_engine:
            return
        
        try:
            summary = self.grading_engine.get_grading_summary()
            
            st.markdown("#### 📊 상세 진행 상황")
            
            # Summary statistics
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**전체 통계:**")
                st.write(f"- 배치 ID: {summary.get('batch_id', 'N/A')}")
                st.write(f"- 성공률: {summary.get('success_rate', 0):.1f}%")
                st.write(f"- 총 처리시간: {summary.get('total_processing_time', 0):.1f}초")
            
            with col2:
                st.markdown("**시간 정보:**")
                start_time = None
                if summary.get('start_time'):
                    start_time = datetime.fromisoformat(summary['start_time'])
                    st.write(f"- 시작시간: {start_time.strftime('%H:%M:%S')}")
                
                elapsed_time = time.time() - start_time.timestamp() if start_time else 0
                minutes, seconds = divmod(int(elapsed_time), 60)
                st.write(f"- 경과시간: {minutes}분 {seconds}초")
            
            # Student details table
            if summary.get('student_details'):
                st.markdown("**학생별 상세 정보:**")
                
                # Create a more readable table
                student_data = []
                for detail in summary['student_details']:
                    status_emoji = {
                        'completed': '✅',
                        'failed': '❌',
                        'in_progress': '🔄',
                        'not_started': '⏳',
                        'cancelled': '⏹️'
                    }.get(detail['status'], '❓')
                    
                    student_data.append({
                        '상태': f"{status_emoji} {detail['status']}",
                        '학생명': detail['student_name'],
                        '시도횟수': detail['attempt_count'],
                        '소요시간': f"{detail['processing_time']:.1f}초" if detail['processing_time'] > 0 else '-',
                        '점수': f"{detail.get('total_score', 0)}/{detail.get('total_max_score', 0)}" if detail.get('total_score') is not None else '-',
                        '오류': detail.get('error_message', '')[:50] + '...' if detail.get('error_message') and len(detail.get('error_message', '')) > 50 else detail.get('error_message', '')
                    })
                
                st.dataframe(student_data, use_container_width=True)
        
        except Exception as e:
            st.error(f"상세 정보를 불러오는 중 오류가 발생했습니다: {e}")
    
    def render_realtime_results(self):
        """Render real-time grading results with option to view detailed results."""
        st.markdown("### 📋 실시간 채점 결과")
        
        results = st.session_state.student_results
        print(f"DEBUG: Rendering results, count: {len(results) if results else 0}")
        
        if not results:
            st.info("아직 완료된 채점 결과가 없습니다.")
            return
        
        # Results summary
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_score = sum(r.percentage for r in results) / len(results)
            st.metric("평균 점수", f"{avg_score:.1f}%")
        
        with col2:
            avg_time = sum(r.grading_time_seconds for r in results) / len(results)
            st.metric("평균 채점시간", f"{avg_time:.1f}초")
        
        with col3:
            st.metric("완료된 학생", len(results))
        
        with col4:
            # Button to view detailed results
            if st.button(
                "📊 상세 결과 보기",
                key="view_detailed_results",
                type="primary",
                use_container_width=True,
                help="완성된 결과를 상세하게 분석하고 시각화합니다"
            ):
                st.session_state.current_page = "results"
                st.rerun()
        
        # Show recent results preview (last 5)
        st.markdown("#### 최근 채점 결과 (미리보기)")
        
        recent_results = list(reversed(results[-5:]))  # Show last 5 results
        
        for i, result in enumerate(recent_results):
            with st.expander(
                f"🎓 {result.student_name} ({result.student_class_number}) - "
                f"{result.total_score}/{result.total_max_score}점 ({result.percentage:.1f}%) "
                f"[{result.grade_letter}등급]",
                expanded=(i == 0)  # Expand the most recent result
            ):
                self.render_individual_result_preview(result)
    
    def render_individual_result_preview(self, result: GradingResult):
        """Render individual student result preview (simplified version)."""
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("**평가 요소별 점수:**")
            for element_score in result.element_scores:
                percentage = (element_score.score / element_score.max_score * 100) if element_score.max_score > 0 else 0
                st.progress(
                    percentage / 100,
                    text=f"{element_score.element_name}: {element_score.score}/{element_score.max_score}점 ({percentage:.1f}%)"
                )
        
        with col2:
            st.markdown("**채점 정보:**")
            st.write(f"⏱️ 소요시간: {result.grading_time_seconds:.1f}초")
            if result.graded_at:
                st.write(f"📅 채점시각: {result.graded_at.strftime('%H:%M:%S')}")
            else:
                st.write("📅 채점시각: N/A")
            st.write(f"🏆 등급: {result.grade_letter}")
        
        if result.overall_feedback:
            feedback_preview = result.overall_feedback[:150] + "..." if len(result.overall_feedback) > 150 else result.overall_feedback
            st.markdown("**피드백 미리보기:**")
            st.info(feedback_preview)
    
    def start_grading(self):
        """Start the grading process with comprehensive error handling."""
        session = st.session_state.grading_session
        
        try:
            # Initialize grading engine
            self.grading_engine = SequentialGradingEngine()
            
            # Set up callbacks
            self.grading_engine.set_progress_callback(self.on_progress_update)
            self.grading_engine.set_student_completed_callback(self.on_student_completed)
            self.grading_engine.set_grading_completed_callback(self.on_grading_completed)
            self.grading_engine.set_error_callback(self.on_error)
            
            # Validate setup
            validation = self.grading_engine.validate_grading_setup(
                students=session.students,
                rubric=session.rubric,
                model_type=session.model_type,
                grading_type=session.grading_type
            )
            
            if not validation['valid']:
                error_info = handle_error(
                    ValueError(f"채점 설정 검증 실패: {validation['errors']}"),
                    ErrorType.VALIDATION,
                    context="start_grading: validation failed",
                    user_context="채점 설정 검증"
                )
                display_error(error_info)
                return
            
            if validation['warnings']:
                st.warning("⚠️ 주의사항:")
                for warning in validation['warnings']:
                    st.warning(f"- {warning}")
            
            # Clear previous errors but preserve results if this is a retry
            st.session_state.grading_errors = []
            # Only clear results if starting fresh (not retrying)
            if not st.session_state.get('student_results'):
                st.session_state.student_results = []
            # Reset progress for new grading session
            st.session_state.grading_progress = None
            
            # Start grading in background thread
            session.is_active = True
            session.is_paused = False
            session.start_time = datetime.now()
            
            # Start grading thread
            grading_thread = threading.Thread(
                target=self.run_grading_thread,
                args=(session,),
                daemon=True
            )
            grading_thread.start()
            st.session_state.grading_thread = grading_thread
            
            st.success("🚀 채점이 시작되었습니다!")
            st.rerun()
            
        except Exception as e:
            error_info = handle_error(
                e,
                ErrorType.SYSTEM,
                context="start_grading: unexpected error",
                user_context="채점 시작"
            )
            display_error(error_info)
    
    def run_grading_thread(self, session: GradingSession):
        """Run grading in background thread with comprehensive error handling."""
        try:
            # Get the selected Groq model from session state
            groq_model_name = getattr(st.session_state, 'selected_groq_model', 'qwen/qwen3-32b')
            
            if self.grading_engine:
                results = self.grading_engine.grade_students_sequential(
                    students=session.students,
                    rubric=session.rubric,
                    model_type=session.model_type,
                    grading_type=session.grading_type,
                    references=session.references,
                    groq_model_name=groq_model_name,
                    uploaded_files=session.uploaded_files  # Pass uploaded files for on-demand RAG processing
                )
                
                # Mark session as completed - completion callback will handle UI updates
                session.is_active = False
                session.is_paused = False
                
                # Note: Completion notification is now handled by grading_completed_callback
                # instead of manually sending to progress_queue here
            else:
                st.error("채점 엔진이 초기화되지 않았습니다.")
                
        except Exception as e:
            # Handle thread errors with proper error categorization
            error_info = handle_error(
                e,
                ErrorType.SYSTEM,
                context="run_grading_thread: grading execution failed",
                user_context="채점 실행"
            )
            
            # Mark session as failed
            session.is_active = False
            session.is_paused = False
            
            # Send error to UI thread
            self.progress_queue.put(('thread_error', error_info))
    
    def pause_grading(self):
        """Pause the grading process."""
        session = st.session_state.grading_session
        session.is_paused = True
        
        if self.grading_engine:
            self.grading_engine.cancel_grading()
        
        st.warning("⏸️ 채점 일시정지가 요청되었습니다. 현재 학생 채점 완료 후 정지됩니다.")
    
    def resume_grading(self):
        """Resume the grading process."""
        session = st.session_state.grading_session
        session.is_paused = False
        
        # Restart grading from where it left off
        # This would require more complex state management
        st.info("▶️ 채점이 재시작되었습니다.")
    
    def stop_grading(self):
        """Stop the grading process completely."""
        session = st.session_state.grading_session
        session.is_active = False
        session.is_paused = False
        
        if self.grading_engine:
            self.grading_engine.cancel_grading()
        
        st.error("⏹️ 채점이 중단되었습니다.")
        st.rerun()
    
    def retry_failed_students(self):
        """Retry grading for failed students."""
        if not self.grading_engine:
            st.error("채점 엔진이 초기화되지 않았습니다.")
            return
        
        session = st.session_state.grading_session
        
        try:
            # Get the selected Groq model from session state
            groq_model_name = getattr(st.session_state, 'selected_groq_model', 'qwen/qwen3-32b')
            
            new_results = self.grading_engine.retry_failed_students(
                rubric=session.rubric,
                model_type=session.model_type,
                grading_type=session.grading_type,
                references=session.references,
                groq_model_name=groq_model_name,
                uploaded_files=session.uploaded_files  # Pass uploaded files for on-demand RAG processing
            )
            
            # Add new results to session
            st.session_state.student_results.extend(new_results)
            
            st.success(f"🔄 {len(new_results)}명의 학생이 추가로 채점되었습니다.")
            st.rerun()
            
        except Exception as e:
            st.error(f"재시도 중 오류가 발생했습니다: {e}")
    
    def on_progress_update(self, progress: GradingProgress):
        """Callback for progress updates."""
        try:
            # Use queue to safely communicate between threads
            self.progress_queue.put(('progress', progress))
        except Exception as e:
            print(f"Error in progress update: {e}")
    
    def on_student_completed(self, student_status: StudentGradingStatus):
        """Callback for individual student completion."""
        try:
            if student_status.result:
                # Use queue to safely pass results between threads
                self.result_queue.put(('result', student_status.result))
                print(f"DEBUG: Queued result for {student_status.result.student_name}")
            else:
                print(f"DEBUG: No result for student {student_status.student.name}")
        except Exception as e:
            error_msg = f"Error updating student results: {str(e)}"
            print(error_msg)  # Fallback logging
    
    def on_grading_completed(self, completed_count: int):
        """Callback for overall grading completion."""
        try:
            print(f"DEBUG: on_grading_completed called with {completed_count} students")
            # Send completion signal to progress queue
            self.progress_queue.put(('completed', completed_count))
            print(f"DEBUG: Completion signal put in queue")
            
            # Note: Do NOT set session state from background thread
            # It will be handled in the main thread via queue processing
                
        except Exception as e:
            error_msg = f"Error handling grading completion: {str(e)}"
            print(error_msg)  # Fallback logging
    
    def on_error(self, message: str, exception: Exception):
        """Callback for error handling with proper error categorization."""
        try:
            # Determine error type based on exception
            error_type = ErrorType.SYSTEM
            if "api" in message.lower() or "network" in str(exception).lower():
                error_type = ErrorType.API_COMMUNICATION
            elif "file" in message.lower() or "upload" in message.lower():
                error_type = ErrorType.FILE_PROCESSING
            elif "parse" in message.lower() or "json" in str(exception).lower():
                error_type = ErrorType.PARSING
            
            error_info = handle_error(
                exception,
                error_type,
                context=f"on_error: {message}",
                user_context="채점 진행 중"
            )
            
            # Add to error list
            st.session_state.grading_errors.append(error_info)
            
            # Send to UI thread
            self.progress_queue.put(('error', error_info))
            
        except Exception as e:
            # Fallback error handling
            self.progress_queue.put(('error', f"Error handler failed: {e}"))
    
    def update_progress_from_queue(self):
        """Update UI from background thread queues with error handling."""
        print(f"DEBUG: update_progress_from_queue called")
        # Process progress updates
        should_rerun = False
        queue_processed = False
        processed_items = 0
        try:
            while True:
                update_type, data = self.progress_queue.get_nowait()
                queue_processed = True
                processed_items += 1
                print(f"DEBUG: Processing queue item #{processed_items}: {update_type}")
                
                if update_type == 'progress':
                    # Safely update session state in main thread
                    st.session_state.grading_progress = data
                    should_rerun = True
                
                elif update_type == 'error':
                    if isinstance(data, ErrorInfo):
                        display_error(data)
                    else:
                        st.error(f"채점 오류: {data}")
                    should_rerun = True
                
                elif update_type == 'completed':
                    # Handle grading completion - show results immediately
                    print(f"DEBUG: Processing completed signal with {data} students")
                    if hasattr(st.session_state, 'grading_session') and st.session_state.grading_session:
                        st.session_state.grading_session.is_active = False
                        st.session_state.grading_session.is_paused = False
                    
                    # Set completion flag for UI to detect
                    st.session_state.grading_completed = True
                    st.session_state.completed_count = data
                    print(f"DEBUG: Set grading_completed flag to True in main thread")
                    
                    st.success(f"🎉 채점이 완료되었습니다! 총 {data}명의 학생이 채점되었습니다.")
                    st.info("📊 아래에서 실시간 채점 결과를 확인하거나, 상단 탭에서 '결과 보기'를 클릭하세요.")
                    should_rerun = True
                
                elif update_type == 'thread_error':
                    display_error(data)
                    should_rerun = True
                    if hasattr(st.session_state, 'grading_session') and st.session_state.grading_session:
                        st.session_state.grading_session.is_active = False
                    
        except queue.Empty:
            if queue_processed:
                print(f"DEBUG: Queue processed {processed_items} items, now empty")
            else:
                print(f"DEBUG: Queue was empty")
            pass
        
        # Process result updates first
        try:
            while True:
                update_type, data = self.result_queue.get_nowait()
                if update_type == 'result':
                    # Safely update session state in main thread
                    if 'student_results' not in st.session_state:
                        st.session_state.student_results = []
                    st.session_state.student_results.append(data)
                    print(f"DEBUG: Added result for {data.student_name}, total results: {len(st.session_state.student_results)}")
                    should_rerun = True
        except queue.Empty:
            pass
        
        # Check if all results are collected (completion detection via results)
        session = st.session_state.grading_session
        if (session and not session.is_active and 
            st.session_state.student_results and 
            len(st.session_state.student_results) >= len(session.students)):
            if not st.session_state.get('grading_completed', False):
                print(f"DEBUG: Auto-detected completion via result count")
                st.session_state.grading_completed = True
                st.session_state.completed_count = len(st.session_state.student_results)
                should_rerun = True
        
        # Only rerun once if any updates occurred
        if should_rerun:
            st.rerun()

    def _cleanup_temp_directories(self):
        """Clean up temporary directories after grading completion."""
        if 'temp_directories' in st.session_state:
            import shutil
            import os
            for temp_dir in st.session_state.temp_directories:
                if os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                        print(f"DEBUG: Cleaned up temp directory: {temp_dir}")
                    except Exception as e:
                        print(f"DEBUG: Failed to clean up temp directory {temp_dir}: {e}")
            st.session_state.temp_directories = []


def create_grading_execution_ui() -> GradingExecutionUI:
    """
    Factory function to create GradingExecutionUI instance.
    
    Returns:
        GradingExecutionUI: Configured GradingExecutionUI instance
    """
    return GradingExecutionUI()