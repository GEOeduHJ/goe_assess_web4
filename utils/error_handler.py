"""
Comprehensive Error Handling System for Geography Auto-Grading Platform

This module provides centralized error handling, user-friendly error messages,
and recovery mechanisms for various error scenarios.
"""

import logging
import traceback
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass
import time
import streamlit as st


class ErrorType(Enum):
    """Enumeration of error types for categorized handling."""
    FILE_PROCESSING = "file_processing"
    API_COMMUNICATION = "api_communication"
    VALIDATION = "validation"
    SYSTEM = "system"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    MEMORY = "memory"
    PARSING = "parsing"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    """Structured error information."""
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    user_message: str
    suggestion: str
    technical_details: Optional[str] = None
    error_code: Optional[str] = None
    retry_possible: bool = False
    max_retries: int = 0
    current_retry: int = 0


class ErrorHandler:
    """
    Centralized error handler for the geography auto-grading platform.
    
    Provides user-friendly error messages, retry mechanisms, and recovery strategies.
    """
    
    def __init__(self):
        """Initialize error handler with logging configuration."""
        self.logger = logging.getLogger(__name__)
        self.error_history: List[ErrorInfo] = []
        self.retry_delays = [1, 2, 4, 8, 16]  # Exponential backoff delays
        
        # Configure logging if not already configured
        if not self.logger.handlers:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    
    def handle_error(
        self, 
        error: Exception, 
        error_type: ErrorType,
        context: str = "",
        user_context: str = "",
        retry_count: int = 0
    ) -> ErrorInfo:
        """
        Handle an error with appropriate categorization and user messaging.
        
        Args:
            error: The exception that occurred
            error_type: Type of error for categorized handling
            context: Technical context where error occurred
            user_context: User-friendly context description
            retry_count: Current retry attempt number
            
        Returns:
            ErrorInfo: Structured error information
        """
        try:
            # Create error info based on type
            error_info = self._create_error_info(error, error_type, context, user_context, retry_count)
            
            # Log the error
            self._log_error(error_info, error)
            
            # Add to error history
            self.error_history.append(error_info)
            
            # Keep only last 100 errors
            if len(self.error_history) > 100:
                self.error_history = self.error_history[-100:]
            
            return error_info
            
        except Exception as e:
            # Fallback error handling
            self.logger.error(f"Error in error handler: {e}")
            return self._create_fallback_error_info(error)
    
    def _create_error_info(
        self, 
        error: Exception, 
        error_type: ErrorType, 
        context: str, 
        user_context: str,
        retry_count: int
    ) -> ErrorInfo:
        """Create structured error information based on error type."""
        
        if error_type == ErrorType.FILE_PROCESSING:
            return self._handle_file_processing_error(error, context, user_context)
        
        elif error_type == ErrorType.API_COMMUNICATION:
            return self._handle_api_communication_error(error, context, user_context, retry_count)
        
        elif error_type == ErrorType.VALIDATION:
            return self._handle_validation_error(error, context, user_context)
        
        elif error_type == ErrorType.NETWORK:
            return self._handle_network_error(error, context, user_context, retry_count)
        
        elif error_type == ErrorType.AUTHENTICATION:
            return self._handle_authentication_error(error, context, user_context)
        
        elif error_type == ErrorType.RATE_LIMIT:
            return self._handle_rate_limit_error(error, context, user_context, retry_count)
        
        elif error_type == ErrorType.MEMORY:
            return self._handle_memory_error(error, context, user_context)
        
        elif error_type == ErrorType.PARSING:
            return self._handle_parsing_error(error, context, user_context)
        
        else:
            return self._handle_system_error(error, context, user_context)
    
    def _handle_file_processing_error(self, error: Exception, context: str, user_context: str) -> ErrorInfo:
        """Handle file processing errors with specific guidance."""
        error_str = str(error).lower()
        
        if "permission" in error_str or "access" in error_str:
            return ErrorInfo(
                error_type=ErrorType.FILE_PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                message=f"파일 접근 권한 오류: {error}",
                user_message="파일에 접근할 수 없습니다.",
                suggestion="파일이 다른 프로그램에서 사용 중이지 않은지 확인하고, 파일 권한을 확인해주세요.",
                technical_details=f"Context: {context}",
                error_code="FILE_ACCESS_DENIED"
            )
        
        elif "not found" in error_str or "존재하지" in error_str:
            return ErrorInfo(
                error_type=ErrorType.FILE_PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                message=f"파일을 찾을 수 없음: {error}",
                user_message="업로드한 파일을 찾을 수 없습니다.",
                suggestion="파일을 다시 업로드해주세요. 파일명에 특수문자가 포함되어 있지 않은지 확인해주세요.",
                technical_details=f"Context: {context}",
                error_code="FILE_NOT_FOUND"
            )
        
        elif "format" in error_str or "형식" in error_str or "extension" in error_str:
            return ErrorInfo(
                error_type=ErrorType.FILE_PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                message=f"파일 형식 오류: {error}",
                user_message="지원하지 않는 파일 형식입니다.",
                suggestion="Excel 파일은 .xlsx 또는 .xls, 문서는 .pdf 또는 .docx, 이미지는 .jpg, .png 형식을 사용해주세요.",
                technical_details=f"Context: {context}",
                error_code="INVALID_FILE_FORMAT"
            )
        
        elif "size" in error_str or "크기" in error_str or "large" in error_str:
            return ErrorInfo(
                error_type=ErrorType.FILE_PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                message=f"파일 크기 오류: {error}",
                user_message="파일 크기가 너무 큽니다.",
                suggestion="파일 크기를 50MB 이하로 줄여주세요. 이미지의 경우 해상도를 낮추거나 압축해주세요.",
                technical_details=f"Context: {context}",
                error_code="FILE_TOO_LARGE"
            )
        
        elif "corrupt" in error_str or "damaged" in error_str or "손상" in error_str:
            return ErrorInfo(
                error_type=ErrorType.FILE_PROCESSING,
                severity=ErrorSeverity.HIGH,
                message=f"파일 손상 오류: {error}",
                user_message="파일이 손상되어 읽을 수 없습니다.",
                suggestion="파일을 다시 생성하거나 다른 파일을 사용해주세요. 파일이 완전히 업로드되었는지 확인해주세요.",
                technical_details=f"Context: {context}",
                error_code="FILE_CORRUPTED"
            )
        
        else:
            return ErrorInfo(
                error_type=ErrorType.FILE_PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                message=f"파일 처리 오류: {error}",
                user_message="파일을 처리하는 중 오류가 발생했습니다.",
                suggestion="파일 형식과 내용을 확인하고 다시 시도해주세요. 문제가 지속되면 다른 파일을 사용해보세요.",
                technical_details=f"Context: {context}",
                error_code="FILE_PROCESSING_ERROR"
            )
    
    def _handle_api_communication_error(self, error: Exception, context: str, user_context: str, retry_count: int) -> ErrorInfo:
        """Handle API communication errors with retry logic."""
        error_str = str(error).lower()
        
        if "timeout" in error_str or "시간초과" in error_str:
            return ErrorInfo(
                error_type=ErrorType.API_COMMUNICATION,
                severity=ErrorSeverity.MEDIUM,
                message=f"API 시간초과: {error}",
                user_message="AI 서비스 응답 시간이 초과되었습니다.",
                suggestion="네트워크 연결을 확인하고 잠시 후 다시 시도해주세요.",
                technical_details=f"Context: {context}, Retry: {retry_count}",
                error_code="API_TIMEOUT",
                retry_possible=True,
                max_retries=3,
                current_retry=retry_count
            )
        
        elif "connection" in error_str or "연결" in error_str:
            return ErrorInfo(
                error_type=ErrorType.API_COMMUNICATION,
                severity=ErrorSeverity.HIGH,
                message=f"API 연결 오류: {error}",
                user_message="AI 서비스에 연결할 수 없습니다.",
                suggestion="인터넷 연결을 확인하고 잠시 후 다시 시도해주세요.",
                technical_details=f"Context: {context}, Retry: {retry_count}",
                error_code="API_CONNECTION_ERROR",
                retry_possible=True,
                max_retries=3,
                current_retry=retry_count
            )
        
        elif "quota" in error_str or "limit" in error_str or "할당량" in error_str:
            return ErrorInfo(
                error_type=ErrorType.API_COMMUNICATION,
                severity=ErrorSeverity.HIGH,
                message=f"API 할당량 초과: {error}",
                user_message="AI 서비스 사용 한도에 도달했습니다.",
                suggestion="잠시 후 다시 시도하거나 다른 AI 모델을 선택해주세요.",
                technical_details=f"Context: {context}",
                error_code="API_QUOTA_EXCEEDED",
                retry_possible=False
            )
        
        else:
            return ErrorInfo(
                error_type=ErrorType.API_COMMUNICATION,
                severity=ErrorSeverity.MEDIUM,
                message=f"API 통신 오류: {error}",
                user_message="AI 서비스와의 통신 중 오류가 발생했습니다.",
                suggestion="잠시 후 다시 시도해주세요. 문제가 지속되면 다른 AI 모델을 선택해보세요.",
                technical_details=f"Context: {context}, Retry: {retry_count}",
                error_code="API_COMMUNICATION_ERROR",
                retry_possible=True,
                max_retries=3,
                current_retry=retry_count
            )
    
    def _handle_validation_error(self, error: Exception, context: str, user_context: str) -> ErrorInfo:
        """Handle data validation errors."""
        error_str = str(error).lower()
        
        if "column" in error_str or "컬럼" in error_str or "열" in error_str:
            return ErrorInfo(
                error_type=ErrorType.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                message=f"데이터 형식 오류: {error}",
                user_message="Excel 파일의 열 구성이 올바르지 않습니다.",
                suggestion="필수 열(학생 이름, 반, 답안)이 모두 포함되어 있는지 확인해주세요.",
                technical_details=f"Context: {context}",
                error_code="INVALID_COLUMN_FORMAT"
            )
        
        elif "empty" in error_str or "비어" in error_str or "null" in error_str:
            return ErrorInfo(
                error_type=ErrorType.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                message=f"데이터 누락 오류: {error}",
                user_message="필수 데이터가 누락되었습니다.",
                suggestion="모든 학생의 이름, 반, 답안 정보가 입력되어 있는지 확인해주세요.",
                technical_details=f"Context: {context}",
                error_code="MISSING_REQUIRED_DATA"
            )
        
        elif "duplicate" in error_str or "중복" in error_str:
            return ErrorInfo(
                error_type=ErrorType.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                message=f"중복 데이터 오류: {error}",
                user_message="중복된 학생 이름이 있습니다.",
                suggestion="학생 이름이 중복되지 않도록 수정해주세요.",
                technical_details=f"Context: {context}",
                error_code="DUPLICATE_DATA"
            )
        
        else:
            return ErrorInfo(
                error_type=ErrorType.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                message=f"데이터 검증 오류: {error}",
                user_message="업로드한 데이터에 문제가 있습니다.",
                suggestion="데이터 형식과 내용을 확인하고 다시 시도해주세요.",
                technical_details=f"Context: {context}",
                error_code="VALIDATION_ERROR"
            )
    
    def _handle_network_error(self, error: Exception, context: str, user_context: str, retry_count: int) -> ErrorInfo:
        """Handle network-related errors."""
        return ErrorInfo(
            error_type=ErrorType.NETWORK,
            severity=ErrorSeverity.HIGH,
            message=f"네트워크 오류: {error}",
            user_message="네트워크 연결에 문제가 있습니다.",
            suggestion="인터넷 연결을 확인하고 잠시 후 다시 시도해주세요.",
            technical_details=f"Context: {context}, Retry: {retry_count}",
            error_code="NETWORK_ERROR",
            retry_possible=True,
            max_retries=3,
            current_retry=retry_count
        )
    
    def _handle_authentication_error(self, error: Exception, context: str, user_context: str) -> ErrorInfo:
        """Handle authentication errors."""
        return ErrorInfo(
            error_type=ErrorType.AUTHENTICATION,
            severity=ErrorSeverity.CRITICAL,
            message=f"인증 오류: {error}",
            user_message="AI 서비스 인증에 실패했습니다.",
            suggestion="API 키 설정을 확인해주세요. 관리자에게 문의하시기 바랍니다.",
            technical_details=f"Context: {context}",
            error_code="AUTHENTICATION_ERROR"
        )
    
    def _handle_rate_limit_error(self, error: Exception, context: str, user_context: str, retry_count: int) -> ErrorInfo:
        """Handle rate limiting errors."""
        return ErrorInfo(
            error_type=ErrorType.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            message=f"요청 한도 초과: {error}",
            user_message="요청이 너무 많아 일시적으로 제한되었습니다.",
            suggestion="잠시 기다린 후 다시 시도해주세요.",
            technical_details=f"Context: {context}, Retry: {retry_count}",
            error_code="RATE_LIMIT_EXCEEDED",
            retry_possible=True,
            max_retries=5,
            current_retry=retry_count
        )
    
    def _handle_memory_error(self, error: Exception, context: str, user_context: str) -> ErrorInfo:
        """Handle memory-related errors."""
        return ErrorInfo(
            error_type=ErrorType.MEMORY,
            severity=ErrorSeverity.HIGH,
            message=f"메모리 오류: {error}",
            user_message="처리할 데이터가 너무 많습니다.",
            suggestion="파일 크기를 줄이거나 학생 수를 나누어 처리해주세요.",
            technical_details=f"Context: {context}",
            error_code="MEMORY_ERROR"
        )
    
    def _handle_parsing_error(self, error: Exception, context: str, user_context: str) -> ErrorInfo:
        """Handle data parsing errors."""
        return ErrorInfo(
            error_type=ErrorType.PARSING,
            severity=ErrorSeverity.MEDIUM,
            message=f"데이터 파싱 오류: {error}",
            user_message="AI 응답을 처리하는 중 오류가 발생했습니다.",
            suggestion="다시 시도해주세요. 문제가 지속되면 다른 AI 모델을 선택해보세요.",
            technical_details=f"Context: {context}",
            error_code="PARSING_ERROR",
            retry_possible=True,
            max_retries=2
        )
    
    def _handle_system_error(self, error: Exception, context: str, user_context: str) -> ErrorInfo:
        """Handle general system errors."""
        return ErrorInfo(
            error_type=ErrorType.SYSTEM,
            severity=ErrorSeverity.HIGH,
            message=f"시스템 오류: {error}",
            user_message="예상치 못한 오류가 발생했습니다.",
            suggestion="페이지를 새로고침하고 다시 시도해주세요. 문제가 지속되면 관리자에게 문의하세요.",
            technical_details=f"Context: {context}",
            error_code="SYSTEM_ERROR"
        )
    
    def _create_fallback_error_info(self, error: Exception) -> ErrorInfo:
        """Create fallback error info when error handling fails."""
        return ErrorInfo(
            error_type=ErrorType.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            message=f"오류 처리 실패: {error}",
            user_message="시스템에 심각한 오류가 발생했습니다.",
            suggestion="페이지를 새로고침하고 다시 시도해주세요.",
            error_code="ERROR_HANDLER_FAILURE"
        )
    
    def _log_error(self, error_info: ErrorInfo, original_error: Exception):
        """Log error information with appropriate level."""
        log_message = f"[{error_info.error_code}] {error_info.message}"
        
        if error_info.technical_details:
            log_message += f" | Details: {error_info.technical_details}"
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, exc_info=original_error)
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, exc_info=original_error)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def retry_with_backoff(
        self, 
        func: Callable, 
        error_type: ErrorType,
        max_retries: int = 3,
        context: str = "",
        *args, 
        **kwargs
    ) -> Any:
        """
        Execute function with exponential backoff retry logic.
        
        Args:
            func: Function to execute
            error_type: Type of error expected
            max_retries: Maximum number of retry attempts
            context: Context information for error handling
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result or raises final error
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            
            except Exception as e:
                last_error = e
                error_info = self.handle_error(e, error_type, context, retry_count=attempt)
                
                if attempt < max_retries and error_info.retry_possible:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    self.logger.info(f"Retrying in {delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    break
        
        # If we get here, all retries failed
        if last_error:
            raise last_error
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors."""
        if not self.error_history:
            return {"total_errors": 0, "recent_errors": []}
        
        recent_errors = self.error_history[-10:]  # Last 10 errors
        error_counts = {}
        
        for error in self.error_history:
            error_type = error.error_type.value
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return {
            "total_errors": len(self.error_history),
            "recent_errors": [
                {
                    "type": error.error_type.value,
                    "severity": error.severity.value,
                    "message": error.user_message,
                    "code": error.error_code
                }
                for error in recent_errors
            ],
            "error_counts": error_counts
        }


# Global error handler instance
error_handler = ErrorHandler()


def handle_error(
    error: Exception, 
    error_type: ErrorType, 
    context: str = "", 
    user_context: str = "",
    retry_count: int = 0
) -> ErrorInfo:
    """
    Convenience function for handling errors.
    
    Args:
        error: The exception that occurred
        error_type: Type of error for categorized handling
        context: Technical context where error occurred
        user_context: User-friendly context description
        retry_count: Current retry attempt number
        
    Returns:
        ErrorInfo: Structured error information
    """
    return error_handler.handle_error(error, error_type, context, user_context, retry_count)


def retry_with_backoff(
    func: Callable, 
    error_type: ErrorType,
    max_retries: int = 3,
    context: str = "",
    *args, 
    **kwargs
) -> Any:
    """
    Convenience function for retrying operations with backoff.
    
    Args:
        func: Function to execute
        error_type: Type of error expected
        max_retries: Maximum number of retry attempts
        context: Context information for error handling
        *args, **kwargs: Arguments to pass to function
        
    Returns:
        Function result or raises final error
    """
    return error_handler.retry_with_backoff(func, error_type, max_retries, context, *args, **kwargs)