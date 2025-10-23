# 🗺️ 지리과 자동 채점 플랫폼

**AI 기반 지리 교과목 특화 자동 채점 시스템**

Streamlit 웹 UI와 Google Gemini API를 활용하여 서술형 및 백지도형 답안을 자동으로 채점하고 상세한 피드백을 제공하는 교육용 플랫폼입니다.

**2025년 10월 기준 주요 변경사항:**
- Groq 모델 선택 기능은 UI에서 비활성화되어 사용자 선택 불가 (내부 로직은 유지)
- OpenAI GPT-5 Mini 모델이 텍스트/이미지 문항 모두 지원됨

## ✨ 주요 기능

### 🎯 지원 채점 유형
- **텍스트 문항 자동 채점**: RAG 기반 참고 문서와 LLM을 활용한 텍스트 답안 평가
- **백지도형 문항 자동 채점**: 이미지 업로드 및 AI 기반 지도 답안 평가, 참조 이미지 비교 지원

### 📊 실제 핵심 기능
- **동적 루브릭 빌더**: UI에서 평가 요소/기준 직접 추가·수정, 샘플 루브릭 불러오기
- **실시간 채점 진행률 표시**: 다중 학생 답안 순차 처리, 진행 상황 및 오류 자동 재시도
- **상세 결과 분석 및 피드백**: 학생별 점수, 판단 근거, 개선 피드백, 등급 산출
- **Excel 결과 내보내기**: 전체 채점 결과를 구조화된 Excel 파일로 다운로드
- **참고 문서 기반 RAG 시스템**: PDF/DOCX 업로드, 벡터 임베딩 및 유사도 검색
 - **이미지 분석 및 지도 문항 채점**: 백지도형 이미지 업로드, 참조 이미지 비교, AI 기반 지도 답안 평가

### 🤖 실제 AI 모델 지원
- **Google Gemini 2.5 Flash**: 텍스트/이미지 멀티모달 채점
- **OpenAI GPT-5 Mini**: 텍스트/이미지 채점 (UI에서 선택 가능)
- **Groq API**: 고속 텍스트 채점 (내부 로직만 유지, UI에서 선택 불가)
- **KURE-v1 Embedding**: 한국어 문서 벡터 임베딩 및 검색

## 🚀 설치 및 실행

### 1. 프로젝트 클론
```bash
git clone https://github.com/GEOeduHJ/goe_assess_web4.git
cd goe_assess_web4
```

### 2. 가상환경 활성화
```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 3. 의존성 설치
```bash
uv pip install -r requirements.txt
```

### 4. 환경 변수 설정
`.env` 또는 `.streamlit/secrets.toml` 파일에 아래와 같이 4가지 API 키를 반드시 입력해야 합니다. 
이 파일은 외부(공개 저장소 등)에 절대 노출하지 마세요.

```toml
[api]
google_api_key = "your_google_api_key_here"
groq_api_key = "your_groq_api_key_here"
openai_api_key = "your_openai_api_key_here"
hf_token = "your_huggingface_token_here"
```


### 5. 애플리케이션 실행
```bash
streamlit run app.py
```

## 📁 프로젝트 구조

```
geo_assess_web4/
├── app.py                  # 메인 Streamlit 앱 진입점
├── config.py               # 환경 변수 및 설정 관리
├── requirements.txt        # Python 의존성 목록
├── pyproject.toml          # 프로젝트 메타데이터
├── README.md               # 프로젝트 설명
├── ui/                     # Streamlit UI 컴포넌트
│   ├── main_ui.py          # 메인 인터페이스 및 내비게이션
│   ├── rubric_ui.py        # 루브릭 설정 UI
│   ├── grading_execution_ui.py # 채점 실행 및 진행률 UI
│   ├── results_ui.py       # 결과 표시 및 시각화 UI
│   └── __init__.py
├── services/               # 비즈니스 로직 서비스
│   ├── llm_service.py      # LLM API 통합 (Gemini, Groq, GPT-5-mini)
│   ├── rag_service.py      # RAG 문서 처리 및 검색
│   ├── grading_engine.py   # 순차 채점 엔진
│   ├── file_service.py     # 파일 업로드 및 처리
│   ├── export_service.py   # Excel 결과 내보내기
│   └── __init__.py
├── models/                 # 데이터 모델
│   ├── student_model.py    # 학생 정보 모델
│   ├── rubric_model.py     # 루브릭 및 평가 기준 모델
│   ├── result_model.py     # 채점 결과 모델
│   └── __init__.py
├── utils/                  # 유틸리티 함수
│   ├── prompt_utils.py     # 프롬프트 생성 및 응답 파싱
│   ├── embedding_utils.py  # 임베딩 및 벡터 처리
│   ├── error_handler.py    # 통합 오류 처리
│   └── __init__.py
└── sample_data/            # 샘플 데이터 및 테스트 파일
```

## 🛠️ 기술 스택

### Frontend
- **Streamlit**: 웹 UI 프레임워크
- **Plotly**: 데이터 시각화

### Backend & AI
- **Google Gemini API**: 멀티모달 AI 모델 (텍스트 + 이미지)
- **Groq API**: 고속 텍스트 처리
- **LangChain**: RAG 파이프라인 구축
- **FAISS**: 벡터 유사도 검색
- **Sentence Transformers**: 텍스트 임베딩

### Data Processing
- **Pandas**: 데이터 처리 및 분석
- **OpenPyXL**: Excel 파일 처리
- **PyPDF2**: PDF 문서 처리
- **python-docx**: Word 문서 처리

## 🎯 사용법

### 1. 채점 유형 선택
- **서술형**: 텍스트 답안 + 참고 문서 활용
- **백지도형**: 이미지 답안 분석

### 2. 파일 업로드
**서술형:**
- 참고 문서 (PDF, DOCX)
- 학생 답안 Excel (학생명, 반, 답안)

**백지도형:**
- 학생 목록 Excel (학생명, 반)
- 백지도 이미지 파일들 (파일명에 학생명 포함)

### 3. 루브릭 설정
- 평가 요소 추가/삭제
- 각 요소별 채점 기준 및 점수 설정

### 4. 채점 실행
- AI 모델 선택 (Gemini/GPT-5 Mini)
- Groq 모델은 UI에서 선택 불가 (내부 로직만 유지)
- 실시간 진행률 모니터링
- 오류 발생시 자동 재시도

### 5. 결과 확인
- 학생별 상세 결과 보기
- 통계 분석 및 시각화
- Excel 파일로 결과 내보내기

## 📊 채점 결과 구조

### 개별 학생 결과
- **점수**: 요소별 점수 및 총점
- **등급**: 한국 내신 5등급제 상대평가 (1등급 상위 10%, 2등급 상위 34%, 3등급 상위 66%, 4등급 상위 87%, 5등급 상위 100%)
- **판단 근거**: 점수 부여 이유 상세 설명
- **피드백**: 답안 개선을 위한 구체적 조언
- **채점 시간**: 처리 소요 시간

### 전체 통계
- 평균 점수 및 분포
- 요소별 성과 분석
- 채점 시간 통계
- 등급별 학생 수

## 🔧 고급 설정

### Streamlit Cloud 배포
1. Streamlit Cloud에 GitHub 연동
2. Secrets 설정에서 API 키 입력:
```toml
[api]
google_api_key = "your_google_api_key"
groq_api_key = "your_groq_api_key" # (내부 로직용, UI에서 선택 불가)
```

### 성능 최적화
- **청킹 크기**: 500토큰 (조정 가능)
- **Top-K 검색**: 3개 문서 (RAG)
- **배치 처리**: 최대 10명 동시 처리
- **API 재시도**: 최대 3회

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🙋‍♂️ 지원

- **이슈 리포트**: [GitHub Issues](https://github.com/GEOeduHJ/goe_assess_web4/issues)
- **기능 요청**: [GitHub Discussions](https://github.com/GEOeduHJ/goe_assess_web4/discussions)

---

**Made with ❤️ for Geography Education**