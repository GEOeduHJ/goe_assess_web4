"""
Error Display UI Components for Geography Auto-Grading Platform

This module provides user-friendly error display components for Streamlit UI,
including error messages, suggestions, and recovery options.
"""

import streamlit as st
from typing import Optional, List, Dict, Any
from utils.error_handler import ErrorInfo, ErrorType, ErrorSeverity
import time


class ErrorDisplayUI:
    """
    UI components for displaying errors in a user-friendly manner.
    
    Provides various error display formats including alerts, modals,
    and inline messages with appropriate styling and actions.
    """
    
    def __init__(self):
        """Initialize error display UI."""
        self.error_icons = {
            ErrorSeverity.LOW: "ℹ️",
            ErrorSeverity.MEDIUM: "⚠️", 
            ErrorSeverity.HIGH: "❌",
            ErrorSeverity.CRITICAL: "🚨"
        }
        
        self.error_colors = {
            ErrorSeverity.LOW: "info",
            ErrorSeverity.MEDIUM: "warning",
            ErrorSeverity.HIGH: "error", 
            ErrorSeverity.CRITICAL: "error"
        }
    
    def display_error(self, error_info: ErrorInfo, show_details: bool = False) -> None:
        """
        Display error information with appropriate styling and actions.
        
        Args:
            error_info: Structured error information
            show_details: Whether to show technical details
        """
        icon = self.error_icons.get(error_info.severity, "❌")
        
        # Choose appropriate Streamlit component based on severity
        if error_info.severity == ErrorSeverity.CRITICAL:
            st.error(f"{icon} **{error_info.user_message}**")
        elif error_info.severity == ErrorSeverity.HIGH:
            st.error(f"{icon} **{error_info.user_message}**")
        elif error_info.severity == ErrorSeverity.MEDIUM:
            st.warning(f"{icon} **{error_info.user_message}**")
        else:
            st.info(f"{icon} **{error_info.user_message}**")
        
        # Show suggestion if available
        if error_info.suggestion:
            st.markdown(f"**💡 해결 방법:** {error_info.suggestion}")
        
        # Show retry option if applicable
        if error_info.retry_possible:
            self._display_retry_option(error_info)
        
        # Show technical details if requested
        if show_details and error_info.technical_details:
            with st.expander("🔧 기술적 세부사항"):
                st.code(error_info.technical_details)
                if error_info.error_code:
                    st.text(f"오류 코드: {error_info.error_code}")
    
    def _display_retry_option(self, error_info: ErrorInfo) -> None:
        """Display retry option for retryable errors."""
        if error_info.current_retry < error_info.max_retries:
            remaining_retries = error_info.max_retries - error_info.current_retry
            st.info(f"🔄 자동으로 다시 시도합니다... (남은 시도: {remaining_retries}회)")
        else:
            st.error("🔄 최대 재시도 횟수에 도달했습니다.")
    
    def display_file_upload_error(self, error_info: ErrorInfo, file_name: str = "") -> None:
        """
        Display file upload specific error with helpful guidance.
        
        Args:
            error_info: Error information
            file_name: Name of the problematic file
        """
        st.error(f"📁 **파일 업로드 오류**")
        
        if file_name:
            st.markdown(f"**파일:** `{file_name}`")
        
        st.markdown(f"**문제:** {error_info.user_message}")
        st.markdown(f"**해결방법:** {error_info.suggestion}")
        
        # Show file format requirements based on error type
        if "형식" in error_info.message or "format" in error_info.message:
            self._show_file_format_help()
        
        # Show file size guidance if size-related error
        if "크기" in error_info.message or "size" in error_info.message:
            self._show_file_size_help()
    
    def _show_file_format_help(self) -> None:
        """Show file format requirements."""
        with st.expander("📋 지원하는 파일 형식"):
            st.markdown("""
            **Excel 파일:**
            - `.xlsx` (권장)
            - `.xls`
            
            **문서 파일:**
            - `.pdf`
            - `.docx`
            
            **이미지 파일:**
            - `.jpg`, `.jpeg` (권장)
            - `.png`
            - `.bmp`
            """)
    
    def _show_file_size_help(self) -> None:
        """Show file size limitations."""
        with st.expander("📏 파일 크기 제한"):
            st.markdown("""
            **최대 파일 크기:**
            - 이미지 파일: 50MB
            - 문서 파일: 100MB
            - Excel 파일: 10MB
            
            **파일 크기 줄이는 방법:**
            - 이미지: 해상도 낮추기, 압축하기
            - 문서: 불필요한 이미지 제거
            - Excel: 불필요한 시트 삭제
            """)
    
    def display_api_error(self, error_info: ErrorInfo, api_name: str = "") -> None:
        """
        Display API-related error with service-specific guidance.
        
        Args:
            error_info: Error information
            api_name: Name of the API service
        """
        st.error(f"🤖 **AI 서비스 오류**")
        
        if api_name:
            st.markdown(f"**서비스:** {api_name}")
        
        st.markdown(f"**문제:** {error_info.user_message}")
        st.markdown(f"**해결방법:** {error_info.suggestion}")
        
        # Show retry progress if applicable
        if error_info.retry_possible and error_info.current_retry > 0:
            progress_text = f"재시도 중... ({error_info.current_retry}/{error_info.max_retries})"
            st.info(f"🔄 {progress_text}")
        
        # Show alternative options
        self._show_api_alternatives(error_info)
    
    def _show_api_alternatives(self, error_info: ErrorInfo) -> None:
        """Show alternative options for API errors."""
        if error_info.error_type == ErrorType.API_COMMUNICATION:
            with st.expander("🔄 대안 방법"):
                st.markdown("""
                **다른 AI 모델 시도:**
                - Google Gemini ↔ Groq 모델 변경
                - 네트워크 상태 확인 후 재시도
                
                **문제 해결 단계:**
                1. 인터넷 연결 확인
                2. 잠시 후 다시 시도
                3. 다른 AI 모델 선택
                4. 파일 크기 줄이기
                """)
    
    def display_validation_error(self, error_info: ErrorInfo, data_context: str = "") -> None:
        """
        Display data validation error with specific guidance.
        
        Args:
            error_info: Error information
            data_context: Context about the data being validated
        """
        st.error(f"📊 **데이터 검증 오류**")
        
        if data_context:
            st.markdown(f"**데이터:** {data_context}")
        
        st.markdown(f"**문제:** {error_info.user_message}")
        st.markdown(f"**해결방법:** {error_info.suggestion}")
        
        # Show data format requirements
        self._show_data_format_help(error_info)
    
    def _show_data_format_help(self, error_info: ErrorInfo) -> None:
        """Show data format requirements based on error type."""
        if "컬럼" in error_info.message or "column" in error_info.message:
            with st.expander("📋 Excel 파일 형식 요구사항"):
                st.markdown("""
                **서술형 문항용 Excel:**
                | 학생 이름 | 반 | 답안 |
                |----------|----|----|
                | 김철수 | 1반 | 학생의 서술형 답안... |
                | 이영희 | 2반 | 학생의 서술형 답안... |
                
                **백지도형 문항용 Excel:**
                | 학생 이름 | 반 |
                |----------|----| 
                | 김철수 | 1반 |
                | 이영희 | 2반 |
                """)
        
        elif "중복" in error_info.message or "duplicate" in error_info.message:
            with st.expander("👥 중복 데이터 해결 방법"):
                st.markdown("""
                **중복 학생 이름 해결:**
                - 동명이인의 경우: "김철수(1)", "김철수(2)" 형식 사용
                - 오타 확인: 띄어쓰기, 특수문자 확인
                - 반 정보 활용: "1반 김철수", "2반 김철수" 형식
                """)
    
    def display_progress_with_error_handling(
        self, 
        current: int, 
        total: int, 
        current_item: str = "",
        recent_errors: List[ErrorInfo] = None
    ) -> None:
        """
        Display progress with error information.
        
        Args:
            current: Current progress count
            total: Total items to process
            current_item: Currently processing item name
            recent_errors: List of recent errors during processing
        """
        # Progress bar
        progress = current / total if total > 0 else 0
        st.progress(progress)
        
        # Progress text
        progress_text = f"진행률: {current}/{total} ({progress:.1%})"
        if current_item:
            progress_text += f" - 현재: {current_item}"
        st.text(progress_text)
        
        # Show recent errors if any
        if recent_errors:
            error_count = len(recent_errors)
            if error_count > 0:
                st.warning(f"⚠️ {error_count}개의 오류가 발생했습니다.")
                
                with st.expander(f"오류 목록 ({error_count}개)"):
                    for i, error in enumerate(recent_errors[-5:], 1):  # Show last 5 errors
                        st.markdown(f"**{i}.** {error.user_message}")
                        if error.suggestion:
                            st.markdown(f"   💡 {error.suggestion}")
    
    def display_error_summary(self, error_summary: Dict[str, Any]) -> None:
        """
        Display summary of errors that occurred during processing.
        
        Args:
            error_summary: Summary of errors from error handler
        """
        if error_summary["total_errors"] == 0:
            st.success("✅ 오류 없이 처리가 완료되었습니다.")
            return
        
        total_errors = error_summary["total_errors"]
        st.warning(f"⚠️ 총 {total_errors}개의 오류가 발생했습니다.")
        
        # Error type breakdown
        if error_summary.get("error_counts"):
            with st.expander("📊 오류 유형별 통계"):
                for error_type, count in error_summary["error_counts"].items():
                    st.markdown(f"- **{error_type}**: {count}회")
        
        # Recent errors
        recent_errors = error_summary.get("recent_errors", [])
        if recent_errors:
            with st.expander(f"🔍 최근 오류 목록 ({len(recent_errors)}개)"):
                for i, error in enumerate(recent_errors, 1):
                    severity_icon = self.error_icons.get(
                        ErrorSeverity(error["severity"]), "❌"
                    )
                    st.markdown(f"**{i}.** {severity_icon} {error['message']}")
                    if error.get("code"):
                        st.text(f"   코드: {error['code']}")
    
    def display_recovery_options(self, error_info: ErrorInfo) -> Dict[str, bool]:
        """
        Display recovery options for errors and return user choices.
        
        Args:
            error_info: Error information
            
        Returns:
            Dictionary of user choices for recovery actions
        """
        st.markdown("### 🔧 복구 옵션")
        
        choices = {}
        
        # Retry option
        if error_info.retry_possible:
            choices["retry"] = st.button(
                "🔄 다시 시도",
                key=f"retry_{error_info.error_code}_{time.time()}",
                help="같은 작업을 다시 시도합니다."
            )
        
        # Alternative options based on error type
        if error_info.error_type == ErrorType.FILE_PROCESSING:
            choices["reupload"] = st.button(
                "📁 파일 다시 업로드",
                key=f"reupload_{error_info.error_code}_{time.time()}",
                help="다른 파일을 업로드합니다."
            )
        
        elif error_info.error_type == ErrorType.API_COMMUNICATION:
            choices["change_model"] = st.button(
                "🤖 다른 AI 모델 선택",
                key=f"change_model_{error_info.error_code}_{time.time()}",
                help="다른 AI 모델로 변경합니다."
            )
        
        # Reset option
        choices["reset"] = st.button(
            "🔄 처음부터 다시 시작",
            key=f"reset_{error_info.error_code}_{time.time()}",
            help="모든 설정을 초기화하고 처음부터 시작합니다."
        )
        
        return choices
    
    def display_inline_error(self, message: str, suggestion: str = "") -> None:
        """
        Display inline error message for form validation.
        
        Args:
            message: Error message to display
            suggestion: Optional suggestion for fixing the error
        """
        st.markdown(f"<span style='color: red;'>❌ {message}</span>", unsafe_allow_html=True)
        if suggestion:
            st.markdown(f"<span style='color: #666; font-size: 0.9em;'>💡 {suggestion}</span>", unsafe_allow_html=True)
    
    def display_success_with_warnings(self, success_message: str, warnings: List[str] = None) -> None:
        """
        Display success message with optional warnings.
        
        Args:
            success_message: Main success message
            warnings: List of warning messages
        """
        st.success(f"✅ {success_message}")
        
        if warnings:
            for warning in warnings:
                st.warning(f"⚠️ {warning}")


# Global error display UI instance
error_display = ErrorDisplayUI()


def display_error(error_info: ErrorInfo, show_details: bool = False) -> None:
    """
    Convenience function for displaying errors.
    
    Args:
        error_info: Structured error information
        show_details: Whether to show technical details
    """
    error_display.display_error(error_info, show_details)


def display_file_upload_error(error_info: ErrorInfo, file_name: str = "") -> None:
    """
    Convenience function for displaying file upload errors.
    
    Args:
        error_info: Error information
        file_name: Name of the problematic file
    """
    error_display.display_file_upload_error(error_info, file_name)


def display_api_error(error_info: ErrorInfo, api_name: str = "") -> None:
    """
    Convenience function for displaying API errors.
    
    Args:
        error_info: Error information
        api_name: Name of the API service
    """
    error_display.display_api_error(error_info, api_name)


def display_validation_error(error_info: ErrorInfo, data_context: str = "") -> None:
    """
    Convenience function for displaying validation errors.
    
    Args:
        error_info: Error information
        data_context: Context about the data being validated
    """
    error_display.display_validation_error(error_info, data_context)


def display_progress_with_error_handling(
    current: int, 
    total: int, 
    current_item: str = "",
    recent_errors: List[ErrorInfo] = None
) -> None:
    """
    Convenience function for displaying progress with error handling.
    
    Args:
        current: Current progress count
        total: Total items to process
        current_item: Currently processing item name
        recent_errors: List of recent errors during processing
    """
    error_display.display_progress_with_error_handling(current, total, current_item, recent_errors)
