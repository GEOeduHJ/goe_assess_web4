# 서술형 문항 채점 로직 모식도

이 문서는 지리 자동 채점 시스템의 서술형 문항 채점 로직을 Mermaid 다이어그램으로 표현한 것입니다.

## 전체 채점 흐름

```mermaid
flowchart TD
    A[사용자: Streamlit UI] --> B[채점 유형 선택: 서술형]
    B --> C[파일 업로드]
    C --> D[학생 답안 Excel]
    C --> E[참고 문서 PDF/DOCX]

    D --> F[학생 데이터 파싱]
    E --> G[문서 텍스트 추출]

    F --> H[grading_engine.grade_students_sequential]
    G --> I[RAG 인덱스 생성 - 1회만]

    H --> J[학생별 처리 루프]
    I --> K[rag_service.process_documents]

    J --> L[학생 1 처리]
    J --> M[학생 2 처리]
    J --> N[학생 N 처리]

    L --> O[RAG 검색: search_relevant_content]
    O --> P[유사 청크 3개 검색]

    P --> Q[프롬프트 생성: generate_prompt]
    Q --> R[시스템 역할]
    Q --> S[참고 자료 포함]
    Q --> T[평가 루브릭]
    Q --> U[학생 답안]
    Q --> V[출력 포맷]

    V --> W[LLM API 호출]
    W --> X{모델 선택}
    X -->|Gemini| Y[call_gemini_api]
    X -->|Groq| Z[call_groq_api]

    Y --> AA[응답 파싱]
    Z --> AA

    AA --> BB[결과 저장]
    BB --> CC[UI 업데이트]
    CC --> DD[다음 학생 처리]

    DD --> EE{모든 학생 완료?}
    EE -->|아니오| J
    EE -->|예| FF[채점 완료]

    style A fill:#e1f5fe
    style B fill:#e1f5fe
    style C fill:#e1f5fe
    style H fill:#fff3e0
    style K fill:#fff3e0
    style O fill:#fff3e0
    style Q fill:#fff3e0
    style W fill:#fff3e0
    style Y fill:#4caf50
    style Z fill:#2196f3
```

## 상세 컴포넌트 설명

### 1. RAG 파이프라인 상세

```mermaid
flowchart TD
    A[참고 문서 업로드] --> B[rag_service.process_documents]
    B --> C[문서별 텍스트 추출]
    C --> D[_extract_pdf_content 또는 _extract_docx_content]
    D --> E[텍스트 전처리: clean_text]
    E --> F[특수문자 제거<br/>영어/한글/숫자/기본문장부호만 유지]
    F --> G[_chunk_document]
    G --> H[토큰 기반 청크화<br/>chunk_tokens=500<br/>overlap_tokens=100]
    H --> I[청크 임베딩<br/>HuggingFace Embeddings]
    I --> J[FAISS 벡터 저장소 생성]
    J --> K[RAG 인덱스 준비 완료]

    style E fill:#fff3e0
    style G fill:#fff3e0
    style I fill:#4caf50
```

### 2. 학생별 채점 처리

```mermaid
flowchart TD
    A[학생별 루프 시작] --> B[rag_service.search_relevant_content]
    B --> C[학생 답안으로 유사도 검색]
    C --> D[top_k=3 청크 검색]
    D --> E[청크 리스트 반환]

    E --> F[llm_service.generate_prompt]
    F --> G[프롬프트 구성]
    G --> H[시스템 역할: 지리 전문 채점자]
    G --> I[참고 자료: 검색된 3개 청크]
    G --> J[평가 루브릭: 요소별 기준]
    G --> K[학생 답안: 전체 텍스트]
    G --> L[출력 포맷: JSON 스키마]

    L --> M[프롬프트 완성]
    M --> N[모델 선택 및 API 호출]
    N --> O[Gemini 또는 Groq API]
    O --> P[temperature=0.1]
    P --> Q[응답 수신 및 파싱]
    Q --> R[JSON 결과 추출]
    R --> S[결과 저장 및 UI 업데이트]

    style B fill:#fff3e0
    style F fill:#fff3e0
    style N fill:#4caf50
    style O fill:#2196f3
```

### 3. API 호출 분기

```mermaid
flowchart TD
    A[프롬프트 생성 완료] --> B[select_model 호출]
    B --> C{채점 유형?}
    C -->|지도| D[Gemini 필수]
    C -->|서술형| E{사용자 선택?}

    E -->|Gemini| F{Gemini API 키?}
    F -->|있음| G[call_gemini_api]
    F -->|없음| H{Fallback}

    E -->|Groq| I{Groq 클라이언트?}
    I -->|있음| J[call_groq_api]
    I -->|없음| H

    H --> K{사용 가능 모델?}
    K -->|Gemini 우선| G
    K -->|Groq| J
    K -->|없음| L[오류 발생]

    G --> M[Gemini API 호출<br/>temperature=0.1]
    J --> N[Groq API 호출<br/>temperature=0.1<br/>model=qwen/qwen3-32b]

    M --> O[응답 파싱]
    N --> O

    style G fill:#4caf50
    style J fill:#2196f3
    style M fill:#4caf50
    style N fill:#2196f3
```

## 주요 특징

### 🔄 최적화된 RAG 처리
- **1회 인덱싱**: 배치 시작 시 참고 문서로 RAG 인덱스를 한 번만 생성
- **학생별 검색**: 각 학생 답안으로 유사도 검색만 수행 (재인덱싱 없음)
- **토큰 기반 청크**: tiktoken으로 정확한 토큰 수 계산
- **전처리 적용**: 특수문자 제거로 검색 품질 향상

### 🤖 LLM 통합
- **모델 선택**: Gemini (멀티모달) 또는 Groq (텍스트 전용)
- **일관된 설정**: 두 모델 모두 temperature=0.1로 채점 일관성 확보
- **프롬프트 구조**: 시스템 역할 → 참고 자료 → 루브릭 → 답안 → 출력 포맷

### 📊 처리 흐름
1. **준비 단계**: UI에서 파일 업로드 및 설정
2. **인덱싱 단계**: RAG 인덱스 생성 (한 번)
3. **채점 단계**: 학생별로 검색 → 프롬프트 → API 호출 → 결과 저장
4. **완료 단계**: 전체 결과 집계 및 내보내기

이 모식도는 실제 코드의 실행 흐름을 정확히 반영하고 있습니다.