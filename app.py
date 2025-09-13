"""
Main application entry point for the geography auto-grading platform.
"""

import streamlit as st
from config import config
from ui.main_ui import create_main_ui
from ui.rubric_ui import create_rubric_ui
# Performance monitoring imports removed as part of system monitoring cleanup


def main():
    """Main application function."""
    
    # Configure Streamlit page
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon="🗺️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Performance monitoring initialization removed as part of system monitoring cleanup
    
    # Display main title
    st.title(config.APP_TITLE)
    st.markdown("**AI 기반 지리과 자동 채점 시스템**")
    
    # Check API key configuration
    api_validation = config.validate_api_keys()
    if not api_validation["valid"]:
        st.error(f"⚠️ API 키가 설정되지 않았습니다: {', '.join(api_validation['missing_keys'])}")
        st.info("📝 .env 파일에 필요한 API 키를 설정해주세요.")
        
        # Show configuration help
        with st.expander("🔧 API 키 설정 방법"):
            st.markdown("""
            **.env 파일에 다음 API 키들을 설정해주세요:**
            
            ```
            GOOGLE_API_KEY=your_google_api_key_here
            GROQ_API_KEY=your_groq_api_key_here
            ```
            
            **API 키 발급 방법:**
            - **Google Gemini API**: [Google AI Studio](https://aistudio.google.com/app/apikey)에서 발급
            - **Groq API**: [Groq Console](https://console.groq.com/keys)에서 발급
            """)
        
        st.stop()
    
    # Initialize session state for page navigation
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "main"
    
    # Initialize other session state variables
    if 'student_results' not in st.session_state:
        st.session_state.student_results = []
    
    if 'grading_session' not in st.session_state:
        from ui.grading_execution_ui import GradingSession
        st.session_state.grading_session = GradingSession(
            students=[], 
            rubric=None,  # Will be set when user configures rubric
            model_type="", 
            grading_type=""
        )
    
    if 'grading_progress' not in st.session_state:
        st.session_state.grading_progress = None
    
    if 'grading_errors' not in st.session_state:
        st.session_state.grading_errors = []
    
    # Render appropriate page based on current state
    if st.session_state.current_page == "main":
        main_ui = create_main_ui()
        main_ui.render_main_page()
    elif st.session_state.current_page == "rubric":
        render_rubric_page()
    elif st.session_state.current_page == "grading":
        render_grading_page()
    elif st.session_state.current_page == "results":
        render_results_page()
    # Performance page routing removed as part of system monitoring cleanup
    
    # Sidebar with additional information (performance monitoring widget removed)
    render_sidebar()


def render_rubric_page():
    """Render the rubric configuration page."""
    # Navigation breadcrumb
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← 메인으로", key="back_to_main"):
            st.session_state.current_page = "main"
            st.rerun()
    
    with col2:
        st.markdown("**메인 > 루브릭 설정**")
    
    # Render rubric UI
    rubric_ui = create_rubric_ui()
    rubric_ui.render_rubric_builder()


def render_grading_page():
    """Render the grading execution page."""
    from ui.grading_execution_ui import create_grading_execution_ui
    from models.rubric_model import Rubric
    
    # Navigation breadcrumb
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← 루브릭으로", key="back_to_rubric"):
            st.session_state.current_page = "rubric"
            st.rerun()
    
    with col2:
        st.markdown("**메인 > 루브릭 설정 > 채점 실행**")
    
    # Check if required data is available
    if not st.session_state.get('processed_students'):
        st.error("❌ 학생 데이터가 처리되지 않았습니다. 메인 페이지로 돌아가서 파일을 다시 업로드해주세요.")
        return
    
    # Check if rubric is available (either as object or data)
    rubric = None
    if st.session_state.get('rubric'):
        rubric = st.session_state.rubric
    elif st.session_state.get('rubric_data'):
        rubric = Rubric.from_dict(st.session_state.rubric_data)
    
    if not rubric:
        st.error("❌ 루브릭이 설정되지 않았습니다. 루브릭 설정 페이지로 돌아가서 루브릭을 완성해주세요.")
        return
    
    # Ensure grading session has the rubric
    if 'grading_session' in st.session_state:
        st.session_state.grading_session.rubric = rubric
    
    # Get grading parameters
    students = st.session_state.processed_students
    print(f"DEBUG: Students from session state: {len(students) if students else 0}")
    
    model_type = st.session_state.get('selected_model', 'gemini')
    grading_type = st.session_state.get('grading_type', 'descriptive')
    references = st.session_state.get('rag_references')
    
    # Render grading execution UI
    grading_ui = create_grading_execution_ui()
    grading_ui.render_grading_execution_page(
        students=students,
        rubric=rubric,
        model_type=model_type,
        grading_type=grading_type,
        references=references
    )


def render_results_page():
    """Render the results display and visualization page."""
    from ui.results_ui import create_results_ui
    
    # Navigation breadcrumb
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← 채점으로", key="back_to_grading"):
            st.session_state.current_page = "grading"
            st.rerun()
    
    with col2:
        st.markdown("**메인 > 루브릭 설정 > 채점 실행 > 결과 분석**")
    
    # Check if results are available
    if not st.session_state.get('student_results'):
        st.error("❌ 채점 결과가 없습니다. 채점 실행 페이지로 돌아가서 채점을 완료해주세요.")
        return
    
    # Get results from session state
    results = st.session_state.student_results
    
    # Render results UI
    results_ui = create_results_ui()
    results_ui.render_results_page(results)

# Performance page rendering function removed as part of system monitoring cleanup


def render_sidebar():
    """Render sidebar with system information and navigation."""
    with st.sidebar:
        st.markdown("## 📊 시스템 정보")
        
        # Performance monitoring widget removed as part of system monitoring cleanup
        
        # Current configuration
        with st.expander("🔧 현재 설정"):
            st.write("**임베딩 모델:**", config.EMBEDDING_MODEL)
            st.write("**최대 파일 크기:**", f"{config.MAX_FILE_SIZE_MB}MB")
            st.write("**최대 재시도 횟수:**", config.MAX_RETRIES)
            st.write("**검색 결과 수:**", config.TOP_K_RETRIEVAL)
            # Performance-related configuration removed as part of system monitoring cleanup
            st.write("**배치 처리 크기:**", config.BATCH_PROCESSING_SIZE)
        
        # API status
        st.markdown("### 🔑 API 상태")
        api_validation = config.validate_api_keys()
        if api_validation["valid"]:
            st.success("✅ 모든 API 키가 설정되었습니다")
        else:
            st.error(f"❌ 누락된 API 키: {', '.join(api_validation['missing_keys'])}")
        
        # Help and documentation
        st.markdown("---")
        st.markdown("### 📚 도움말")
        
        with st.expander("📝 사용 방법"):
            st.markdown("""
            **1단계: 채점 유형 선택**
            - 서술형 또는 백지도형 중 선택
            
            **2단계: 파일 업로드**
            - 학생 답안 데이터 업로드
            - 참고 자료 업로드 (서술형만)
            
            **3단계: 루브릭 설정**
            - 평가 요소 및 채점 기준 설정
            
            **4단계: 채점 실행**
            - AI 모델을 통한 자동 채점
            
            **5단계: 결과 확인**
            - 채점 결과 확인 및 Excel 다운로드
            """)
        
        with st.expander("🔍 지원 파일 형식"):
            st.markdown("""
            **Excel 파일:**
            - .xlsx, .xls
            
            **참고 자료:**
            - PDF (.pdf)
            - Word 문서 (.docx)
            
            **이미지 파일:**
            - JPG (.jpg, .jpeg)
            - PNG (.png)
            - BMP (.bmp)
            """)
        
        # Performance dashboard link removed as part of system monitoring cleanup
        
        # Version information
        st.markdown("---")
        st.markdown("### ℹ️ 버전 정보")
        st.caption("지리과 자동 채점 플랫폼 v1.0")
        st.caption("Powered by Streamlit & AI")
        # Performance optimization caption removed as part of system monitoring cleanup


if __name__ == "__main__":
    main()