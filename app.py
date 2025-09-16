"""
지리 자동 채점 플랫폼의 메인 애플리케이션 진입점
"""

import streamlit as st
from config import config
from ui.main_ui import create_main_ui
from ui.rubric_ui import create_rubric_ui
# 시스템 모니터링 정리의 일환으로 성능 모니터링 임포트 제거


def main():
    """메인 애플리케이션 함수"""
    
    # Streamlit 페이지 설정
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon="🗺️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 시스템 모니터링 정리의 일환으로 성능 모니터링 초기화 제거
    
    # 메인 제목 표시
    st.title(config.APP_TITLE)
    st.markdown("**AI 기반 지리과 자동 채점 시스템**")
    
    # API 키 설정 확인
    api_validation = config.validate_api_keys()
    if not api_validation["valid"]:
        st.error(f"⚠️ API 키가 설정되지 않았습니다: {', '.join(api_validation['missing_keys'])}")
        st.info("📝 .env 파일에 필요한 API 키를 설정해주세요.")
        
        # 설정 도움말 표시
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
    
    # 페이지 네비게이션을 위한 세션 상태 초기화
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "main"
    
    # 다른 세션 상태 변수들 초기화
    if 'student_results' not in st.session_state:
        st.session_state.student_results = []
    
    if 'grading_session' not in st.session_state:
        from ui.grading_execution_ui import GradingSession
        st.session_state.grading_session = GradingSession(
            students=[], 
            rubric=None,  # 사용자가 루브릭을 설정할 때 지정됨
            model_type="", 
            grading_type=""
        )
    
    if 'grading_progress' not in st.session_state:
        st.session_state.grading_progress = None
    
    if 'grading_errors' not in st.session_state:
        st.session_state.grading_errors = []
    
    # 현재 상태에 따라 적절한 페이지 렌더링
    if st.session_state.current_page == "main":
        main_ui = create_main_ui()
        main_ui.render_main_page()
    elif st.session_state.current_page == "rubric":
        render_rubric_page()
    elif st.session_state.current_page == "grading":
        render_grading_page()
    elif st.session_state.current_page == "results":
        render_results_page()
    # 시스템 모니터링 정리의 일환으로 성능 페이지 라우팅 제거
    
    # 추가 정보가 포함된 사이드바 (성능 모니터링 위젯 제거)
    render_sidebar()


def render_rubric_page():
    """루브릭 설정 페이지를 렌더링합니다."""
    # 네비게이션 브레드크럼
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← 메인으로", key="back_to_main"):
            st.session_state.current_page = "main"
            st.rerun()
    
    with col2:
        st.markdown("**메인 > 루브릭 설정**")
    
    # 루브릭 UI 렌더링
    rubric_ui = create_rubric_ui()
    rubric_ui.render_rubric_builder()


def render_grading_page():
    """채점 실행 페이지를 렌더링합니다."""
    from ui.grading_execution_ui import create_grading_execution_ui
    from models.rubric_model import Rubric
    
    # 네비게이션 브레드크럼
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← 루브릭으로", key="back_to_rubric"):
            st.session_state.current_page = "rubric"
            st.rerun()
    
    with col2:
        st.markdown("**메인 > 루브릭 설정 > 채점 실행**")
    
    # 필요한 데이터가 있는지 확인
    if not st.session_state.get('processed_students'):
        st.error("❌ 학생 데이터가 처리되지 않았습니다. 메인 페이지로 돌아가서 파일을 다시 업로드해주세요.")
        return
    
    # 루브릭이 있는지 확인 (객체 또는 데이터로)
    rubric = None
    if st.session_state.get('rubric'):
        rubric = st.session_state.rubric
    elif st.session_state.get('rubric_data'):
        rubric = Rubric.from_dict(st.session_state.rubric_data)
    
    if not rubric:
        st.error("❌ 루브릭이 설정되지 않았습니다. 루브릭 설정 페이지로 돌아가서 루브릭을 완성해주세요.")
        return
    
    # 채점 세션이 루브릭을 갖도록 보장
    if 'grading_session' in st.session_state:
        st.session_state.grading_session.rubric = rubric
    
    # 채점 매개변수 가져오기
    students = st.session_state.processed_students
    print(f"DEBUG: Students from session state: {len(students) if students else 0}")
    
    model_type = st.session_state.get('selected_model', 'gemini')
    grading_type = st.session_state.get('grading_type', 'descriptive')
    references = st.session_state.get('rag_references')
    
    # Groq 모델 선택값 가져오기
    groq_model = st.session_state.get('selected_groq_model', 'qwen/qwen3-32b')
    
    # 채점 실행 UI 렌더링
    grading_ui = create_grading_execution_ui()
    grading_ui.render_grading_execution_page(
        students=students,
        rubric=rubric,
        model_type=model_type,
        grading_type=grading_type,
        references=references,
        groq_model=groq_model
    )


def render_results_page():
    """결과 표시 및 시각화 페이지를 렌더링합니다."""
    from ui.results_ui import create_results_ui
    
    # 네비게이션 브레드크럼
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("← 채점으로", key="back_to_grading"):
            st.session_state.current_page = "grading"
            st.rerun()
    
    with col2:
        st.markdown("**메인 > 루브릭 설정 > 채점 실행 > 결과 분석**")
    
    # 결과가 있는지 확인
    if not st.session_state.get('student_results'):
        st.error("❌ 채점 결과가 없습니다. 채점 실행 페이지로 돌아가서 채점을 완료해주세요.")
        return
    
    # 세션 상태에서 결과 가져오기
    results = st.session_state.student_results
    
    # 결과 UI 렌더링
    results_ui = create_results_ui()
    results_ui.render_results_page(results)

# 시스템 모니터링 정리의 일환으로 성능 페이지 렌더링 함수 제거


def render_sidebar():
    """시스템 정보와 네비게이션이 포함된 사이드바를 렌더링합니다."""
    with st.sidebar:
        st.markdown("## 📊 시스템 정보")
        
        # 시스템 모니터링 정리의 일환으로 성능 모니터링 위젯 제거
        
        # 현재 설정
        with st.expander("🔧 현재 설정"):
            st.write("**임베딩 모델:**", config.EMBEDDING_MODEL)
            st.write("**최대 파일 크기:**", f"{config.MAX_FILE_SIZE_MB}MB")
            st.write("**최대 재시도 횟수:**", config.MAX_RETRIES)
            st.write("**검색 결과 수:**", config.TOP_K_RETRIEVAL)
            # 시스템 모니터링 정리의 일환으로 성능 관련 설정 제거
            st.write("**배치 처리 크기:**", config.BATCH_PROCESSING_SIZE)
        
        # API 상태
        st.markdown("### 🔑 API 상태")
        api_validation = config.validate_api_keys()
        if api_validation["valid"]:
            st.success("✅ 모든 API 키가 설정되었습니다")
        else:
            st.error(f"❌ 누락된 API 키: {', '.join(api_validation['missing_keys'])}")
        
        # 도움말 및 문서
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
        
        # 시스템 모니터링 정리의 일환으로 성능 대시보드 링크 제거
        
        # 버전 정보
        st.markdown("---")
        st.markdown("### ℹ️ 버전 정보")
        st.caption("지리과 자동 채점 플랫폼 v1.0")
        st.caption("Powered by Streamlit & AI")
        # 시스템 모니터링 정리의 일환으로 성능 최적화 캡션 제거


if __name__ == "__main__":
    main()