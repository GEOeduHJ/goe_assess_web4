"""지리 자동 채점 플랫폼의 메인 UI 컴포넌트."""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
import time
from enum import Enum

import streamlit as st

logger = logging.getLogger(__name__)


def display_file_upload_error(error_info, filename: str = ""):
    message = getattr(error_info, "user_message", str(error_info))
    if filename:
        st.error(f"📁 파일 '{filename}' 처리 오류: {message}")
    else:
        st.error(f"📁 파일 처리 오류: {message}")


def display_error(error_info, show_details: bool = False):
    error_type = getattr(getattr(error_info, "error_type", None), "value", "시스템 오류")
    message = getattr(error_info, "user_message", str(error_info))
    st.error(f"⚠️ {error_type}: {message}")
    if show_details and hasattr(error_info, "technical_details"):
        with st.expander("기술적 세부사항"):
            st.code(error_info.technical_details)


class GradingType(Enum):
    DESCRIPTIVE = "descriptive"
    MAP = "map"


class LLMModel(Enum):
    GEMINI = "gemini"
    GPT5_MINI = "gpt-5-mini"


class MainUI:
    """지리 자동 채점 플랫폼의 메인 UI 컨트롤러."""

    def __init__(self):
        self.initialize_session_state()

    def initialize_session_state(self):
        defaults = {
            "grading_type": None,
            "selected_model": None,
            "uploaded_files": {},
            "rubric_data": None,
            "current_page": "main",
            "processed_students": None,
            "rag_references": None,
            "uploaded_reference_files": None,
            "reference_image_path": None,
            "student_results": [],
            "grading_progress": None,
            "grading_errors": [],
            "grading_completed": False,
            "completed_count": 0,
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def render_main_page(self):
        st.markdown("## 🎯 채점 시스템 설정")
        st.markdown("---")
        self.render_grading_type_selection()
        if st.session_state.grading_type:
            st.markdown("---")
            self.render_model_selection_section()
            self.render_file_upload_section()
            self.render_navigation_buttons()

    def render_grading_type_selection(self):
        st.markdown("### 📝 채점 유형 선택")
        st.markdown("채점하고자 하는 문항의 유형을 선택해주세요.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝 텍스트 문항", key="descriptive_button", help="텍스트 기반 답안을 채점합니다.", use_container_width=True):
                self.handle_grading_type_selection(GradingType.DESCRIPTIVE)
        with col2:
            if st.button("🗺️ 백지도형 문항", key="map_button", help="이미지 기반 백지도 답안을 채점합니다.", use_container_width=True):
                self.handle_grading_type_selection(GradingType.MAP)
        if st.session_state.grading_type:
            name = "📝 텍스트 문항" if st.session_state.grading_type == GradingType.DESCRIPTIVE.value else "🗺️ 백지도형 문항"
            st.success(f"✅ 선택된 채점 유형: **{name}**")

    def handle_grading_type_selection(self, grading_type: GradingType):
        if st.session_state.grading_type == grading_type.value:
            return
        st.session_state.grading_type = grading_type.value
        self._reset_grading_workflow_state()
        st.rerun()

    def _reset_grading_workflow_state(self):
        reset_values = {
            "selected_model": None,
            "uploaded_files": {},
            "uploaded_reference_files": None,
            "reference_image_path": None,
            "rubric_data": None,
            "rubric": None,
            "processed_students": None,
            "rag_references": None,
            "student_results": [],
            "grading_progress": None,
            "grading_errors": [],
            "grading_completed": False,
            "completed_count": 0,
            "grading_session": None,
            "grading_thread": None,
            "grading_engine": None,
        }
        for key, value in reset_values.items():
            st.session_state[key] = value
        for queue_name in ("progress_queue", "result_queue"):
            q = st.session_state.get(queue_name)
            if q is not None:
                while True:
                    try:
                        q.get_nowait()
                    except Exception:
                        break

    def render_model_selection_section(self):
        st.markdown("### 🧠 LLM 모델 선택")
        if st.session_state.grading_type == GradingType.MAP.value:
            st.markdown("백지도형 문항 채점에 사용할 AI 모델을 선택해주세요.")
        else:
            st.markdown("텍스트 문항 채점에 사용할 AI 모델을 선택해주세요.")

        model_options = {
            LLMModel.GEMINI.value: {
                "name": "Google Gemini 2.5 Flash",
                "description": "Google의 멀티모달 AI 모델입니다.",
                "icon": "🔥",
            },
            LLMModel.GPT5_MINI.value: {
                "name": "OpenAI GPT-5 Mini",
                "description": "OpenAI의 추론 모델입니다.",
                "icon": "⚡",
            },
        }
        selected_model = st.radio(
            "모델 선택:",
            options=list(model_options.keys()),
            format_func=lambda value: f"{model_options[value]['icon']} {model_options[value]['name']}",
            key="model_selection",
        )
        if selected_model:
            st.session_state.selected_model = selected_model
            st.info(f"ℹ️ {model_options[selected_model]['description']}")

    def render_file_upload_section(self):
        st.markdown("### 📁 파일 업로드")
        if st.session_state.grading_type == GradingType.DESCRIPTIVE.value:
            self.render_descriptive_file_upload()
        elif st.session_state.grading_type == GradingType.MAP.value:
            self.render_map_file_upload()

    def render_descriptive_file_upload(self):
        st.markdown("#### 📚 참고 자료 (선택사항)")
        reference_files = st.file_uploader(
            "참고 자료 업로드",
            type=["pdf", "docx"],
            accept_multiple_files=True,
            key="reference_files",
        )
        if reference_files:
            st.session_state.uploaded_reference_files = reference_files
            st.session_state.uploaded_files["reference_files"] = reference_files
            st.success(f"✅ {len(reference_files)}개의 참고 자료가 업로드되었습니다.")

        st.markdown("#### 📝 학생 답안 데이터")
        student_data_file = st.file_uploader(
            "학생 답안 Excel 파일",
            type=["xlsx", "xls"],
            key="student_data_descriptive",
        )
        if student_data_file:
            st.session_state.uploaded_files["student_data"] = student_data_file
            st.success(f"✅ 학생 답안 파일이 업로드되었습니다: {student_data_file.name}")

    def render_map_file_upload(self):
        st.markdown("#### 📚 모범 답안 이미지")
        reference_image_file = st.file_uploader(
            "모범 답안 이미지:",
            type=["jpg", "jpeg", "png", "bmp"],
            key="reference_image_uploader",
        )
        if reference_image_file:
            reference_path = self._save_uploaded_file(reference_image_file, "reference")
            st.session_state.reference_image_path = reference_path
            st.success("✅ 모범 답안 이미지가 업로드되었습니다!")
            st.image(reference_image_file, caption="업로드된 모범 답안", width=400)
        else:
            st.warning("⚠️ 백지도형 채점을 위해 모범 답안 이미지를 업로드해주세요.")

        st.markdown("#### 📊 학생 정보 데이터")
        student_info_file = st.file_uploader("학생 정보 Excel 파일", type=["xlsx", "xls"], key="student_info_map")
        if student_info_file:
            st.session_state.uploaded_files["student_info"] = student_info_file
            st.success(f"✅ 학생 정보 파일이 업로드되었습니다: {student_info_file.name}")

        st.markdown("#### 🖼️ 학생 답안 이미지")
        image_files = st.file_uploader(
            "백지도 이미지 파일들",
            type=["jpg", "jpeg", "png", "bmp"],
            accept_multiple_files=True,
            key="image_files",
        )
        if image_files:
            st.session_state.uploaded_files["image_files"] = image_files
            st.success(f"✅ {len(image_files)}개의 이미지 파일이 업로드되었습니다.")

    def render_navigation_buttons(self):
        st.markdown("---")
        st.markdown("### 🚀 다음 단계")
        can_proceed = self.check_required_files()
        _, col = st.columns([1, 2])
        with col:
            if st.button(
                "📋 루브릭 설정하기",
                key="proceed_to_rubric" if can_proceed else "proceed_to_rubric_disabled",
                use_container_width=True,
                type="primary" if can_proceed else "secondary",
                disabled=not can_proceed,
                help=None if can_proceed else "필수 파일을 모두 업로드한 후 진행할 수 있습니다.",
            ):
                self.process_uploaded_files()
                st.session_state.current_page = "rubric"
                st.rerun()
        self.show_requirements_status()

    def check_required_files(self) -> bool:
        if not st.session_state.grading_type:
            return False
        if st.session_state.grading_type == GradingType.DESCRIPTIVE.value:
            return "student_data" in st.session_state.uploaded_files
        if st.session_state.grading_type == GradingType.MAP.value:
            return (
                "student_info" in st.session_state.uploaded_files
                and "image_files" in st.session_state.uploaded_files
                and st.session_state.get("reference_image_path") is not None
            )
        return False

    def show_requirements_status(self):
        st.markdown("#### ✅ 설정 완료 상태")
        if st.session_state.grading_type:
            name = "📝 텍스트" if st.session_state.grading_type == GradingType.DESCRIPTIVE.value else "🗺️ 백지도형"
            st.success(f"✅ 채점 유형: {name}")
        else:
            st.error("❌ 채점 유형을 선택해주세요")

        if st.session_state.selected_model:
            model_name = "Google Gemini 2.5 Flash" if st.session_state.selected_model == LLMModel.GEMINI.value else "OpenAI GPT-5 Mini"
            st.success(f"✅ LLM 모델: {model_name}")
        else:
            st.error("❌ LLM 모델을 선택해주세요")

        if st.session_state.grading_type == GradingType.DESCRIPTIVE.value:
            if "student_data" in st.session_state.uploaded_files:
                st.success("✅ 학생 답안 파일 업로드 완료")
            else:
                st.error("❌ 학생 답안 Excel 파일을 업로드해주세요")
            if st.session_state.uploaded_reference_files:
                st.success(f"✅ 참고 자료 {len(st.session_state.uploaded_reference_files)}개 업로드 완료")
            else:
                st.info("ℹ️ 참고 자료는 선택사항입니다")
        elif st.session_state.grading_type == GradingType.MAP.value:
            st.success("✅ 모범 답안 이미지 업로드 완료") if st.session_state.get("reference_image_path") else st.error("❌ 모범 답안 이미지를 업로드해주세요")
            st.success("✅ 학생 정보 파일 업로드 완료") if "student_info" in st.session_state.uploaded_files else st.error("❌ 학생 정보 Excel 파일을 업로드해주세요")
            if "image_files" in st.session_state.uploaded_files:
                st.success(f"✅ 이미지 파일 {len(st.session_state.uploaded_files['image_files'])}개 업로드 완료")
            else:
                st.error("❌ 학생 답안 이미지 파일들을 업로드해주세요")

    def process_uploaded_files(self):
        try:
            from services.file_service import FileService
            from utils.error_handler import ErrorType, handle_error

            file_service = FileService()
            if st.session_state.grading_type == GradingType.DESCRIPTIVE.value:
                student_file = st.session_state.uploaded_files.get("student_data")
                if student_file:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
                        tmp_file.write(student_file.read())
                        tmp_file_path = tmp_file.name
                    try:
                        result = file_service.process_student_data(tmp_file_path, grading_type="descriptive")
                        if result["success"]:
                            st.session_state.processed_students = result["students"]
                            st.success(f"✅ {len(result['students'])}명의 학생 데이터를 성공적으로 처리했습니다.")
                        else:
                            display_file_upload_error(result.get("error_info", result.get("message", "파일 처리 실패")), student_file.name)
                            return
                    finally:
                        if os.path.exists(tmp_file_path):
                            os.unlink(tmp_file_path)
            elif st.session_state.grading_type == GradingType.MAP.value:
                if not st.session_state.get("reference_image_path"):
                    st.error("❌ 백지도형 채점에는 모범 답안 이미지가 필요합니다.")
                    return
                student_info_file = st.session_state.uploaded_files.get("student_info")
                image_files = st.session_state.uploaded_files.get("image_files")
                if student_info_file and image_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
                        tmp_file.write(student_info_file.read())
                        tmp_file_path = tmp_file.name
                    temp_dir = tempfile.mkdtemp()
                    try:
                        temp_image_paths = []
                        for image_file in image_files:
                            image_path = os.path.join(temp_dir, image_file.name)
                            with open(image_path, "wb") as file:
                                file.write(image_file.read())
                            temp_image_paths.append(image_path)
                        result = file_service.process_student_data(tmp_file_path, grading_type="map", image_files=temp_image_paths)
                        if result["success"]:
                            st.session_state.processed_students = result["students"]
                            st.session_state.setdefault("temp_directories", []).append(temp_dir)
                            st.success(f"✅ {len(result['students'])}명의 학생 데이터를 성공적으로 처리했습니다.")
                        else:
                            display_file_upload_error(result.get("error_info", result.get("message", "파일 처리 실패")), student_info_file.name)
                            if os.path.exists(temp_dir):
                                shutil.rmtree(temp_dir)
                            return
                    finally:
                        if os.path.exists(tmp_file_path):
                            os.unlink(tmp_file_path)
        except Exception as exc:
            from utils.error_handler import ErrorType, handle_error

            display_error(handle_error(exc, ErrorType.FILE_PROCESSING, context="process_uploaded_files", user_context="파일 처리"))

    def cleanup_temp_directories(self):
        for temp_dir in st.session_state.get("temp_directories", []):
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug("Cleaned up temp directory")
                except Exception as exc:
                    logger.warning("Failed to clean up temp directory: %s", exc)
        st.session_state.temp_directories = []

    def _save_uploaded_file(self, uploaded_file, prefix: str) -> str:
        temp_dir = os.path.join(tempfile.gettempdir(), "geo_assess_temp")
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, f"{prefix}_{int(time.time())}_{uploaded_file.name}")
        with open(file_path, "wb") as file:
            file.write(uploaded_file.getbuffer())
        logger.debug("Saved uploaded file: prefix=%s", prefix)
        return file_path


def create_main_ui() -> MainUI:
    return MainUI()
