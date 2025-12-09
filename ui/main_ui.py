"""
지리 자동 채점 플랫폼의 메인 UI 컴포넌트
채점 유형 선택, 모델 선택, 파일 업로드를 처리합니다.
"""

import streamlit as st
from typing import Optional, List, Dict, Any
from enum import Enum
import os
import tempfile
import shutil


def display_file_upload_error(error_info, filename: str = ""):
    """파일 업로드 오류 표시 함수 (error_display_ui 대체)"""
    if hasattr(error_info, 'user_message'):
        message = error_info.user_message
    else:
        message = str(error_info)
    
    if filename:
        st.error(f"📁 파일 '{filename}' 처리 오류: {message}")
    else:
        st.error(f"📁 파일 처리 오류: {message}")


def display_error(error_info, show_details: bool = False):
    """기본적인 오류 표시 함수 (error_display_ui 대체)"""
    if hasattr(error_info, 'error_type'):
        error_type = error_info.error_type.value
    else:
        error_type = "시스템 오류"
    
    if hasattr(error_info, 'user_message'):
        message = error_info.user_message
    else:
        message = str(error_info)
    
    st.error(f"⚠️ {error_type}: {message}")
    
    if show_details and hasattr(error_info, 'technical_details'):
        with st.expander("기술적 세부사항"):
            st.code(error_info.technical_details)


class GradingType(Enum):
    """채점 유형 열거형"""
    DESCRIPTIVE = "descriptive"
    MAP = "map"


class LLMModel(Enum):
    """사용 가능한 LLM 모델 열거형"""
    GEMINI = "gemini"
    GROQ = "groq"


class MainUI:
    """지리 자동 채점 플랫폼의 메인 UI 컨트롤러"""
    
    def __init__(self):
        """메인 UI 컨트롤러 초기화"""
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Streamlit 세션 상태 변수들을 초기화합니다."""
        if 'grading_type' not in st.session_state:
            st.session_state.grading_type = None
        
        if 'selected_model' not in st.session_state:
            st.session_state.selected_model = None
        
        if 'uploaded_files' not in st.session_state:
            st.session_state.uploaded_files = {}
        
        if 'rubric_data' not in st.session_state:
            st.session_state.rubric_data = None
        
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "main"
        
        if 'processed_students' not in st.session_state:
            st.session_state.processed_students = None
        
        if 'rag_references' not in st.session_state:
            st.session_state.rag_references = None
        
        # 처리하지 않고 업로드된 참고 파일들 저장
        if 'uploaded_reference_files' not in st.session_state:
            st.session_state.uploaded_reference_files = None
        
        # 모범 답안 이미지 경로 초기화 추가
        if 'reference_image_path' not in st.session_state:
            st.session_state.reference_image_path = None
        
        # 백지도형 채점을 위한 모범 답안 이미지 경로
        if 'reference_image_path' not in st.session_state:
            st.session_state.reference_image_path = None
    
    def render_main_page(self):
        """
        모든 UI 컴포넌트가 포함된 메인 페이지를 렌더링합니다.
        """
        # 페이지 헤더
        st.markdown("## 🎯 채점 시스템 설정")
        st.markdown("---")
        
        # 채점 유형 선택
        self.render_grading_type_selection()
        
        # Show additional options based on selected grading type
        if st.session_state.grading_type:
            st.markdown("---")
            
            # Model selection - show for both descriptive and map types
            self.render_model_selection_section()
            
            # File upload section
            self.render_file_upload_section()
            
            # Navigation buttons
            self.render_navigation_buttons()
    
    def render_grading_type_selection(self):
        """
        Render the grading type selection interface.
        Implements Requirements 1.1, 1.2, 1.3
        """
        st.markdown("### 📝 채점 유형 선택")
        st.markdown("채점하고자 하는 문항의 유형을 선택해주세요.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(
                "📝 텍스트 문항",
                key="descriptive_button",
                help="텍스트 기반 답안을 채점합니다. 참고 자료를 활용한 RAG 기반 채점이 가능합니다.",
                use_container_width=True
            ):
                self.handle_grading_type_selection(GradingType.DESCRIPTIVE)
        
        with col2:
            if st.button(
                "🗺️ 백지도형 문항",
                key="map_button", 
                help="이미지 기반 백지도 답안을 채점합니다. Google Gemini 또는 OpenAI GPT-5-mini의 이미지 분석 기능을 사용합니다.",
                use_container_width=True
            ):
                self.handle_grading_type_selection(GradingType.MAP)
        
        # Display current selection
        if st.session_state.grading_type:
            grading_type_name = "📝 텍스트 문항" if st.session_state.grading_type == GradingType.DESCRIPTIVE.value else "🗺️ 백지도형 문항"
            st.success(f"✅ 선택된 채점 유형: **{grading_type_name}**")
    
    def handle_grading_type_selection(self, grading_type: GradingType):
        """
        Handle grading type selection and reset related state.
        Implements Requirement 1.3 - reset previous data when type changes
        """
        # Reset session state when grading type changes
        if st.session_state.grading_type != grading_type.value:
            st.session_state.grading_type = grading_type.value
            st.session_state.selected_model = None
            st.session_state.uploaded_files = {}
            st.session_state.rubric_data = None
            st.rerun()
    
    def render_model_selection_section(self):
        """
        Render LLM model selection section with detailed options.
        Implements Requirement 5.1
        """
        st.markdown("### 🧠 LLM 모델 선택")
        
        # Display different messages based on grading type
        if st.session_state.grading_type == GradingType.MAP.value:
            st.markdown("백지도형 문항 채점에 사용할 AI 모델을 선택해주세요.")
        else:
            st.markdown("텍스트 문항 채점에 사용할 AI 모델을 선택해주세요.")
        
        # Filter models based on grading type
        if st.session_state.grading_type == GradingType.MAP.value:
            # For MAP type, show only multimodal models (Gemini and GPT-5-mini)
            model_options = {
                LLMModel.GEMINI.value: {
                    "name": "Google Gemini 2.5 Flash",
                    "description": "Google의 최신 멀티모달 AI 모델. 텍스트와 이미지 문항 모두 분석 가능합니다.",
                    "icon": "🔥"
                },
                "gpt-5-mini": {
                    "name": "OpenAI GPT-5 Mini",
                    "description": "OpenAI의 최신 추론 모델. 텍스트와 이미지 문항 모두 분석 가능합니다.",
                    "icon": "⚡"
                }
            }
        else:
            # For DESCRIPTIVE type, show all models
            model_options = {
                LLMModel.GEMINI.value: {
                    "name": "Google Gemini 2.5 Flash",
                    "description": "Google의 최신 멀티모달 AI 모델. 텍스트와 이미지 문항 모두 분석 가능합니다.",
                    "icon": "🔥"
                },
                # LLMModel.GROQ.value: {
                #     "name": "Groq",
                #     "description": "빠른 추론 속도를 제공하는 텍스트 전용 AI 모델입니다.",
                #     "icon": "⚡"
                # },
                "gpt-5-mini": {
                    "name": "OpenAI GPT-5 Mini",
                    "description": "OpenAI의 최신 추론 모델. 텍스트와 이미지 문항 모두 분석 가능합니다.",
                    "icon": "⚡"
                }
            }
        
        selected_model = st.radio(
            "모델 선택:",
            options=list(model_options.keys()),
            format_func=lambda x: f"{model_options[x]['icon']} {model_options[x]['name']}",
            key="model_selection",
            help="각 모델의 특성을 고려하여 선택해주세요."
        )
        
        if selected_model:
            st.session_state.selected_model = selected_model
            
            # Display model description
            st.info(f"ℹ️ {model_options[selected_model]['description']}")
            
            # If Groq is selected, show model options
            if selected_model == LLMModel.GROQ.value:
                st.markdown("#### 🧠 Groq 모델 상세 선택")
                groq_model_options = {
                    "qwen/qwen3-32b": "Qwen3 32B",
                    "openai/gpt-oss-120b": "GPT-OSS 120B"
                }
                
                selected_groq_model = st.selectbox(
                    "Groq 모델 선택:",
                    options=list(groq_model_options.keys()),
                    format_func=lambda x: groq_model_options[x],
                    key="groq_model_selection",
                    help="Groq 플랫폼에서 사용할 구체적인 모델을 선택해주세요."
                )
                
                st.session_state.selected_groq_model = selected_groq_model
                
                # 선택 확인 표시
                st.success(f"✅ 선택된 Groq 모델: **{groq_model_options[selected_groq_model]}**")
                
                # API 호출에 사용될 모델명 표시
                with st.expander("🔧 기술 정보"):
                    st.code(f"API 호출 모델명: {selected_groq_model}")
                    st.info("이 모델명이 실제 Groq API 호출에 사용됩니다.")
    
    def render_file_upload_section(self):
        """
        Render file upload section based on grading type.
        Implements Requirements 4.1, 4.2, 4.3
        """
        st.markdown("### 📁 파일 업로드")
        
        if st.session_state.grading_type == GradingType.DESCRIPTIVE.value:
            self.render_descriptive_file_upload()
        elif st.session_state.grading_type == GradingType.MAP.value:
            self.render_map_file_upload()
    
    def render_descriptive_file_upload(self):
        """
        Render file upload section for descriptive grading.
        """
        st.markdown("#### 📚 참고 자료 (선택사항)")
        st.markdown("채점 기준으로 사용할 참고 자료를 업로드해주세요. RAG 기반 채점에 활용됩니다.")
        
        reference_files = st.file_uploader(
            "참고 자료 업로드",
            type=['pdf', 'docx'],
            accept_multiple_files=True,
            key="reference_files",
            help="PDF 또는 DOCX 형식의 파일을 업로드할 수 있습니다."
        )
        
        if reference_files:
            # Store uploaded reference files without processing
            st.session_state.uploaded_reference_files = reference_files
            st.success(f"✅ {len(reference_files)}개의 참고 자료가 업로드되었습니다.")
            
            # Display uploaded files
            with st.expander("📋 업로드된 참고 자료 목록"):
                for i, file in enumerate(reference_files, 1):
                    st.write(f"{i}. {file.name} ({file.size:,} bytes) - {file.type}")
        
        st.markdown("#### 📝 학생 답안 데이터")
        st.markdown("학생 이름, 반, 답안이 포함된 Excel 파일을 업로드해주세요.")
        
        # Show required format
        with st.expander("📋 필수 Excel 파일 형식"):
            st.markdown("""
            **필수 열 구성:**
            - `학생 이름`: 학생의 이름
            - `반`: 학생의 반 정보
            - `답안`: 학생이 작성한 답안
            
            **예시:**
            | 학생 이름 | 반 | 답안 |
            |----------|----|----|
            | 김철수 | 1반 | 지구온난화는... |
            | 이영희 | 2반 | 기후변화로 인해... |
            """)
        
        student_data_file = st.file_uploader(
            "학생 답안 Excel 파일",
            type=['xlsx', 'xls'],
            key="student_data_descriptive",
            help="학생 이름, 반, 답안 열이 포함된 Excel 파일을 업로드해주세요."
        )
        
        if student_data_file:
            st.session_state.uploaded_files['student_data'] = student_data_file
            st.success(f"✅ 학생 답안 파일이 업로드되었습니다: {student_data_file.name}")
    
    def render_map_file_upload(self):
        """
        Render file upload section for map grading.
        """
        # 모범 답안 업로드 섹션 추가
        st.markdown("#### 📚 모범 답안 이미지")
        st.markdown("*채점 기준이 될 모범 답안 이미지를 업로드하세요. 모든 학생 채점 시 동일하게 사용됩니다.*")
        
        reference_image_file = st.file_uploader(
            "모범 답안 이미지:",
            type=['jpg', 'jpeg', 'png', 'bmp'],
            key="reference_image_uploader",
            help="모든 학생 채점 시 비교 기준으로 사용될 모범 답안 이미지"
        )
        
        if reference_image_file:
            # 임시 파일로 저장
            reference_path = self._save_uploaded_file(reference_image_file, "reference")
            st.session_state.reference_image_path = reference_path
            st.success("✅ 모범 답안 이미지가 업로드되었습니다!")
            
            # 미리보기 표시
            st.image(reference_image_file, caption="업로드된 모범 답안", width=400)
        else:
            st.warning("⚠️ 백지도형 채점을 위해 모범 답안 이미지를 업로드해주세요.")
        
        st.markdown("---")
        
        st.markdown("#### 📊 학생 정보 데이터")
        st.markdown("학생 이름과 반 정보가 포함된 Excel 파일을 업로드해주세요.")
        
        # Show required format for map grading
        with st.expander("📋 필수 Excel 파일 형식"):
            st.markdown("""
            **필수 열 구성:**
            - `학생 이름`: 학생의 이름 (이미지 파일명과 매칭됩니다)
            - `반`: 학생의 반 정보
            
            **예시:**
            | 학생 이름 | 반 |
            |----------|----| 
            | 김철수 | 1반 |
            | 이영희 | 2반 |
            
            **이미지 파일명 규칙:**
            - 파일명에 학생 이름이 포함되어야 합니다
            - 예: `김철수_백지도.jpg`, `이영희.png`
            """)
        
        student_info_file = st.file_uploader(
            "학생 정보 Excel 파일",
            type=['xlsx', 'xls'],
            key="student_info_map",
            help="학생 이름과 반 정보가 포함된 Excel 파일을 업로드해주세요."
        )
        
        if student_info_file:
            st.session_state.uploaded_files['student_info'] = student_info_file
            st.success(f"✅ 학생 정보 파일이 업로드되었습니다: {student_info_file.name}")
        
        st.markdown("#### 🖼️ 학생 답안 이미지")
        st.markdown("학생들이 작성한 백지도 이미지 파일들을 업로드해주세요.")
        
        image_files = st.file_uploader(
            "백지도 이미지 파일들",
            type=['jpg', 'jpeg', 'png', 'bmp'],
            accept_multiple_files=True,
            key="image_files",
            help="JPG, PNG 등의 이미지 파일을 업로드할 수 있습니다. 파일명에 학생 이름이 포함되어야 합니다."
        )
        
        if image_files:
            st.session_state.uploaded_files['image_files'] = image_files
            st.success(f"✅ {len(image_files)}개의 이미지 파일이 업로드되었습니다.")
            
            # Display uploaded images
            with st.expander("🖼️ 업로드된 이미지 파일 목록"):
                for i, file in enumerate(image_files, 1):
                    st.write(f"{i}. {file.name} ({file.size:,} bytes) - {file.type}")
    
    def render_navigation_buttons(self):
        """
        Render navigation buttons for proceeding to next steps.
        """
        st.markdown("---")
        st.markdown("### 🚀 다음 단계")
        
        # Check if required files are uploaded
        can_proceed = self.check_required_files()
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Performance dashboard button removed as part of system monitoring cleanup
            pass
        
        with col2:
            if can_proceed:
                if st.button(
                    "📋 루브릭 설정하기",
                    key="proceed_to_rubric",
                    use_container_width=True,
                    type="primary"
                ):
                    # Process files before proceeding
                    self.process_uploaded_files()
                    st.session_state.current_page = "rubric"
                    st.rerun()
            else:
                st.button(
                    "📋 루브릭 설정하기",
                    key="proceed_to_rubric_disabled",
                    use_container_width=True,
                    disabled=True,
                    help="필수 파일을 모두 업로드한 후 진행할 수 있습니다."
                )
        
        # Show requirements status
        self.show_requirements_status()
    
    def check_required_files(self) -> bool:
        """
        Check if all required files are uploaded based on grading type.
        
        Returns:
            bool: True if all required files are uploaded
        """
        if not st.session_state.grading_type:
            return False
        
        if st.session_state.grading_type == GradingType.DESCRIPTIVE.value:
            # For descriptive: student data is required, reference files are optional
            return 'student_data' in st.session_state.uploaded_files
        
        elif st.session_state.grading_type == GradingType.MAP.value:
            # For map: student info, image files, AND reference image are all required
            has_student_info = 'student_info' in st.session_state.uploaded_files
            has_image_files = 'image_files' in st.session_state.uploaded_files
            has_reference_image = st.session_state.get('reference_image_path') is not None
            
            return has_student_info and has_image_files and has_reference_image
        
        return False
    
    def show_requirements_status(self):
        """
        Show the current status of requirements.
        """
        st.markdown("#### ✅ 설정 완료 상태")
        
        # Grading type status
        if st.session_state.grading_type:
            grading_type_name = "📝 텍스트" if st.session_state.grading_type == GradingType.DESCRIPTIVE.value else "🗺️ 백지도형"
            st.success(f"✅ 채점 유형: {grading_type_name}")
        else:
            st.error("❌ 채점 유형을 선택해주세요")
        
        # Model selection status
        if st.session_state.selected_model:
            # Map model value to display name
            if st.session_state.selected_model == LLMModel.GEMINI.value:
                model_name = "Google Gemini 2.5 Flash"
            elif st.session_state.selected_model == LLMModel.GROQ.value:
                # Show specific Groq model name
                groq_model = st.session_state.get('selected_groq_model', 'qwen/qwen3-32b')
                model_name = f"Groq ({groq_model})"
            elif st.session_state.selected_model == "gpt-5-mini":
                model_name = "OpenAI GPT-5 Mini"
            else:
                model_name = st.session_state.selected_model
            
            st.success(f"✅ LLM 모델: {model_name}")
        else:
            st.error("❌ LLM 모델을 선택해주세요")
        
        # File upload status
        if st.session_state.grading_type == GradingType.DESCRIPTIVE.value:
            if 'student_data' in st.session_state.uploaded_files:
                st.success("✅ 학생 답안 파일 업로드 완료")
            else:
                st.error("❌ 학생 답안 Excel 파일을 업로드해주세요")
            
            if st.session_state.uploaded_reference_files:
                st.success(f"✅ 참고 자료 {len(st.session_state.uploaded_reference_files)}개 업로드 완료")
            else:
                st.info("ℹ️ 참고 자료는 선택사항입니다")
        
        elif st.session_state.grading_type == GradingType.MAP.value:
            # 모범 답안 이미지 상태 추가
            if st.session_state.get('reference_image_path'):
                st.success("✅ 모범 답안 이미지 업로드 완료")
            else:
                st.error("❌ 모범 답안 이미지를 업로드해주세요")
            
            if 'student_info' in st.session_state.uploaded_files:
                st.success("✅ 학생 정보 파일 업로드 완료")
            else:
                st.error("❌ 학생 정보 Excel 파일을 업로드해주세요")
            
            if 'image_files' in st.session_state.uploaded_files:
                st.success(f"✅ 이미지 파일 {len(st.session_state.uploaded_files['image_files'])}개 업로드 완료")
            else:
                st.error("❌ 학생 답안 이미지 파일들을 업로드해주세요")


    def process_uploaded_files(self):
        """업로드된 파일을 처리하고 채점을 위한 데이터를 준비합니다."""
        try:
            from services.file_service import FileService
            from utils.error_handler import handle_error, ErrorType
            # 삭제된 error_display_ui 대신 기본 Streamlit 오류 표시 사용
            
            file_service = FileService()
            
            # 채점 유형에 따라 학생 데이터 처리
            if st.session_state.grading_type == GradingType.DESCRIPTIVE.value:
                # 텍스트 채점 파일 처리
                student_file = st.session_state.uploaded_files.get('student_data')
                if student_file:
                    # 업로드된 파일을 임시로 저장
                    import tempfile
                    import os
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                        tmp_file.write(student_file.read())
                        tmp_file_path = tmp_file.name
                    
                    try:
                        result = file_service.process_student_data(
                            excel_file_path=tmp_file_path,
                            grading_type="descriptive"
                        )
                        
                        if result['success']:
                            st.session_state.processed_students = result['students']
                            st.success(f"✅ {len(result['students'])}명의 학생 데이터를 성공적으로 처리했습니다.")
                        else:
                            if 'error_info' in result:
                                display_file_upload_error(result['error_info'], student_file.name)
                            else:
                                st.error(f"❌ {result['message']}")
                            return
                    
                    finally:
                        # Clean up temporary file
                        if os.path.exists(tmp_file_path):
                            os.unlink(tmp_file_path)
                
                # Store reference files without immediate RAG processing
                reference_files = st.session_state.uploaded_files.get('reference_files')
                if reference_files:
                    st.session_state.uploaded_reference_files = reference_files
                    st.info(f"ℹ️ {len(reference_files)}개의 참고 자료가 저장되었습니다. 채점 시작 시 처리됩니다.")
            
            elif st.session_state.grading_type == GradingType.MAP.value:
                # Process map grading files
                
                # 모범 답안 체크 추가
                if not st.session_state.get('reference_image_path'):
                    st.error("❌ 백지도형 채점에는 모범 답안 이미지가 필요합니다. 파일 업로드 섹션에서 모범 답안을 업로드해주세요.")
                    return
                
                student_info_file = st.session_state.uploaded_files.get('student_info')
                image_files = st.session_state.uploaded_files.get('image_files')
                
                if student_info_file and image_files:
                    # Save uploaded files temporarily
                    import tempfile
                    import os
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                        tmp_file.write(student_info_file.read())
                        tmp_file_path = tmp_file.name
                    
                    # Save image files temporarily
                    temp_image_paths = []
                    temp_dir = tempfile.mkdtemp()
                    
                    try:
                        for image_file in image_files:
                            image_path = os.path.join(temp_dir, image_file.name)
                            with open(image_path, 'wb') as f:
                                f.write(image_file.read())
                            temp_image_paths.append(image_path)
                        
                        result = file_service.process_student_data(
                            excel_file_path=tmp_file_path,
                            grading_type="map",
                            image_files=temp_image_paths
                        )
                        
                        if result['success']:
                            st.session_state.processed_students = result['students']
                            # Store temp directories for cleanup after grading
                            if 'temp_directories' not in st.session_state:
                                st.session_state.temp_directories = []
                            st.session_state.temp_directories.append(temp_dir)
                            st.success(f"✅ {len(result['students'])}명의 학생 데이터를 성공적으로 처리했습니다.")
                        else:
                            if 'error_info' in result:
                                display_file_upload_error(result['error_info'], student_info_file.name)
                            else:
                                st.error(f"❌ {result['message']}")
                            # Clean up on failure
                            import shutil
                            if os.path.exists(temp_dir):
                                shutil.rmtree(temp_dir)
                            return
                    
                    finally:
                        # Clean up Excel file only (keep image files for grading)
                        if os.path.exists(tmp_file_path):
                            os.unlink(tmp_file_path)
            
        except Exception as e:
            error_info = handle_error(
                e,
                ErrorType.FILE_PROCESSING,
                context="process_uploaded_files: unexpected error",
                user_context="파일 처리"
            )
            display_error(error_info)

    def cleanup_temp_directories(self):
        """Clean up temporary directories after grading completion."""
        if 'temp_directories' in st.session_state:
            import shutil
            for temp_dir in st.session_state.temp_directories:
                if os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                        print(f"DEBUG: Cleaned up temp directory: {temp_dir}")
                    except Exception as e:
                        print(f"DEBUG: Failed to clean up temp directory {temp_dir}: {e}")
            st.session_state.temp_directories = []
    
    def _save_uploaded_file(self, uploaded_file, prefix: str) -> str:
        """
        업로드된 파일을 임시 디렉토리에 저장합니다.
        
        Args:
            uploaded_file: Streamlit의 UploadedFile 객체
            prefix: 파일명 prefix (예: "reference", "student")
            
        Returns:
            str: 저장된 파일의 절대 경로
        """
        import tempfile
        import time
        
        # 임시 디렉토리 생성
        temp_dir = os.path.join(tempfile.gettempdir(), "geo_assess_temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # 파일 저장 (타임스탬프 추가로 중복 방지)
        timestamp = str(int(time.time()))
        file_path = os.path.join(temp_dir, f"{prefix}_{timestamp}_{uploaded_file.name}")
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        print(f"DEBUG: Saved uploaded file to: {file_path}")
        return file_path


def create_main_ui() -> MainUI:
    """
    Factory function to create MainUI instance.
    
    Returns:
        MainUI: Configured MainUI instance
    """
    return MainUI()