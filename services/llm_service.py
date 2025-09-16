"""
지리 자동 채점 시스템의 LLM 서비스

이 모듈은 Google Gemini 및 Groq API를 사용한 자동 채점을 위한 LLM 통합을 제공합니다.
구조화된 프롬프트를 통해 텍스트 기반(서술형) 및 이미지 기반(지도) 채점을 모두 지원합니다.
메모리 사용량, API 호출 효율성, 응답 캐싱에 대한 성능 최적화가 포함되어 있습니다.
"""

import json
import time
import base64
from typing import Dict, List, Optional, Union, Any, Callable
from pathlib import Path
import logging
from functools import lru_cache
import hashlib
import inspect

# Groq 클라이언트의 httpx 프록시 문제 해결책
import groq._base_client
original_sync_httpx_client_wrapper_init = groq._base_client.SyncHttpxClientWrapper.__init__

def patched_sync_httpx_client_wrapper_init(self, **kwargs):
    # 'proxies' 인수가 있으면 제거
    if 'proxies' in kwargs:
        del kwargs['proxies']
    return original_sync_httpx_client_wrapper_init(self, **kwargs)

# 패치 적용
groq._base_client.SyncHttpxClientWrapper.__init__ = patched_sync_httpx_client_wrapper_init

import google.generativeai as genai
from groq import Groq

from config import config
from models.student_model import Student
from models.rubric_model import Rubric
from models.result_model import GradingResult, ElementScore, GradingTimer
from utils.error_handler import handle_error, retry_with_backoff, ErrorType, ErrorInfo
# 시스템 모니터링 정리의 일환으로 성능 최적화 import 제거


# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMModelType:
    """LLM 모델 유형을 위한 열거형 클래스"""
    GEMINI = "gemini"
    GROQ = "groq"


class GradingType:
    """채점 유형을 위한 열거형 클래스"""
    DESCRIPTIVE = "descriptive"  # 서술형
    MAP = "map"  # 백지도형


class LLMService:
    """
    LLM 기반 자동 채점을 위한 서비스
    
    구조화된 프롬프트 생성 및 응답 파싱과 함께 
    Google Gemini (텍스트 + 이미지) 및 Groq (텍스트만) API를 지원합니다.
    """
    
    def __init__(self):
        """Initialize LLM service with API clients and performance optimization."""
        self.groq_client = None
        self._initialize_clients()
        
        # Performance optimization (removed as part of system monitoring cleanup)
        self.response_cache = {}
        self.api_call_count = 0
        self.total_processing_time = 0.0
        self._cache_hits = 0
        self._cache_requests = 0
    
    def _initialize_clients(self):
        """Initialize API clients with proper configuration."""
        try:
            # Initialize Google Gemini
            if config.GOOGLE_API_KEY:
                # Configure the API key for google-generativeai
                genai.configure(api_key=config.GOOGLE_API_KEY)
                logger.info("Google Gemini client initialized successfully")
            else:
                logger.warning("Google API key not found")
            
            # Initialize Groq
            if config.GROQ_API_KEY:
                try:
                    # Fix: Initialize Groq client with explicit parameters to avoid proxy issues
                    self.groq_client = Groq(
                        api_key=config.GROQ_API_KEY,
                        http_client=None  # Explicitly set to None to avoid proxy issues
                    )
                    logger.info("Groq client initialized successfully")
                except Exception as groq_error:
                    logger.error(f"Failed to initialize Groq client: {groq_error}")
                    self.groq_client = None
            else:
                logger.warning("Groq API key not found")
                
        except Exception as e:
            logger.error(f"Failed to initialize LLM clients: {e}")
            # Log initialization status
            if not config.GOOGLE_API_KEY:
                logger.info("Gemini client not initialized due to missing API key")
            if self.groq_client is None:
                logger.info("Groq client not initialized due to error")
    
    def select_model(self, model_type: str, grading_type: str) -> str:
        """
        Select appropriate model based on grading type and user preference.
        
        Args:
            model_type: Preferred model type (gemini/groq)
            grading_type: Type of grading (descriptive/map)
            
        Returns:
            Selected model identifier
            
        Raises:
            ValueError: If invalid combination is requested
        """
        # For map grading, only Gemini supports image analysis
        if grading_type == GradingType.MAP:
            if not config.GOOGLE_API_KEY:
                raise ValueError("Gemini API is required for map grading but not available")
            return LLMModelType.GEMINI
        
        # For descriptive grading, allow user choice
        if grading_type == GradingType.DESCRIPTIVE:
            if model_type == LLMModelType.GEMINI and config.GOOGLE_API_KEY:
                return LLMModelType.GEMINI
            elif model_type == LLMModelType.GROQ and self.groq_client:
                return LLMModelType.GROQ
            else:
                # Fallback to available model
                if config.GOOGLE_API_KEY:
                    return LLMModelType.GEMINI
                elif self.groq_client:
                    return LLMModelType.GROQ
                else:
                    raise ValueError("No LLM models available")
        
        raise ValueError(f"Invalid grading type: {grading_type}")
    
    def generate_prompt(
        self, 
        rubric: Rubric,
        student_answer: str = "", 
        references: Optional[List[str]] = None,
        grading_type: str = GradingType.DESCRIPTIVE
    ) -> str:
        """
        Generate structured prompt for LLM grading.
        
        Args:
            rubric: Evaluation rubric
            student_answer: Student's text answer (for descriptive questions)
            references: Reference materials from RAG (for descriptive questions)
            grading_type: Type of grading (descriptive/map)
            
        Returns:
            Structured prompt string
        """
        prompt_parts = []
        
        # 1. System role definition
        if grading_type == GradingType.MAP:
            prompt_parts.append("당신은 지리 교과목 전문 채점자입니다. 학생이 작성한 백지도 답안을 분석하여 채점해주세요.")
        else:
            prompt_parts.append("당신은 지리 교과목 전문 채점자입니다. 학생의 서술형 답안을 분석하여 채점해주세요.")
        
        # 2. Reference materials (descriptive only)
        if grading_type == GradingType.DESCRIPTIVE and references:
            prompt_parts.append("\n다음은 채점 참고 자료입니다:")
            for i, ref in enumerate(references, 1):
                # Limit each reference chunk to 300 characters
                clean_ref = ref.strip()
                if len(clean_ref) > 300:
                    clean_ref = clean_ref[:300] + "..."
                prompt_parts.append(f"참고자료 {i}: {clean_ref}")
        
        # 3. Evaluation rubric
        prompt_parts.append("\n다음은 평가 루브릭입니다:")
        for element in rubric.elements:
            prompt_parts.append(f"\n평가요소: {element.name} (최대 {element.max_score}점)")
            for criteria in element.criteria:
                prompt_parts.append(f"  {criteria.score}점: {criteria.description}")
        
        # 4. Student answer
        if grading_type == GradingType.MAP:
            prompt_parts.append("\n다음은 학생이 작성한 백지도 답안입니다. 이미지를 분석하여 채점해주세요.")
        else:
            prompt_parts.append(f"\n다음은 학생 답안입니다:\n{student_answer}")
        
        # 5. Output format specification
        prompt_parts.append(f"""
다음 JSON 형식으로 채점 결과를 제공해주세요:
{{
  "scores": {{
    {', '.join([f'"{element.name}": 점수' for element in rubric.elements])}
  }},
  "reasoning": {{
    {', '.join([f'"{element.name}": "점수 부여 근거"' for element in rubric.elements])}
  }},
  "feedback": "학생을 위한 개선 피드백",
  "total_score": {rubric.total_max_score}
}}

중요: 반드시 위의 JSON 형식을 정확히 따라주세요. 각 평가요소에 대해 루브릭에 명시된 점수만 부여하세요.
""")
        
        return "\n".join(prompt_parts)
    
    def _cleanup_cache(self):
        """Clean up internal caches to free memory."""
        self.response_cache.clear()
        logger.info("LLM service cache cleaned up")
    
    def _generate_cache_key(self, prompt: str, image_path: Optional[str] = None) -> str:
        """Generate cache key for API responses."""
        key_data = prompt
        if image_path:
            # Include image file hash for cache key
            try:
                with open(image_path, 'rb') as f:
                    image_hash = hashlib.md5(f.read()).hexdigest()[:8]
                key_data += f"_img_{image_hash}"
            except Exception:
                key_data += f"_img_{image_path}"
        
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached API response if available and valid."""
        self._cache_requests += 1
        
        if cache_key in self.response_cache:
            cached_data = self.response_cache[cache_key]
            # Check if cache is still valid (TTL)
            if time.time() - cached_data['timestamp'] < getattr(config, 'API_CACHE_TTL_SECONDS', 300):
                self._cache_hits += 1
                return cached_data['response']
            else:
                # Remove expired cache entry
                del self.response_cache[cache_key]
        return None
    
    def _cache_response(self, cache_key: str, response: Dict[str, Any]):
        """Cache API response with TTL."""
        # Implement simple LRU eviction if cache is full
        if len(self.response_cache) >= getattr(config, 'API_CACHE_MAX_SIZE', 100):
            # Remove oldest entry
            oldest_key = min(self.response_cache.keys(), 
                           key=lambda k: self.response_cache[k]['timestamp'])
            del self.response_cache[oldest_key]
        
        self.response_cache[cache_key] = {
            'response': response,
            'timestamp': time.time()
        }
    
    def _create_rubric_hash(self, rubric: Rubric) -> str:
        """Create hash for rubric to enable caching."""
        rubric_str = ""
        for element in rubric.elements:
            rubric_str += f"{element.name}:{element.max_score}:"
            for criteria in element.criteria:
                rubric_str += f"{criteria.score}-{criteria.description};"
        return hashlib.md5(rubric_str.encode()).hexdigest()
    
    def _create_references_hash(self, references: Optional[List[str]]) -> Optional[str]:
        """Create hash for references to enable caching."""
        if not references:
            return None
        references_str = "".join(references)
        return hashlib.md5(references_str.encode()).hexdigest()
    
    def generate_prompt_with_caching(
        self, 
        rubric: Rubric, 
        student_answer: str = "", 
        references: Optional[List[str]] = None,
        grading_type: str = GradingType.DESCRIPTIVE
    ) -> str:
        """Generate prompt with caching support."""
        rubric_hash = self._create_rubric_hash(rubric)
        references_hash = self._create_references_hash(references)
        
        return self.generate_prompt(
            rubric=rubric,
            student_answer=student_answer,
            references=references,
            grading_type=grading_type
        )
    
    def _encode_image(self, image_path: str) -> str:
        """
        Encode image file to base64 for API transmission.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded image string
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            raise
    
    def call_gemini_api(
        self, 
        prompt: str, 
        image_path: Optional[str] = None,
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Call Google Gemini API for text/image analysis with caching and optimization.
        
        Args:
            prompt: Text prompt for the model
            image_path: Optional path to image file
            max_retries: Maximum number of retry attempts
            
        Returns:
            API response as dictionary
            
        Raises:
            Exception: If API call fails after retries
        """
        if not config.GOOGLE_API_KEY:
            error_info = handle_error(
                ValueError("Gemini client not initialized"),
                ErrorType.AUTHENTICATION,
                context="call_gemini_api: client not initialized",
                user_context="Google Gemini API 호출"
            )
            raise ValueError(error_info.user_message)
        
        # Check cache first
        cache_key = self._generate_cache_key(prompt, image_path)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            logger.debug("Using cached Gemini API response")
            return cached_response
        
        def _make_api_call():
            # Prepare content for API call following official documentation
            # Reference: https://ai.google.dev/gemini-api/docs/vision
            
            if image_path and Path(image_path).exists():
                print(f"DEBUG: Adding image to Gemini API request: {image_path}")
                try:
                    # Read image file
                    with open(image_path, "rb") as image_file:
                        image_data = image_file.read()
                    
                    print(f"DEBUG: Successfully read image data: {len(image_data)} bytes")
                    
                    # Determine MIME type based on file extension
                    file_ext = Path(image_path).suffix.lower()
                    mime_type = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg', 
                        '.png': 'image/png',
                        '.bmp': 'image/bmp',
                        '.tiff': 'image/tiff'
                    }.get(file_ext, 'image/jpeg')  # Default to jpeg
                    
                    print(f"DEBUG: Using MIME type: {mime_type} for file extension: {file_ext}")
                    
                    # Create image part using google-generativeai
                    image_part = {
                        'mime_type': mime_type,
                        'data': image_data
                    }
                    
                    # According to official docs: put text and image in same contents array
                    content = [prompt, image_part]
                    print(f"DEBUG: Created content with text and image")
                    
                except Exception as e:
                    print(f"DEBUG: Failed to read image: {e}")
                    error_info = handle_error(
                        e,
                        ErrorType.FILE_PROCESSING,
                        context=f"call_gemini_api: failed to read image {image_path}",
                        user_context="이미지 파일 읽기"
                    )
                    raise ValueError(error_info.user_message)
            else:
                print(f"DEBUG: No image provided or image file not found")
                print(f"DEBUG: image_path: {image_path}")
                if image_path:
                    print(f"DEBUG: Path exists: {Path(image_path).exists()}")
                
                # Text only content
                content = [prompt]
            
            # Generate response
            try:
                # Use google-generativeai GenerativeModel with latest model
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(content)
                
                if response.text:
                    result = {"text": response.text}
                    # Cache successful response
                    self._cache_response(cache_key, result)
                    self.api_call_count += 1
                    return result
                else:
                    raise ValueError("Empty response from Gemini API")
            
            except Exception as e:
                error_str = str(e).lower()
                
                if "quota" in error_str or "limit" in error_str:
                    error_info = handle_error(
                        e,
                        ErrorType.RATE_LIMIT,
                        context="call_gemini_api: quota exceeded",
                        user_context="Google Gemini API 호출"
                    )
                    raise Exception(error_info.user_message)
                
                elif "timeout" in error_str:
                    error_info = handle_error(
                        e,
                        ErrorType.NETWORK,
                        context="call_gemini_api: timeout",
                        user_context="Google Gemini API 호출"
                    )
                    raise Exception(error_info.user_message)
                
                elif "auth" in error_str or "key" in error_str:
                    error_info = handle_error(
                        e,
                        ErrorType.AUTHENTICATION,
                        context="call_gemini_api: authentication failed",
                        user_context="Google Gemini API 인증"
                    )
                    raise Exception(error_info.user_message)
                
                else:
                    error_info = handle_error(
                        e,
                        ErrorType.API_COMMUNICATION,
                        context="call_gemini_api: general API error",
                        user_context="Google Gemini API 호출"
                    )
                    raise Exception(error_info.user_message)
        
        # Use retry mechanism with exponential backoff
        max_retries = max_retries or config.MAX_RETRIES
        return retry_with_backoff(
            _make_api_call,
            ErrorType.API_COMMUNICATION,
            max_retries=max_retries,
            context="call_gemini_api"
        )
    
    def get_selected_groq_model(self) -> str:
        """세션 상태에서 선택된 Groq 모델을 가져옵니다."""
        try:
            import streamlit as st
            if hasattr(st, 'session_state') and 'selected_groq_model' in st.session_state:
                return st.session_state.selected_groq_model
        except:
            pass
        
        # 기본값 반환
        return "qwen/qwen3-32b"

    def call_groq_api(
        self, 
        prompt: str, 
        model_name: Optional[str] = None,
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Call Groq API for text analysis with caching and optimization.
        
        Args:
            prompt: Text prompt for the model
            model_name: Name of the Groq model to use (None = auto-select from session)
            max_retries: Maximum number of retry attempts
            
        Returns:
            API response as dictionary
            
        Raises:
            Exception: If API call fails after retries
        """
        # 모델명이 지정되지 않으면 세션에서 가져오기
        if model_name is None:
            model_name = self.get_selected_groq_model()
        
        print(f"DEBUG: Using Groq model: {model_name}")
        
        if not self.groq_client:
            error_info = handle_error(
                ValueError("Groq client not initialized"),
                ErrorType.AUTHENTICATION,
                context="call_groq_api: client not initialized",
                user_context="Groq API 호출"
            )
            raise ValueError(error_info.user_message)
        
        # Check cache first
        cache_key = self._generate_cache_key(prompt)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            logger.debug("Using cached Groq API response")
            return cached_response
        
        def _make_api_call():
            try:
                # 모델별 max_tokens 설정
                if "gpt-oss" in model_name:
                    max_tokens = 65536  # GPT-OSS 120B 모델의 최대값
                elif "qwen" in model_name:
                    max_tokens = 40960  # Qwen3 32B 모델은 더 높은 값 지원
                else:
                    max_tokens = 65536  # 안전한 기본값
                
                print(f"DEBUG: Using max_tokens={max_tokens} for model {model_name}")
                
                # Call Groq API
                response = self.groq_client.chat.completions.create(
                    model=model_name,  # Use specified Groq model
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,  # Low temperature for consistent grading
                    max_tokens=max_tokens
                )
                
                if response.choices and response.choices[0].message.content:
                    result = {"text": response.choices[0].message.content}
                    # Cache successful response
                    self._cache_response(cache_key, result)
                    self.api_call_count += 1
                    return result
                else:
                    raise ValueError("Empty response from Groq API")
            
            except Exception as e:
                error_str = str(e).lower()
                
                if "quota" in error_str or "limit" in error_str or "rate" in error_str:
                    error_info = handle_error(
                        e,
                        ErrorType.RATE_LIMIT,
                        context="call_groq_api: rate limit exceeded",
                        user_context="Groq API 호출"
                    )
                    raise Exception(error_info.user_message)
                
                elif "timeout" in error_str:
                    error_info = handle_error(
                        e,
                        ErrorType.NETWORK,
                        context="call_groq_api: timeout",
                        user_context="Groq API 호출"
                    )
                    raise Exception(error_info.user_message)
                
                elif "auth" in error_str or "key" in error_str or "unauthorized" in error_str:
                    error_info = handle_error(
                        e,
                        ErrorType.AUTHENTICATION,
                        context="call_groq_api: authentication failed",
                        user_context="Groq API 인증"
                    )
                    raise Exception(error_info.user_message)
                
                else:
                    error_info = handle_error(
                        e,
                        ErrorType.API_COMMUNICATION,
                        context="call_groq_api: general API error",
                        user_context="Groq API 호출"
                    )
                    raise Exception(error_info.user_message)
        
        # Use retry mechanism with exponential backoff
        max_retries = max_retries or config.MAX_RETRIES
        return retry_with_backoff(
            _make_api_call,
            ErrorType.API_COMMUNICATION,
            max_retries=max_retries,
            context="call_groq_api"
        )
    
    def parse_response(self, response_text: str, rubric: Rubric) -> Dict[str, Any]:
        """
        Parse and validate LLM response.
        
        Args:
            response_text: Raw response text from LLM
            rubric: Evaluation rubric for validation
            
        Returns:
            Parsed and validated response dictionary
            
        Raises:
            ValueError: If response format is invalid
        """
        try:
            # Debug: Log the actual response content
            print(f"DEBUG: API Response (length: {len(response_text)})")
            print(f"DEBUG: API Response content: {repr(response_text)}")
            
            # Extract JSON from response (handle cases where LLM adds extra text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                error_info = handle_error(
                    ValueError("No JSON found in response"),
                    ErrorType.PARSING,
                    context=f"parse_response: no JSON in response text (length: {len(response_text)})",
                    user_context="AI 응답 파싱"
                )
                raise ValueError(error_info.user_message)
            
            json_text = response_text[json_start:json_end]
            
            try:
                parsed = json.loads(json_text)
            except json.JSONDecodeError as e:
                error_info = handle_error(
                    e,
                    ErrorType.PARSING,
                    context=f"parse_response: JSON decode error in text: {json_text[:200]}...",
                    user_context="AI 응답 JSON 파싱"
                )
                raise ValueError(error_info.user_message)
            
            # Validate required fields
            required_fields = ['scores', 'reasoning', 'feedback', 'total_score']
            missing_fields = [field for field in required_fields if field not in parsed]
            if missing_fields:
                error_info = handle_error(
                    ValueError(f"Missing required fields: {missing_fields}"),
                    ErrorType.PARSING,
                    context=f"parse_response: missing fields {missing_fields}",
                    user_context="AI 응답 필드 검증"
                )
                raise ValueError(error_info.user_message)
            
            # Validate scores against rubric
            for element in rubric.elements:
                element_name = element.name
                if element_name not in parsed['scores']:
                    error_info = handle_error(
                        ValueError(f"Missing score for element: {element_name}"),
                        ErrorType.PARSING,
                        context=f"parse_response: missing score for {element_name}",
                        user_context="평가 요소 점수 검증"
                    )
                    raise ValueError(error_info.user_message)
                
                score = parsed['scores'][element_name]
                if not isinstance(score, (int, float)):
                    error_info = handle_error(
                        ValueError(f"Invalid score type for {element_name}: {type(score)}"),
                        ErrorType.PARSING,
                        context=f"parse_response: invalid score type {type(score)} for {element_name}",
                        user_context="점수 형식 검증"
                    )
                    raise ValueError(error_info.user_message)
                
                # Check if score is valid according to rubric
                valid_scores = [criteria.score for criteria in element.criteria]
                if score not in valid_scores:
                    logger.warning(f"Score {score} for {element_name} not in rubric: {valid_scores}")
                    # Don't raise error for this, just log warning
            
            # Validate reasoning - add default if missing
            for element in rubric.elements:
                element_name = element.name
                if element_name not in parsed['reasoning']:
                    parsed['reasoning'][element_name] = "채점 근거가 제공되지 않았습니다."
            
            return parsed
            
        except ValueError:
            # Re-raise ValueError with error info already handled
            raise
        except Exception as e:
            error_info = handle_error(
                e,
                ErrorType.PARSING,
                context=f"parse_response: unexpected parsing error",
                user_context="AI 응답 파싱"
            )
            raise ValueError(error_info.user_message)
    
    def grade_student_sequential(
        self,
        student: Student,
        rubric: Rubric,
        model_type: str,
        grading_type: str,
        references: Optional[List[str]] = None,
        groq_model_name: str = "qwen/qwen3-32b"
    ) -> GradingResult:
        """
        Grade a single student's answer sequentially.
        
        Args:
            student: Student data with answer
            rubric: Evaluation rubric
            model_type: LLM model to use
            grading_type: Type of grading (descriptive/map)
            references: Reference materials from RAG
            groq_model_name: Specific Groq model to use (default: qwen/qwen3-32b)
            
        Returns:
            Grading result with timing information
        """
        timer = GradingTimer()
        timer.start()
        
        try:
            # Select appropriate model
            selected_model = self.select_model(model_type, grading_type)
            
            # Generate prompt with caching
            prompt = self.generate_prompt_with_caching(
                rubric=rubric,
                student_answer=student.answer,
                references=references,
                grading_type=grading_type
            )
            
            # Call appropriate API
            if selected_model == LLMModelType.GEMINI:
                image_path_to_use = student.image_path if grading_type == GradingType.MAP else None
                print(f"DEBUG: Using Gemini API for student {student.name}")
                print(f"DEBUG: Grading type: {grading_type}")
                print(f"DEBUG: Student image_path: {student.image_path}")
                print(f"DEBUG: Image path to use: {image_path_to_use}")
                if image_path_to_use:
                    print(f"DEBUG: Image file exists: {Path(image_path_to_use).exists()}")
                    if Path(image_path_to_use).exists():
                        print(f"DEBUG: Image file size: {Path(image_path_to_use).stat().st_size} bytes")
                
                response = self.call_gemini_api(
                    prompt=prompt,
                    image_path=image_path_to_use
                )
            else:  # GROQ
                response = self.call_groq_api(prompt=prompt, model_name=groq_model_name)
            
            # Parse response
            parsed_result = self.parse_response(response["text"], rubric)
            
            # Stop timer and get elapsed time
            elapsed_time = timer.stop()
            
            # Create grading result
            result = GradingResult(
                student_name=student.name,
                student_class_number=student.class_number,
                grading_time_seconds=elapsed_time,
                overall_feedback=parsed_result["feedback"]
            )
            
            # Add element scores
            for element in rubric.elements:
                element_name = element.name
                score = parsed_result["scores"][element_name]
                reasoning = parsed_result["reasoning"].get(element_name, "")
                
                result.add_element_score(
                    element_name=element_name,
                    score=int(score),
                    max_score=element.max_score,
                    feedback="",  # 피드백은 별도로 설정
                    reasoning=reasoning  # 판단 근거
                )
            
            logger.info(f"Successfully graded student {student.name} in {elapsed_time:.2f}s")
            return result
            
        except Exception as e:
            # Stop timer even on error
            elapsed_time = timer.stop()
            
            logger.error(f"Failed to grade student {student.name}: {e}")
            # Create error result
            result = GradingResult(
                student_name=student.name,
                student_class_number=student.class_number,
                grading_time_seconds=elapsed_time,
                overall_feedback=f"채점 중 오류가 발생했습니다: {str(e)}"
            )
            
            # Add zero scores for all elements
            for element in rubric.elements:
                result.add_element_score(
                    element_name=element.name,
                    score=0,
                    max_score=element.max_score,
                    feedback="채점 오류로 인해 점수를 부여할 수 없습니다.",
                    reasoning="채점 처리 중 오류 발생"
                )
            
            return result
    
    def grade_students_batch(
        self,
        students: List[Student],
        rubric: Rubric,
        model_type: str,
        grading_type: str,
        references: Optional[List[str]] = None,
        groq_model_name: str = "qwen/qwen3-32b",
        progress_callback: Optional[Callable] = None
    ) -> List[GradingResult]:
        """
        Grade multiple students sequentially with progress tracking.
        
        Args:
            students: List of students to grade
            rubric: Evaluation rubric
            model_type: LLM model to use
            grading_type: Type of grading
            references: Reference materials from RAG
            groq_model_name: Specific Groq model to use (default: qwen/qwen3-32b)
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of grading results
        """
        results = []
        total_students = len(students)
        
        logger.info(f"Starting batch grading for {total_students} students")
        
        for i, student in enumerate(students, 1):
            try:
                # Grade individual student
                result = self.grade_student_sequential(
                    student=student,
                    rubric=rubric,
                    model_type=model_type,
                    grading_type=grading_type,
                    references=references,
                    groq_model_name=groq_model_name
                )
                
                results.append(result)
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(i, total_students, result)
                
                logger.info(f"Completed {i}/{total_students} students")
                
            except Exception as e:
                logger.error(f"Failed to grade student {student.name}: {e}")
                # Continue with next student
                continue
        
        logger.info(f"Batch grading completed. {len(results)}/{total_students} students graded successfully")
        return results
    
    def validate_api_availability(self) -> Dict[str, bool]:
        """
        Check availability of API services.
        
        Returns:
            Dictionary with API availability status
        """
        return {
            "gemini": bool(config.GOOGLE_API_KEY),
            "groq": self.groq_client is not None
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get LLM service performance statistics."""
        # Since @lru_cache was removed, we can't get cache info
        prompt_cache_info = {
            "hits": 0,
            "misses": 0,
            "maxsize": 0,
            "currsize": 0
        }
        
        return {
            "api_call_count": self.api_call_count,
            "total_processing_time": self.total_processing_time,
            "avg_processing_time": self.total_processing_time / max(self.api_call_count, 1),
            "cache_size": len(self.response_cache),
            "cache_hit_rate": self._calculate_cache_hit_rate(),
            "prompt_cache_info": prompt_cache_info
        }
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        if self._cache_requests == 0:
            return 0.0
        
        return (self._cache_hits / self._cache_requests) * 100
    
    def optimize_memory_usage(self) -> Dict[str, Any]:
        """Optimize memory usage by cleaning up caches and resources."""
        cache_size = len(self.response_cache)
        
        # Clear old cache entries
        current_time = time.time()
        expired_keys = [
            key for key, data in self.response_cache.items()
            if current_time - data['timestamp'] > getattr(config, 'API_CACHE_TTL_SECONDS', 300)
        ]
        
        for key in expired_keys:
            del self.response_cache[key]
        
        # Clear prompt cache if it's getting large
        # Since @lru_cache was removed, there's no prompt cache to clear
        pass
        
        logger.info(f"LLM memory optimization: removed {len(expired_keys)} expired cache entries, "
                   f"cleared prompt cache (0 entries)")
        
        return {
            "expired_entries_removed": len(expired_keys),
            "prompt_cache_cleared": False,
            "cache_size_before": cache_size,
            "cache_size_after": len(self.response_cache)
        }