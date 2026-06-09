# 🗺️ 지리과 자동 채점 플랫폼

**AI 기반 지리 교과목 특화 자동 채점 시스템**

Streamlit 웹 UI와 Google Gemini 및 OpenAI API를 활용하여 서술형 및 백지도형 답안을 자동으로 채점하고 상세한 피드백을 제공하는 교육용 플랫폼입니다.

**주요 변경사항:**
- LLM provider를 Google Gemini와 OpenAI GPT-5.4 Mini로 정리
- RAG 설정이 환경 변수와 `config.py` 값을 따르도록 개선

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
- **Google Gemini 3.1 Flash Lite**: 텍스트/이미지 멀티모달 채점
- **OpenAI GPT-5.4 Mini**: 텍스트/이미지 채점 (UI에서 선택 가능)
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
`.env` 또는 `.streamlit/secrets.toml` 파일에 아래 API 키 중 사용할 모델에 해당하는 키를 입력합니다. 앱 시작에는 둘 중 하나 이상이 필요합니다.
이 파일은 외부(공개 저장소 등)에 절대 노출하지 마세요.

```toml
[api]
google_api_key = "your_google_api_key_here"
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
│   ├── llm_service.py      # LLM API 통합 (Gemini, GPT-5-mini)
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

## 🎯 사용법

### 1. 메인 설정/채점 유형 및 파일 업로드 (메인 페이지)
- **기능:** 한 페이지에서 채점 유형(텍스트/백지도형) 선택, AI 모델 선택, 파일 업로드까지 모두 수행
- **사용자 입력/작업:**
	- 채점 유형 선택: "📝 텍스트 문항" 또는 "🗺️ 백지도형 문항" 버튼 클릭
	- AI 모델 선택: Gemini 또는 GPT-5.4 Mini 중 선택
	- 파일 업로드:
		- 텍스트 문항: 참고 문서(PDF/DOCX, 선택), 학생 답안 Excel(필수, 학생명/반/답안)
		- 백지도형 문항: 모범 답안 이미지(필수), 학생 목록 Excel(필수, 학생명/반), 학생 답안 이미지들(필수, 파일명에 학생명 포함)
	- 업로드 현황: 업로드된 파일 목록, 필수 파일 업로드 여부, 선택된 유형/모델 상태 실시간 표시
	- 다음 단계 이동: 필수 파일이 모두 업로드되면 "루브릭 설정하기" 버튼 활성화 → 클릭 시 루브릭 설정 페이지로 이동

### 2. 루브릭 설정 (루브릭 설정 페이지)
- **기능:** 평가 요소/기준 추가·수정·삭제, 샘플 루브릭 불러오기, 점수 배분, 실시간 미리보기
- **사용자 입력/작업:**
	- 평가 요소 직접 추가/삭제
	- 각 요소별로 세부 채점 기준 및 점수 입력
	- 샘플 루브릭 불러오기 및 수정
	- 실시간으로 루브릭 구조 미리보기
	- 모든 설정 완료 후 "채점 실행" 페이지로 이동

### 3. 채점 실행 및 진행률 (채점 실행 페이지)
- **기능:** 자동 채점 시작/현재 학생 후 정지/중단, 진행률·오류·실패 재시도, 실시간 결과 미리보기
- **사용자 입력/작업:**
	- "채점 시작" 버튼 클릭 → 자동 채점 시작
	- 진행률, 완료/실패 학생 수, 평균 소요시간, 예상 완료시간 실시간 확인
	- 오류 발생 시 재시도/모델 변경/오류 무시 등 복구 옵션 선택 가능
	- 최근 채점 결과 미리보기(학생별 점수, 등급, 피드백 등)

### 4. 결과 확인 및 분석 (결과 페이지)
- **기능:** 전체/개별 학생 결과 상세 보기, 통계/시각화, Excel 다운로드
- **사용자 입력/작업:**
	- 학생별 상세 결과(점수, 등급, 피드백, 판단 근거) 확인
	- 전체 통계(평균, 분포, 등급별 인원 등) 및 Plotly 기반 시각화
	- 결과를 Excel 파일로 다운로드

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

**Made with ❤️ for Geography Education**
