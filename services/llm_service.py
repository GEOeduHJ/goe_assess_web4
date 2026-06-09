"""
지리 자동 채점 시스템의 LLM 서비스

이 모듈은 Google Gemini 및 OpenAI GPT API를 사용한 자동 채점을 위한 LLM 통합을 제공합니다.
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

from google import genai
from google.genai import types
from openai import OpenAI

from config import config
from models.grading_response_model import GradeResponse, normalize_raw_response, validate_against_rubric
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
    GPT5_MINI = "gpt-5-mini"


class GradingType:
    """채점 유형을 위한 열거형 클래스"""
    DESCRIPTIVE = "descriptive"  # 서술형
    MAP = "map"  # 백지도형


class LLMService:
    """
    LLM 기반 자동 채점을 위한 서비스
    
    구조화된 프롬프트 생성 및 응답 파싱과 함께 
    Google Gemini 및 OpenAI GPT-5-mini API를 지원합니다.
    """
    
    def __init__(self):
        """Initialize LLM service with API clients and performance optimization."""
        self.gemini_client = None
        self.openai_client = None
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
                self.gemini_client = genai.Client(api_key=config.GOOGLE_API_KEY)
                logger.info("Google Gemini client initialized successfully")
            else:
                logger.warning("Google API key not found")
            
            # Initialize OpenAI
            if config.OPENAI_API_KEY:
                try:
                    self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
                    logger.info("OpenAI client initialized successfully")
                except Exception as openai_error:
                    logger.error(f"Failed to initialize OpenAI client: {openai_error}")
                    self.openai_client = None
            else:
                logger.warning("OpenAI API key not found")
                
        except Exception as e:
            logger.error(f"Failed to initialize LLM clients: {e}")
            # Log initialization status
            if self.gemini_client is None:
                logger.info("Gemini client not initialized due to missing API key or initialization error")
            if self.openai_client is None:
                logger.info("OpenAI client not initialized due to error")
    
    def select_model(self, model_type: str, grading_type: str) -> str:
        """
        Select appropriate model based on grading type and user preference.
        
        Args:
            model_type: Preferred model type
            grading_type: Type of grading (descriptive/map)
            
        Returns:
            Selected model identifier
            
        Raises:
            ValueError: If invalid combination is requested
        """
        if model_type == LLMModelType.GEMINI and config.GOOGLE_API_KEY:
            return LLMModelType.GEMINI

        if model_type == LLMModelType.GPT5_MINI and self.openai_client:
            return LLMModelType.GPT5_MINI

        if config.GOOGLE_API_KEY:
            return LLMModelType.GEMINI

        if self.openai_client:
            return LLMModelType.GPT5_MINI

        raise ValueError("No supported LLM models available. Configure GOOGLE_API_KEY or OPENAI_API_KEY.")
    
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
            prompt_parts.append("""① 시스템 역할(System role): 당신은 지리 교과 이미지 서답형 문항 전문 채점자입니다. 

② 참고 자료(모범 답안): 첫 번째로 전달되는 이미지는 문제의 모범 답안입니다. 
이 모범 답안을 참고하여 학생 답안의 정확성을 평가하세요.

③ 학생 답안(Student answer): 두 번째로 전달되는 이미지는 학생이 작성한 백지도 답안입니다. 
모범 답안과 비교하여 도형, 선, 화살표, 위치 표시 등의 정확성을 평가하세요.""")
        else:
            prompt_parts.append("① 시스템 역할(System role): 당신은 지리 교과 텍스트 서답형 문항 전문 채점자입니다. 전달하는 학생의 텍스트 답안을 아래 지시사항과 자료를 토대로 분석하여 채점해주세요.")
        
        # 2. Reference materials (descriptive only)
        if grading_type == GradingType.DESCRIPTIVE and references:
            prompt_parts.append("\n③ 참고 자료(Reference materials): 다음은 채점 참고 자료입니다:")
            for i, ref in enumerate(references, 1):
                # 청크 전체를 사용 (이미 500토큰으로 적절히 생성되어 있음)
                clean_ref = ref.strip()
                if clean_ref:
                    prompt_parts.append(f"\n참고자료 {i}:\n{clean_ref}")
        
        # 3. Evaluation rubric
        prompt_parts.append("\n④ 평가 루브릭(Evaluation rubric): 다음은 평가 루브릭입니다:")
        for element in rubric.elements:
            prompt_parts.append(f"\n평가요소: {element.name} (최대 {element.max_score}점)")
            for criteria in element.criteria:
                prompt_parts.append(f"  {criteria.score}점: {criteria.description}")
        
        # 4. Student answer
        if grading_type == GradingType.MAP:
            prompt_parts.append("\n② 학생 답안(Student answer): 다음은 학생이 작성한 백지도 답안입니다. 해당 이미지를 분석하여 1. 답안에 표기된 백지도가 어느 지역인지 파악하고 2. 제시된 평가 루브릭에 따라 학생이 백지도 위에 작성한 도형, 선, 화살표 등을 상세히 분석하고 3. 평가 기준 점수에 따라 학생 답안에 대한 점수를 부여하세요.")
        else:
            prompt_parts.append(f"\n② 학생 답안(Student answer): 다음은 학생 답안입니다:\n{student_answer}")
        
        # 5. Output format specification
        prompt_parts.append(f"""
⑤ 출력 포맷(Output format): 다음 JSON 형식으로 채점 결과를 제공해주세요:
{{
  "elements": [
    {{"element_name": "평가요소명", "score": 점수, "reasoning": "점수 부여 근거"}}
  ],
  "feedback": "평가 루브릭에 따른 전반적인 피드백과 학생 응답의 개선점 제시"
}}

⑥ 주의사항(Cautions): 반드시 위의 JSON 형식을 정확히 따라주세요. 모든 평가요소를 elements 배열에 한 번씩 포함하고, element_name은 루브릭의 평가요소명과 정확히 일치해야 합니다. 각 평가요소에 대해 루브릭에 명시된 점수만 부여하세요. total_score는 출력하지 마세요.
""")
        
        final_prompt = "\n".join(prompt_parts)
        
        # 🔍 프롬프트 전체 로깅 (디버깅용)
        logger.info("="*80)
        logger.info("생성된 프롬프트 전체 내용:")
        logger.info("="*80)
        logger.info(final_prompt)
        logger.info("="*80)
        
        return final_prompt
    
    def _cleanup_cache(self):
        """Clean up internal caches to free memory."""
        self.response_cache.clear()
        logger.info("LLM service cache cleaned up")
    
    def _get_image_mime_type(self, image_path: str) -> str:
        file_ext = Path(image_path).suffix.lower()
        return {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
        }.get(file_ext, 'image/jpeg')

    def _encode_image_part(self, image_path: str) -> types.Part:
        """
        이미지 파일을 Google GenAI SDK용 Part로 인코딩합니다.
        
        Args:
            image_path: 인코딩할 이미지 파일 경로
            
        Returns:
            types.Part containing mime_type and bytes data
            
        Raises:
            Exception: If image file cannot be read
        """
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()

            return types.Part.from_bytes(
                data=image_data,
                mime_type=self._get_image_mime_type(image_path),
            )
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            raise Exception(f"이미지 파일을 읽을 수 없습니다: {image_path}")
    
    def _generate_cache_key(self, prompt: str, image_path: Optional[str] = None) -> str:
        """Generate cache key for API responses (backward compatibility)."""
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
    
    def _generate_cache_key_v2(
        self, 
        prompt: str, 
        reference_image_path: Optional[str] = None, 
        student_image_path: Optional[str] = None
    ) -> str:
        """
        두 이미지(모범 답안 + 학생 답안)를 포함한 캐시 키 생성.
        
        Args:
            prompt: 프롬프트 텍스트
            reference_image_path: 모범 답안 이미지 경로
            student_image_path: 학생 답안 이미지 경로
            
        Returns:
            MD5 해시 기반 캐시 키
        """
        key_data = prompt
        
        # 모범 답안 이미지 해시 추가
        if reference_image_path:
            try:
                with open(reference_image_path, 'rb') as f:
                    ref_hash = hashlib.md5(f.read()).hexdigest()[:8]
                key_data += f"_ref_{ref_hash}"
            except Exception:
                key_data += f"_ref_{reference_image_path}"
        
        # 학생 답안 이미지 해시 추가
        if student_image_path:
            try:
                with open(student_image_path, 'rb') as f:
                    stu_hash = hashlib.md5(f.read()).hexdigest()[:8]
                key_data += f"_stu_{stu_hash}"
            except Exception:
                key_data += f"_stu_{student_image_path}"
        
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
        reference_image_path: Optional[str] = None,  # 새로 추가: 모범 답안
        student_image_path: Optional[str] = None,     # 새로 추가: 학생 답안
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Call Google Gemini API for text/image analysis with caching and optimization.
        
        Args:
            prompt: Text prompt for the model
            image_path: Optional path to image file (backward compatibility)
            reference_image_path: Optional path to reference (model answer) image
            student_image_path: Optional path to student answer image
            max_retries: Maximum number of retry attempts
            
        Returns:
            API response as dictionary
            
        Raises:
            Exception: If API call fails after retries
        """
        if not self.gemini_client:
            error_info = handle_error(
                ValueError("Gemini client not initialized"),
                ErrorType.AUTHENTICATION,
                context="call_gemini_api: client not initialized",
                user_context="Google Gemini API 호출"
            )
            raise ValueError(error_info.user_message)
        
        # Backward compatibility: image_path를 student_image_path로 사용
        if image_path and not student_image_path:
            student_image_path = image_path
        
        # Check cache first (v2 cache key for multiple images)
        cache_key = self._generate_cache_key_v2(prompt, reference_image_path, student_image_path)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            logger.debug("Using cached Gemini API response")
            return cached_response
        
        def _make_api_call():
            # Prepare content for API call following official documentation
            # Reference: https://ai.google.dev/gemini-api/docs/vision
            
            contents = [prompt]  # 프롬프트를 먼저 추가
            
            # 모범 답안 이미지 추가 (있는 경우)
            if reference_image_path and Path(reference_image_path).exists():
                print(f"DEBUG: Adding reference image to Gemini API request: {reference_image_path}")
                try:
                    reference_part = self._encode_image_part(reference_image_path)
                    contents.append(reference_part)
                    print(f"DEBUG: Successfully added reference image")
                except Exception as e:
                    print(f"DEBUG: Failed to read reference image: {e}")
                    error_info = handle_error(
                        e,
                        ErrorType.FILE_PROCESSING,
                        context=f"call_gemini_api: failed to read reference image {reference_image_path}",
                        user_context="모범 답안 이미지 파일 읽기"
                    )
                    raise ValueError(error_info.user_message)
            
            # 학생 답안 이미지 추가 (있는 경우)
            if student_image_path and Path(student_image_path).exists():
                print(f"DEBUG: Adding student image to Gemini API request: {student_image_path}")
                try:
                    student_part = self._encode_image_part(student_image_path)
                    contents.append(student_part)
                    print(f"DEBUG: Successfully added student image")
                except Exception as e:
                    print(f"DEBUG: Failed to read student image: {e}")
                    error_info = handle_error(
                        e,
                        ErrorType.FILE_PROCESSING,
                        context=f"call_gemini_api: failed to read student image {student_image_path}",
                        user_context="학생 답안 이미지 파일 읽기"
                    )
                    raise ValueError(error_info.user_message)
            
            if len(contents) == 1:  # 이미지가 없는 경우
                print(f"DEBUG: No images provided or image files not found")
                if reference_image_path:
                    print(f"DEBUG: reference_image_path: {reference_image_path}, exists: {Path(reference_image_path).exists()}")
                if student_image_path:
                    print(f"DEBUG: student_image_path: {student_image_path}, exists: {Path(student_image_path).exists()}")
            
            # Generate response
            try:
                response = self.gemini_client.models.generate_content(
                    model=config.GEMINI_MODEL,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json",
                        response_schema=GradeResponse,
                    ),
                )
                
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
    
    def call_gpt5_mini_api(
        self,
        prompt: str,
        reference_image_path: Optional[str] = None,
        student_image_path: Optional[str] = None,
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Call OpenAI GPT-5-mini API for grading.
        
        Args:
            prompt: Grading prompt
            reference_image_path: Path to reference answer image (optional)
            student_image_path: Path to student answer image (optional)
            max_retries: Maximum number of retries
            
        Returns:
            Dict with 'text' key containing the response
        """
        if not self.openai_client:
            error_info = handle_error(
                ValueError("OpenAI client not initialized"),
                ErrorType.AUTHENTICATION,
                context="call_gpt5_mini_api: client not initialized",
                user_context="OpenAI API 클라이언트 초기화"
            )
            raise Exception(error_info.user_message)

        cache_key = self._generate_cache_key_v2(prompt, reference_image_path, student_image_path)
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            logger.debug("Using cached OpenAI API response")
            return cached_response
        
        def _make_api_call():
            try:
                # Build input content array
                input_content = []
                
                # Add text prompt
                input_content.append({
                    "type": "input_text",
                    "text": prompt
                })
                
                # Add reference image if provided
                if reference_image_path:
                    try:
                        reference_base64 = self._encode_image(reference_image_path)
                        input_content.append({
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{reference_base64}"
                        })
                    except Exception as e:
                        error_info = handle_error(
                            e,
                            ErrorType.FILE_PROCESSING,
                            context="call_gpt5_mini_api: reference image encoding failed",
                            user_context="모범 답안 이미지 인코딩"
                        )
                        raise Exception(error_info.user_message)
                
                # Add student image if provided
                if student_image_path:
                    try:
                        student_base64 = self._encode_image(student_image_path)
                        input_content.append({
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{student_base64}"
                        })
                    except Exception as e:
                        error_info = handle_error(
                            e,
                            ErrorType.FILE_PROCESSING,
                            context="call_gpt5_mini_api: student image encoding failed",
                            user_context="학생 답안 이미지 인코딩"
                        )
                        raise Exception(error_info.user_message)
                
                # Call OpenAI API
                response = self.openai_client.responses.create(
                    model="gpt-5-mini",
                    input=[{
                        "role": "user",
                        "content": input_content
                    }],
                    reasoning={"effort": "medium"},
                    text={
                        "format": {"type": "json_object"},
                        "verbosity": "low"
                    }
                )
                
                result = {"text": response.output_text}
                self._cache_response(cache_key, result)
                self.api_call_count += 1
                return result
                
            except Exception as e:
                # Handle specific OpenAI errors
                error_message = str(e)
                
                if "quota" in error_message.lower() or "insufficient_quota" in error_message.lower():
                    error_info = handle_error(
                        e,
                        ErrorType.RATE_LIMIT,
                        context="call_gpt5_mini_api: quota exceeded",
                        user_context="OpenAI API 할당량 초과"
                    )
                    raise Exception(error_info.user_message)
                
                elif "timeout" in error_message.lower():
                    error_info = handle_error(
                        e,
                        ErrorType.NETWORK,
                        context="call_gpt5_mini_api: timeout",
                        user_context="OpenAI API 시간 초과"
                    )
                    raise Exception(error_info.user_message)
                
                elif "authentication" in error_message.lower() or "unauthorized" in error_message.lower():
                    error_info = handle_error(
                        e,
                        ErrorType.AUTHENTICATION,
                        context="call_gpt5_mini_api: authentication failed",
                        user_context="OpenAI API 인증"
                    )
                    raise Exception(error_info.user_message)
                
                else:
                    error_info = handle_error(
                        e,
                        ErrorType.API_COMMUNICATION,
                        context="call_gpt5_mini_api: general API error",
                        user_context="OpenAI API 호출"
                    )
                    raise Exception(error_info.user_message)
        
        # Use retry mechanism with exponential backoff
        max_retries = max_retries or config.MAX_RETRIES
        return retry_with_backoff(
            _make_api_call,
            ErrorType.API_COMMUNICATION,
            max_retries=max_retries,
            context="call_gpt5_mini_api"
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
            
            parsed = self._extract_json_object(response_text)

            if parsed is None:
                error_info = handle_error(
                    ValueError("No JSON found in response"),
                    ErrorType.PARSING,
                    context=f"parse_response: no JSON in response text (length: {len(response_text)})",
                    user_context="AI 응답 파싱"
                )
                raise ValueError(error_info.user_message)
            
            structured = normalize_raw_response(parsed)
            return validate_against_rubric(structured, rubric)
            
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

    def _extract_json_object(self, response_text: str) -> Optional[Dict[str, Any]]:
        """응답 텍스트에서 첫 번째 유효 JSON 객체를 엄격하게 추출합니다."""
        if not response_text:
            return None

        text = response_text.strip()
        decoder = json.JSONDecoder()

        candidates = [0]
        candidates.extend(i for i, char in enumerate(text) if char == "{")

        seen = set()
        for start in candidates:
            if start in seen:
                continue
            seen.add(start)
            try:
                parsed, _ = decoder.raw_decode(text[start:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

        return None
    
    def grade_student_sequential(
        self,
        student: Student,
        rubric: Rubric,
        model_type: str,
        grading_type: str,
        references: Optional[List[str]] = None,
        reference_image_path: Optional[str] = None
    ) -> GradingResult:
        """
        Grade a single student's answer sequentially.
        
        Args:
            student: Student data with answer
            rubric: Evaluation rubric
            model_type: LLM model to use
            grading_type: Type of grading (descriptive/map)
            references: Reference materials from RAG
            
        Returns:
            Grading result with timing information
        """
        timer = GradingTimer()
        timer.start()
        original_answer = student.answer if grading_type == GradingType.DESCRIPTIVE else (student.image_path or "")
        
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
                print(f"DEBUG: Reference image_path: {reference_image_path}")
                print(f"DEBUG: Image path to use: {image_path_to_use}")
                if image_path_to_use:
                    print(f"DEBUG: Student image file exists: {Path(image_path_to_use).exists()}")
                    if Path(image_path_to_use).exists():
                        print(f"DEBUG: Student image file size: {Path(image_path_to_use).stat().st_size} bytes")
                if reference_image_path:
                    print(f"DEBUG: Reference image file exists: {Path(reference_image_path).exists()}")
                    if Path(reference_image_path).exists():
                        print(f"DEBUG: Reference image file size: {Path(reference_image_path).stat().st_size} bytes")
                
                response = self.call_gemini_api(
                    prompt=prompt,
                    reference_image_path=reference_image_path,
                    student_image_path=image_path_to_use
                )
            elif selected_model == LLMModelType.GPT5_MINI:
                image_path_to_use = student.image_path if grading_type == GradingType.MAP else None
                print(f"DEBUG: Using GPT-5-mini API for student {student.name}")
                print(f"DEBUG: Grading type: {grading_type}")
                print(f"DEBUG: Student image_path: {student.image_path}")
                print(f"DEBUG: Reference image_path: {reference_image_path}")
                print(f"DEBUG: Image path to use: {image_path_to_use}")
                
                response = self.call_gpt5_mini_api(
                    prompt=prompt,
                    reference_image_path=reference_image_path,
                    student_image_path=image_path_to_use
                )
            else:
                raise ValueError(f"Unsupported selected model: {selected_model}")
            
            # Parse response
            parsed_result = self.parse_response(response["text"], rubric)
            
            # Stop timer and get elapsed time
            elapsed_time = timer.stop()
            
            # Create grading result
            result = GradingResult(
                student_name=student.name,
                student_class_number=student.class_number,
                original_answer=original_answer,
                grading_time_seconds=elapsed_time,
                overall_feedback=parsed_result["feedback"],
                status="success",
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
                original_answer=original_answer,
                grading_time_seconds=elapsed_time,
                overall_feedback=f"채점 중 오류가 발생했습니다: {str(e)}",
                status="failed",
                error_message=str(e),
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
                    references=references
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
            "gemini": self.gemini_client is not None,
            "gpt-5-mini": self.openai_client is not None
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
