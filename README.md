# 지리과 자동 채점 플랫폼

AI를 활용한 지리과 서술형 및 백지도형 답안 자동 채점 시스템입니다.

## 기능

- 📝 서술형 문항 자동 채점 (RAG 기반)
- 🗺️ 백지도형 문항 자동 채점 (이미지 분석)
- 📊 동적 루브릭 설정
- 📈 실시간 채점 진행률 표시
- 📋 Excel 결과 내보내기

## 설치 및 실행

### 1. 프로젝트 클론 및 환경 설정

```bash
# 가상환경 활성화 (이미 생성됨)
.venv\Scripts\activate

# 의존성이 이미 설치되어 있습니다
```

### 2. 환경 변수 설정

`.env` 파일에 필요한 API 키를 설정하세요:

```env
GOOGLE_API_KEY=your_google_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

### 3. 애플리케이션 실행

```bash
uv run streamlit run app.py
```

## 프로젝트 구조

```
geography-auto-grading/
├── ui/                 # UI 컴포넌트
├── services/           # 비즈니스 로직 서비스
├── models/             # 데이터 모델
├── utils/              # 유틸리티 함수
├── config.py           # 설정 관리
├── app.py              # 메인 애플리케이션
├── .env                # 환경 변수
└── pyproject.toml      # 프로젝트 설정
```

## 개발 상태

- ✅ 프로젝트 초기 설정 완료
- 🚧 데이터 모델 구현 중
- ⏳ UI 컴포넌트 개발 예정
- ⏳ RAG 서비스 개발 예정
- ⏳ LLM 서비스 개발 예정

## 기술 스택

- **Frontend**: Streamlit
- **AI/ML**: Google Gemini, Groq, Sentence Transformers
- **Vector DB**: FAISS
- **Data Processing**: Pandas, OpenPyXL
- **Document Processing**: PyPDF2, python-docx