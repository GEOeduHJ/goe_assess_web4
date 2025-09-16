# 🗺️ 지리과 자동 채점 플랫폼

**AI 기반 지리 교과목 특화 자동 채점 시스템**

Streamlit 웹 UI와 Google Gemini API를 활용하여 서술형 및 백지도형 답안을 자동으로 채점하고 상세한 피드백을 제공하는 교육용 플랫폼입니다.

## ✨ 주요 기능

### 🎯 채점 유형
- **📝 서술형 문항**: RAG 기반 참고 자료 활용한 텍스트 답안 채점
- **🗺️ 백지도형 문항**: 이미지 분석 기반 백지도 답안 채점

### 📊 핵심 기능
- **동적 루브릭 설정**: 웹 UI에서 평가 요소와 채점 기준 자유 설정
- **실시간 채점 진행률**: 다중 학생 답안 순차 처리 및 진행 상황 실시간 표시
- **상세 결과 분석**: 학생별 점수, 판단 근거, 개선 피드백 제공
- **Excel 결과 내보내기**: 전체 채점 결과를 구조화된 Excel 파일로 내보내기
- **RAG 시스템**: 참고 문서 기반 맥락적 채점 (서술형 전용)

### 🤖 AI 모델 지원
- **Google Gemini 1.5 Flash**: 텍스트 및 이미지 분석
- **Groq API**: 고속 텍스트 분석 (서술형 전용)
- **KURE-v1 Embedding**: 한국어 특화 문서 임베딩

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
pip install -r requirements.txt
```

### 4. 환경 변수 설정
`.env` 파일을 생성하고 API 키를 설정하세요:

```env
# Google Gemini API
GOOGLE_API_KEY=your_google_api_key_here

# Groq API (선택사항)
GROQ_API_KEY=your_groq_api_key_here

# HuggingFace Token (선택사항)
HF_TOKEN=your_huggingface_token_here
```

**API 키 발급:**
- **Google Gemini**: [Google AI Studio](https://aistudio.google.com/app/apikey)
- **Groq**: [Groq Console](https://console.groq.com/keys)

### 5. 애플리케이션 실행
```bash
streamlit run app.py
```

## 📁 프로젝트 구조

```
geo_assess_web4/
├── app.py                  # 메인 애플리케이션 진입점
├── config.py              # 설정 관리 및 환경변수 처리
├── requirements.txt       # Python 의존성 목록
├── pyproject.toml         # 프로젝트 메타데이터
│
├── ui/                    # Streamlit UI 컴포넌트
│   ├── main_ui.py         # 메인 인터페이스 및 내비게이션
│   ├── rubric_ui.py       # 루브릭 설정 UI
│   ├── grading_execution_ui.py  # 채점 실행 및 진행률 UI
│   └── results_ui.py      # 결과 표시 및 시각화 UI
│
├── services/              # 비즈니스 로직 서비스
│   ├── llm_service.py     # LLM API 통합 (Gemini, Groq)
│   ├── rag_service.py     # RAG 문서 처리 및 검색
│   ├── grading_engine.py  # 순차 채점 엔진
│   ├── file_service.py    # 파일 업로드 및 처리
│   └── export_service.py  # Excel 결과 내보내기
│
├── models/                # 데이터 모델
│   ├── student_model.py   # 학생 정보 모델
│   ├── rubric_model.py    # 루브릭 및 평가 기준 모델
│   └── result_model.py    # 채점 결과 모델
│
├── utils/                 # 유틸리티 함수
│   ├── prompt_utils.py    # 프롬프트 생성 및 응답 파싱
│   ├── embedding_utils.py # 임베딩 및 벡터 처리
│   └── error_handler.py   # 통합 오류 처리
│
├── docs/                  # 문서화
├── sample_data/          # 샘플 데이터 및 테스트 파일
└── .streamlit/           # Streamlit 설정
    └── secrets.toml      # 로컬 개발용 시크릿 (gitignore됨)
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
- AI 모델 선택 (Gemini/Groq)
- 실시간 진행률 모니터링
- 오류 발생시 자동 재시도

### 5. 결과 확인
- 학생별 상세 결과 보기
- 통계 분석 및 시각화
- Excel 파일로 결과 내보내기

## 📊 채점 결과 구조

### 개별 학생 결과
- **점수**: 요소별 점수 및 총점
- **등급**: A~F 자동 계산 (90%이상 A, 80%이상 B, ...)
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
groq_api_key = "your_groq_api_key"
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