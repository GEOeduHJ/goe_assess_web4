# 🏗️ 지리과 자동 채점 플랫폼 아키텍처

이 문서는 지리과 자동 채점 플랫폼의 전체 시스템 아키텍처와 데이터 흐름을 설명합니다.

## 1. 전체 프로젝트 구조

```mermaid
flowchart TD
    %% Frontend Layer
    subgraph "🖥️ Frontend Layer"
        UI[Streamlit Web UI]
        MAIN[main_ui.py<br/>메인 인터페이스]
        RUBRIC[rubric_ui.py<br/>루브릭 설정]
        EXEC[grading_execution_ui.py<br/>채점 실행]
        RESULT[results_ui.py<br/>결과 표시]
        PROGRESS[enhanced_progress_display.py<br/>진행률 표시]
        ERROR[error_display_ui.py<br/>오류 표시]
        STATUS[status_display_ui.py<br/>상태 표시]
    end
    
    %% Application Entry Point
    subgraph "🚀 Application Entry"
        APP[app.py<br/>메인 진입점]
        CONFIG[config.py<br/>환경설정 관리]
    end
    
    %% Core Services Layer
    subgraph "⚙️ Core Services"
        LLM[llm_service.py<br/>AI 모델 통합]
        RAG[rag_service.py<br/>문서 검색]
        GRADING[grading_engine.py<br/>채점 엔진]
        FILE[file_service.py<br/>파일 처리]
        EXPORT[export_service.py<br/>결과 내보내기]
        MSG[status_message_manager.py<br/>상태 메시지]
    end
    
    %% Data Models Layer
    subgraph "📊 Data Models"
        STUDENT[student_model.py<br/>학생 정보]
        RUBRICM[rubric_model.py<br/>루브릭 모델]
        RESULTM[result_model.py<br/>채점 결과]
        PROGRESS_M[enhanced_progress_model.py<br/>진행률 모델]
        STATUS_M[status_message_model.py<br/>상태 메시지]
    end
    
    %% Utilities Layer
    subgraph "🛠️ Utilities"
        PROMPT[prompt_utils.py<br/>프롬프트 생성]
        EMBED[embedding_utils.py<br/>임베딩 처리]
        ERR[error_handler.py<br/>오류 처리]
    end
    
    %% External Services
    subgraph "🌐 External Services"
        GEMINI[Google Gemini API<br/>멀티모달 AI]
        GROQ[Groq API<br/>고속 텍스트 AI]
        HF[HuggingFace Models<br/>임베딩 모델]
    end
    
    %% Data Storage
    subgraph "💾 Data Storage"
        FAISS[(FAISS Vector Store<br/>벡터 검색)]
        TEMP[(Temporary Files<br/>임시 파일)]
        EXCEL[(Excel Output<br/>결과 파일)]
    end
    
    %% Connections - Top to Bottom Flow
    UI --> APP
    MAIN --> APP
    RUBRIC --> APP
    EXEC --> APP
    RESULT --> APP
    PROGRESS --> APP
    ERROR --> APP
    STATUS --> APP
    
    APP --> CONFIG
    APP --> LLM
    APP --> RAG
    APP --> GRADING
    APP --> FILE
    APP --> EXPORT
    APP --> MSG
    
    LLM --> PROMPT
    LLM --> GEMINI
    LLM --> GROQ
    
    RAG --> EMBED
    RAG --> HF
    RAG --> FAISS
    
    GRADING --> STUDENT
    GRADING --> RUBRICM
    GRADING --> RESULTM
    GRADING --> PROGRESS_M
    GRADING --> STATUS_M
    
    FILE --> TEMP
    EXPORT --> EXCEL
    
    PROMPT --> ERR
    EMBED --> ERR
    
    %% Styling
    classDef frontend fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef app fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef service fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef model fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef util fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef external fill:#e0f2f1,stroke:#00695c,stroke-width:2px
    classDef storage fill:#f1f8e9,stroke:#558b2f,stroke-width:2px
    
    class UI,MAIN,RUBRIC,EXEC,RESULT,PROGRESS,ERROR,STATUS frontend
    class APP,CONFIG app
    class LLM,RAG,GRADING,FILE,EXPORT,MSG service
    class STUDENT,RUBRICM,RESULTM,PROGRESS_M,STATUS_M model
    class PROMPT,EMBED,ERR util
    class GEMINI,GROQ,HF external
    class FAISS,TEMP,EXCEL storage
```

## 2. 플랫폼 이용자 흐름

```mermaid
flowchart TD
    START([교사 접속]) --> SELECT[채점 유형 선택]
    
    SELECT --> DESC{서술형?}
    SELECT --> MAP{백지도형?}
    
    DESC -->|Yes| MODEL_D[AI 모델 선택<br/>Gemini/Groq]
    MAP -->|Yes| MODEL_M[AI 모델 선택<br/>Gemini Only]
    
    MODEL_D --> REF_UPLOAD[참고 문서 업로드<br/>PDF, DOCX]
    MODEL_M --> STUDENT_LIST[학생 목록 업로드<br/>Excel]
    
    REF_UPLOAD --> RAG_PROC[RAG 문서 처리<br/>청킹 & 임베딩]
    RAG_PROC --> STUDENT_ANS_D[학생 답안 업로드<br/>Excel - 텍스트]
    
    STUDENT_LIST --> IMAGE_UPLOAD[백지도 이미지 업로드<br/>JPG, PNG]
    
    STUDENT_ANS_D --> RUBRIC[루브릭 설정]
    IMAGE_UPLOAD --> RUBRIC
    
    RUBRIC --> ADD_ELEMENT[평가 요소 추가]
    ADD_ELEMENT --> ADD_CRITERIA[채점 기준 설정]
    ADD_CRITERIA --> MORE{더 추가?}
    MORE -->|Yes| ADD_ELEMENT
    MORE -->|No| VALIDATE[설정 검증]
    
    VALIDATE --> START_GRADING[채점 시작]
    START_GRADING --> PROGRESS[실시간 진행률 모니터링]
    
    PROGRESS --> GRADING_LOOP[순차 채점 실행]
    GRADING_LOOP --> STUDENT_DONE{완료?}
    STUDENT_DONE -->|No| NEXT_STUDENT[다음 학생]
    NEXT_STUDENT --> GRADING_LOOP
    
    STUDENT_DONE -->|Yes| RESULTS[결과 확인]
    
    RESULTS --> VIEW_MODE{보기 모드}
    VIEW_MODE --> OVERVIEW[전체 보기]
    VIEW_MODE --> INDIVIDUAL[개별 결과]
    VIEW_MODE --> ANALYTICS[통계 분석]
    
    OVERVIEW --> EXPORT[Excel 내보내기]
    INDIVIDUAL --> EXPORT
    ANALYTICS --> EXPORT
    
    EXPORT --> END([완료])
    
    style START fill:#e1f5fe
    style END fill:#c8e6c9
    style GRADING_LOOP fill:#fff3e0
    style RESULTS fill:#f3e5f5
```

## 3. 프롬프트 구성 흐름

```mermaid
flowchart TD
    START[채점 요청] --> TYPE{채점 유형}
    
    TYPE -->|서술형| DESC_FLOW[서술형 프롬프트 구성]
    TYPE -->|백지도형| MAP_FLOW[백지도형 프롬프트 구성]
    
    subgraph "서술형 프롬프트 구성"
        DESC_FLOW --> RAG_QUERY[RAG 쿼리 생성]
        RAG_QUERY --> RAG_SEARCH[벡터 검색 실행]
        RAG_SEARCH --> REF_CONTENT[참고 자료 추출]
        
        REF_CONTENT --> DESC_PROMPT[서술형 프롬프트 조립]
        RUBRIC_FORMAT --> DESC_PROMPT
        STUDENT_TEXT[학생 텍스트 답안] --> DESC_PROMPT
        
        DESC_PROMPT --> DESC_FINAL[최종 텍스트 프롬프트]
    end
    
    subgraph "백지도형 프롬프트 구성"
        MAP_FLOW --> MAP_PROMPT[백지도형 프롬프트 조립]
        RUBRIC_FORMAT --> MAP_PROMPT
        STUDENT_IMAGE[학생 이미지 답안] --> MAP_PROMPT
        
        MAP_PROMPT --> MAP_FINAL[최종 멀티모달 프롬프트]
    end
    
    subgraph "공통 구성 요소"
        RUBRIC_DATA[루브릭 데이터] --> RUBRIC_FORMAT[루브릭 포맷팅]
        OUTPUT_FORMAT[JSON 출력 형식] --> RUBRIC_FORMAT
        GRADING_INST[채점 지시사항] --> RUBRIC_FORMAT
    end
    
    DESC_FINAL --> LLM_CALL[LLM API 호출]
    MAP_FINAL --> LLM_CALL
    
    LLM_CALL --> RESPONSE[AI 응답 수신]
    RESPONSE --> PARSE[JSON 파싱]
    PARSE --> VALIDATE[응답 검증]
    
    VALIDATE --> VALID{유효한가?}
    VALID -->|No| RETRY[재시도]
    RETRY --> LLM_CALL
    
    VALID -->|Yes| RESULT[채점 결과 생성]
    
    style DESC_FLOW fill:#e3f2fd
    style MAP_FLOW fill:#fff3e0
    style LLM_CALL fill:#f3e5f5
    style RESULT fill:#c8e6c9
```

## 4. RAG 파이프라인 작동 방식

```mermaid
flowchart TD
    START[참고 문서 업로드] --> FILE_CHECK{파일 형식}
    
    FILE_CHECK -->|PDF| PDF_EXTRACT[PyPDF2로 텍스트 추출]
    FILE_CHECK -->|DOCX| DOCX_EXTRACT[python-docx로 텍스트 추출]
    FILE_CHECK -->|기타| ERROR[지원하지 않는 형식]
    
    PDF_EXTRACT --> CLEAN[텍스트 정제]
    DOCX_EXTRACT --> CLEAN
    
    CLEAN --> CHUNK[문서 청킹]
    
    subgraph "청킹 과정"
        CHUNK --> SPLIT[500토큰 단위 분할]
        SPLIT --> OVERLAP[100토큰 중복]
        OVERLAP --> CHUNK_LIST[청크 리스트 생성]
    end
    
    CHUNK_LIST --> EMBED[임베딩 생성]
    
    subgraph "임베딩 과정"
        EMBED --> MODEL[all-MiniLM-L6-v2 모델]
        MODEL --> VECTORS[벡터 변환]
        VECTORS --> NORM[벡터 정규화]
    end
    
    NORM --> FAISS_BUILD[FAISS 인덱스 구축]
    FAISS_BUILD --> STORE[벡터 저장소 저장]
    
    STORE --> READY[RAG 준비 완료]
    
    subgraph "검색 과정"
        QUERY[학생 답안 쿼리] --> QUERY_EMBED[쿼리 임베딩]
        QUERY_EMBED --> SEARCH[유사도 검색]
        SEARCH --> TOP_K[Top-3 문서 선택]
        TOP_K --> RETRIEVE[관련 내용 추출]
    end
    
    READY -.-> SEARCH
    RETRIEVE --> CONTEXT[컨텍스트 생성]
    CONTEXT --> PROMPT[프롬프트에 포함]
    
    style CHUNK fill:#e1f5fe
    style EMBED fill:#f3e5f5
    style SEARCH fill:#fff3e0
    style CONTEXT fill:#c8e6c9
```

## 5. 채점 로직

```mermaid
flowchart TD
    START[채점 시작] --> INIT[채점 엔진 초기화]
    INIT --> STUDENT_QUEUE[학생 대기열 생성]
    
    STUDENT_QUEUE --> NEXT_STUDENT[다음 학생 선택]
    NEXT_STUDENT --> TIMER_START[타이머 시작]
    
    TIMER_START --> ANSWER_TYPE{답안 유형}
    
    ANSWER_TYPE -->|텍스트| TEXT_PROCESS[텍스트 답안 처리]
    ANSWER_TYPE -->|이미지| IMAGE_PROCESS[이미지 답안 처리]
    
    subgraph "텍스트 채점 흐름"
        TEXT_PROCESS --> RAG_ENABLE{RAG 활성화?}
        RAG_ENABLE -->|Yes| RAG_SEARCH[관련 문서 검색]
        RAG_ENABLE -->|No| DIRECT_PROMPT[직접 프롬프트]
        RAG_SEARCH --> TEXT_PROMPT[텍스트 프롬프트 생성]
        DIRECT_PROMPT --> TEXT_PROMPT
        TEXT_PROMPT --> TEXT_LLM[텍스트 LLM 호출]
    end
    
    subgraph "이미지 채점 흐름"
        IMAGE_PROCESS --> IMAGE_VALID[이미지 검증]
        IMAGE_VALID --> IMAGE_ENCODE[Base64 인코딩]
        IMAGE_ENCODE --> IMAGE_PROMPT[멀티모달 프롬프트 생성]
        IMAGE_PROMPT --> IMAGE_LLM[멀티모달 LLM 호출]
    end
    
    TEXT_LLM --> RESPONSE_RECV[응답 수신]
    IMAGE_LLM --> RESPONSE_RECV
    
    RESPONSE_RECV --> JSON_PARSE[JSON 파싱]
    JSON_PARSE --> STRUCT_VALID[구조 검증]
    
    STRUCT_VALID --> VALID_CHECK{유효한가?}
    VALID_CHECK -->|No| ERROR_COUNT[오류 카운트 증가]
    ERROR_COUNT --> RETRY_CHECK{재시도 가능?}
    RETRY_CHECK -->|Yes| WAIT[대기 후 재시도]
    WAIT --> TEXT_LLM
    RETRY_CHECK -->|No| ERROR_RESULT[오류 결과 생성]
    
    VALID_CHECK -->|Yes| SCORE_EXTRACT[점수 추출]
    SCORE_EXTRACT --> FEEDBACK_EXTRACT[피드백 추출]
    FEEDBACK_EXTRACT --> REASONING_EXTRACT[판단근거 추출]
    
    REASONING_EXTRACT --> TIMER_STOP[타이머 정지]
    ERROR_RESULT --> TIMER_STOP
    
    TIMER_STOP --> RESULT_CREATE[결과 객체 생성]
    RESULT_CREATE --> PROGRESS_UPDATE[진행률 업데이트]
    
    PROGRESS_UPDATE --> MORE_STUDENTS{남은 학생?}
    MORE_STUDENTS -->|Yes| NEXT_STUDENT
    MORE_STUDENTS -->|No| GRADING_COMPLETE[채점 완료]
    
    subgraph "결과 처리"
        GRADING_COMPLETE --> STATS_CALC[통계 계산]
        STATS_CALC --> GRADE_ASSIGN[등급 부여]
        GRADE_ASSIGN --> RESULTS_READY[결과 준비 완료]
    end
    
    RESULTS_READY --> END[채점 종료]
    
    style START fill:#e1f5fe
    style TEXT_PROCESS fill:#e8f5e8
    style IMAGE_PROCESS fill:#fff3e0
    style ERROR_RESULT fill:#ffebee
    style RESULTS_READY fill:#c8e6c9
    style END fill:#4caf50
```

## 시스템 특징

### 🔧 **아키텍처 설계 원칙**
- **모듈 분리**: UI, Service, Model 계층 명확 분리
- **확장성**: 새로운 AI 모델 및 채점 유형 추가 용이
- **안정성**: 오류 처리 및 재시도 메커니즘
- **성능**: 순차 처리 및 진행률 추적

### 🚀 **핵심 기술 스택**
- **Frontend**: Streamlit (Python 웹 UI)
- **AI Models**: Google Gemini, Groq
- **Vector Search**: FAISS + HuggingFace Embeddings
- **Data Processing**: Pandas, OpenPyXL
- **Document Processing**: PyPDF2, python-docx

### 📊 **데이터 흐름**
1. **입력**: 문서 → 청킹 → 임베딩 → 벡터 저장
2. **처리**: 쿼리 → 검색 → 프롬프트 → AI 추론
3. **출력**: 결과 → 검증 → 저장 → 시각화

### 🔒 **보안 및 설정**
- **API 키 관리**: 환경변수 및 Streamlit Secrets
- **파일 처리**: 임시 파일 자동 정리
- **오류 처리**: 체계적인 예외 처리 및 로깅