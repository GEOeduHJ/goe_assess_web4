"""
Main UI components for the geography auto-grading platform.
Handles grading type selection, model selection, and file uploads.
"""

import streamlit as st
from typing import Optional, List, Dict, Any
from enum import Enum


class GradingType(Enum):
    """Enumeration for grading types."""
    DESCRIPTIVE = "descriptive"
    MAP = "map"


class LLMModel(Enum):
    """Enumeration for available LLM models."""
    GEMINI = "gemini"
    GROQ = "groq"


class MainUI:
    """Main UI controller for the geography auto-grading platform."""
    
    def __init__(self):
        """Initialize the main UI controller."""
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """Initialize Streamlit session state variables."""
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
    
    def render_main_page(self):
        """
        Render the main page with all UI components.
        """
        # Page header
        st.markdown("## 🎯 채점 시스템 설정")
        st.markdown("---")
        
        # Grading type selection
        self.render_grading_type_selection()
        
        # Show additional options based on selected grading type
        if st.session_state.grading_type:
            st.markdown("---")
            
            # Model selection (for descriptive type)
            if st.session_state.grading_type == GradingType.DESCRIPTIVE.value:
                self.render_model_selection()
            
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
                "📝 서술형 문항",
                key="descriptive_button",
                help="텍스트 기반 서술형 답안을 채점합니다. 참고 자료를 활용한 RAG 기반 채점이 가능합니다.",
                use_container_width=True
            ):
                self.handle_grading_type_selection(GradingType.DESCRIPTIVE)
        
        with col2:
            if st.button(
                "🗺️ 백지도형 문항",
                key="map_button", 
                help="이미지 기반 백지도 답안을 채점합니다. Google Gemini의 이미지 분석 기능을 사용합니다.",
                use_container_width=True
            ):
                self.handle_grading_type_selection(GradingType.MAP)
        
        # Display current selection
        if st.session_state.grading_type:
            grading_type_name = "📝 서술형 문항" if st.session_state.grading_type == GradingType.DESCRIPTIVE.value else "🗺️ 백지도형 문항"
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
    
    def render_model_selection(self):
        """
        Render LLM model selection for descriptive grading.
        Implements Requirement 5.1
        """
        st.markdown("### 🤖 LLM 모델 선택")
        st.markdown("서술형 문항 채점에 사용할 AI 모델을 선택해주세요.")
        
        model_options = {
            LLMModel.GEMINI.value: {
                "name": "Google Gemini 2.5 Flash",
                "description": "Google의 최신 멀티모달 AI 모델. 텍스트와 이미지 분석이 모두 가능합니다.",
                "icon": "🔥"
            },
            LLMModel.GROQ.value: {
                "name": "Groq Qwen3",
                "description": "빠른 추론 속도를 제공하는 텍스트 전용 AI 모델입니다.",
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
            st.session_state.uploaded_files['reference_files'] = reference_files
            st.success(f"✅ {len(reference_files)}개의 참고 자료가 업로드되었습니다.")
            
            # Display uploaded files
            with st.expander("📋 업로드된 참고 자료 목록"):
                for i, file in enumerate(reference_files, 1):
                    st.write(f"{i}. {file.name} ({file.size:,} bytes)")
        
        st.markdown("#### 📝 학생 답안 데이터")
        st.markdown("학생 이름, 반, 답안이 포함된 Excel 파일을 업로드해주세요.")
        
        # Show required format
        with st.expander("📋 필수 Excel 파일 형식"):
            st.markdown("""
            **필수 열 구성:**
            - `학생 이름`: 학생의 이름
            - `반`: 학생의 반 정보
            - `답안`: 학생이 작성한 서술형 답안
            
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
                    st.write(f"{i}. {file.name} ({file.size:,} bytes)")
    
    def render_navigation_buttons(self):
        """
        Render navigation buttons for proceeding to next steps.
        """
        st.markdown("---")
        st.markdown("### 🚀 다음 단계")
        
        # Check if required files are uploaded
        can_proceed = self.check_required_files()
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
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
            # For map: both student info and image files are required
            return ('student_info' in st.session_state.uploaded_files and 
                    'image_files' in st.session_state.uploaded_files)
        
        return False
    
    def show_requirements_status(self):
        """
        Show the current status of requirements.
        """
        st.markdown("#### ✅ 설정 완료 상태")
        
        # Grading type status
        if st.session_state.grading_type:
            grading_type_name = "📝 서술형" if st.session_state.grading_type == GradingType.DESCRIPTIVE.value else "🗺️ 백지도형"
            st.success(f"✅ 채점 유형: {grading_type_name}")
        else:
            st.error("❌ 채점 유형을 선택해주세요")
        
        # Model selection status (for descriptive only)
        if st.session_state.grading_type == GradingType.DESCRIPTIVE.value:
            if st.session_state.selected_model:
                model_name = "Google Gemini 2.5 Flash" if st.session_state.selected_model == LLMModel.GEMINI.value else "Groq Qwen3"
                st.success(f"✅ LLM 모델: {model_name}")
            else:
                st.error("❌ LLM 모델을 선택해주세요")
        
        # File upload status
        if st.session_state.grading_type == GradingType.DESCRIPTIVE.value:
            if 'student_data' in st.session_state.uploaded_files:
                st.success("✅ 학생 답안 파일 업로드 완료")
            else:
                st.error("❌ 학생 답안 Excel 파일을 업로드해주세요")
            
            if 'reference_files' in st.session_state.uploaded_files:
                st.success(f"✅ 참고 자료 {len(st.session_state.uploaded_files['reference_files'])}개 업로드 완료")
            else:
                st.info("ℹ️ 참고 자료는 선택사항입니다")
        
        elif st.session_state.grading_type == GradingType.MAP.value:
            if 'student_info' in st.session_state.uploaded_files:
                st.success("✅ 학생 정보 파일 업로드 완료")
            else:
                st.error("❌ 학생 정보 Excel 파일을 업로드해주세요")
            
            if 'image_files' in st.session_state.uploaded_files:
                st.success(f"✅ 이미지 파일 {len(st.session_state.uploaded_files['image_files'])}개 업로드 완료")
            else:
                st.error("❌ 학생 답안 이미지 파일들을 업로드해주세요")


    def process_uploaded_files(self):
        """Process uploaded files and prepare data for grading."""
        try:
            from services.file_service import FileService
            from services.rag_service import RAGService
            from utils.error_handler import handle_error, ErrorType
            from ui.error_display_ui import display_file_upload_error, display_error
            
            file_service = FileService()
            
            # Process student data based on grading type
            if st.session_state.grading_type == GradingType.DESCRIPTIVE.value:
                # Process descriptive grading files
                student_file = st.session_state.uploaded_files.get('student_data')
                if student_file:
                    # Save uploaded file temporarily
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
                
                # Process reference files for RAG
                reference_files = st.session_state.uploaded_files.get('reference_files')
                if reference_files:
                    try:
                        rag_service = RAGService()
                        result = rag_service.process_reference_documents(reference_files)
                        
                        if result['success']:
                            st.session_state.rag_references = result
                            st.success(f"✅ {result['chunks_created']}개의 참고 자료 청크를 생성했습니다.")
                        else:
                            st.error(f"❌ 참고 자료 처리 실패: {result['message']}")
                    
                    except Exception as e:
                        error_info = handle_error(
                            e,
                            ErrorType.FILE_PROCESSING,
                            context="process_uploaded_files: RAG processing failed",
                            user_context="참고 자료 처리"
                        )
                        display_error(error_info)
            
            elif st.session_state.grading_type == GradingType.MAP.value:
                # Process map grading files
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
                            st.success(f"✅ {len(result['students'])}명의 학생 데이터를 성공적으로 처리했습니다.")
                        else:
                            if 'error_info' in result:
                                display_file_upload_error(result['error_info'], student_info_file.name)
                            else:
                                st.error(f"❌ {result['message']}")
                            return
                    
                    finally:
                        # Clean up temporary files
                        if os.path.exists(tmp_file_path):
                            os.unlink(tmp_file_path)
                        
                        import shutil
                        if os.path.exists(temp_dir):
                            shutil.rmtree(temp_dir)
            
        except Exception as e:
            error_info = handle_error(
                e,
                ErrorType.FILE_PROCESSING,
                context="process_uploaded_files: unexpected error",
                user_context="파일 처리"
            )
            display_error(error_info)


def create_main_ui() -> MainUI:
    """
    Factory function to create MainUI instance.
    
    Returns:
        MainUI: Configured MainUI instance
    """
    return MainUI()