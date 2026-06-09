# Codex 작업 지시서: Google GenAI SDK 마이그레이션 및 의존성 정리

## 0. 작업 원칙

이 저장소는 `GEOeduHJ/goe_assess_web4`입니다.
현재 main에 직접 반영된 일부 안정화 커밋이 있으나, 아직 `services/llm_service.py`, 의존성 파일, `ui/grading_execution_ui.py`에 후속 정리가 필요합니다.

이번 작업의 핵심 목표는 다음입니다.

1. Google Gemini 연동을 legacy `google-generativeai` SDK에서 최신 `google-genai` SDK로 이전한다.
2. 의존성 파일(`requirements.txt`, `pyproject.toml`)을 실제 사용 코드와 일치시킨다.
3. LLM 응답 검증을 이미 추가된 `models/grading_response_model.py`와 연결한다.
4. `GradingResult` 생성 시 `original_answer`, `status`, `error_message`를 일관되게 채운다.
5. 디버그 출력은 제거하지 않는다. 개발자가 로컬 실행 중 문제를 직접 확인해야 하므로 `print("DEBUG...")` 계열은 유지해도 된다.
6. 단, 존재하지 않는 enum, 깨지는 import, legacy/new SDK 혼재 등 실제 런타임 오류는 반드시 제거한다.

중요: 이 작업에서는 “디버그 출력 제거”를 목표로 삼지 말 것. 디버그 출력은 개발/검증용으로 유지한다.

---

## 1. 현재 확인된 상태

### 1.1 `requirements.txt` 현재 문제

현재 `requirements.txt`에는 legacy와 신규 의존성이 동시에 존재한다.

```txt
streamlit>=1.49.1
google-generativeai>=0.8.5
google-genai
openai>=2.6.0
pydantic>=2
...
pypdf2>=3.0.1
pypdf
```

최종 목표는 코드 마이그레이션 완료 후 다음과 같이 정리하는 것이다.

```txt
google-genai
# google-generativeai 제거

pypdf
# pypdf2 제거, 단 실제 사용처가 없을 때만 제거
```

단, `google-generativeai`는 `llm_service.py` 마이그레이션이 끝난 뒤 제거해야 한다. 먼저 제거하면 현재 import에서 앱이 깨진다.

### 1.2 Google 공식 문서 기준

Google 공식 문서에 따르면 Gemini API 개발에는 Google GenAI SDK 사용이 권장된다.
Python 설치 패키지는 다음이다.

```bash
pip install google-genai
```

legacy Python 라이브러리 `google-generativeai`는 not actively maintained로 분류되므로, `google-genai`로 이전해야 한다.

참고 문서:

- https://ai.google.dev/gemini-api/docs/libraries
- https://ai.google.dev/gemini-api/docs/migrate

---

## 2. 반드시 지켜야 할 금지사항

다음은 하지 말 것.

1. 디버그 출력을 전면 제거하지 말 것.
2. `print("DEBUG...")`를 없애는 것을 작업 목표로 삼지 말 것.
3. SDK 마이그레이션 전에 `google-generativeai` 의존성을 먼저 제거하지 말 것.
4. 실제 테스트 없이 `google-generativeai`와 `pypdf2`를 무조건 삭제하지 말 것.
5. LLM이 반환하는 `total_score`를 신뢰하지 말 것.
6. 큰 파일 전체를 무리하게 한 번에 갈아엎지 말 것.
7. UI 디버그 출력 정리보다 LLM/의존성/런타임 오류 수정을 우선할 것.

---

## 3. 커밋 단위 권장 순서

한 번에 많이 바꾸지 말고 아래 순서대로 작은 커밋을 만든다.

---

## Commit 1: `llm_service.py`의 존재하지 않는 `ErrorType` 참조 수정

### 목적

현재 `services/llm_service.py`에는 실제 enum에 없는 `ErrorType` 값이 사용될 가능성이 있다. 특정 오류 상황에서 `AttributeError`가 발생할 수 있으므로 먼저 고친다.

### 작업

`utils/error_handler.py`의 실제 `ErrorType` enum을 확인한 뒤, `llm_service.py`의 존재하지 않는 enum 참조를 교체한다.

권장 매핑:

```python
ErrorType.CONFIGURATION -> ErrorType.AUTHENTICATION 또는 ErrorType.SYSTEM
ErrorType.FILE_OPERATION -> ErrorType.FILE_PROCESSING
ErrorType.TIMEOUT -> ErrorType.NETWORK
```

### 완료 기준

다음 검색 결과가 없어야 한다.

```bash
grep -R "ErrorType.CONFIGURATION\|ErrorType.FILE_OPERATION\|ErrorType.TIMEOUT" -n .
```

### 검증

```bash
python -m compileall .
```

---

## Commit 2: Google Gemini 연동을 `google-genai` SDK로 마이그레이션

### 목적

`services/llm_service.py`의 legacy Gemini SDK 사용을 최신 Google GenAI SDK로 교체한다.

### 현재 형태

현재 코드에 다음 형태가 남아 있다.

```python
import google.generativeai as genai

genai.configure(api_key=config.GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content(...)
```

### 목표 형태

다음 구조로 변경한다.

```python
from google import genai
from google.genai import types

self.gemini_client = genai.Client(api_key=config.GOOGLE_API_KEY)

response = self.gemini_client.models.generate_content(
    model=config.GEMINI_MODEL,
    contents=contents,
    config=types.GenerateContentConfig(
        temperature=0.0,
        response_mime_type="application/json",
        # 가능하면 response_schema 사용
    ),
)
```

### 구체 작업

1. `import google.generativeai as genai` 제거.
2. `from google import genai` 추가.
3. 필요한 경우 `from google.genai import types` 추가.
4. `__init__` 또는 `_initialize_clients()`에서 `self.gemini_client`를 초기화한다.
5. `genai.configure(...)` 제거.
6. `genai.GenerativeModel(...)` 제거.
7. `call_gemini_api()`에서 `self.gemini_client.models.generate_content(...)`를 사용한다.
8. 텍스트 채점과 이미지 채점 모두 동작하도록 `contents` 구성 로직을 갱신한다.
9. 기존 디버그 출력은 제거하지 않아도 된다. 필요하면 SDK 마이그레이션 상태를 확인할 수 있는 디버그를 추가해도 된다.

### 이미지 입력 처리 참고

Google GenAI SDK 문서에서는 Python에서 이미지 입력 시 PIL Image 객체 사용 예시를 제공한다.
다만 현재 앱은 이미지 파일 경로를 사용하므로 다음 중 하나로 구현한다.

선택지 A: PIL 사용

```python
from PIL import Image

contents = [prompt, Image.open(reference_image_path), Image.open(student_image_path)]
```

선택지 B: bytes/Part 사용

```python
from google.genai import types

part = types.Part.from_bytes(
    data=image_bytes,
    mime_type=mime_type,
)
```

PIL을 사용할 경우 `Pillow` 의존성이 필요하다. 현재 `sentence-transformers` 계열에서 간접 설치될 수 있지만, 명시성을 위해 필요하면 `Pillow`를 requirements/pyproject에 추가한다.

### 완료 기준

다음 검색 결과가 없어야 한다.

```bash
grep -R "google.generativeai\|genai.configure\|GenerativeModel" -n services/llm_service.py requirements.txt pyproject.toml
```

단, 마이그레이션 완료 전 중간 커밋에서는 `requirements.txt`에 `google-generativeai`가 잠깐 남아 있어도 된다. 이 커밋 끝에서는 코드 사용처가 없어져야 한다.

### 검증

```bash
python -m compileall .
python - <<'PY'
from services.llm_service import LLMService
svc = LLMService()
print(svc.validate_api_availability())
PY
```

---

## Commit 3: structured output 검증 연결

### 목적

이미 추가된 `models/grading_response_model.py`를 실제 `llm_service.py` 파싱 흐름에 연결한다.

### 현재 문제

현재 `parse_response()`는 다음 문제가 있다.

1. `scores`, `reasoning`, `feedback`, `total_score`를 필수로 요구한다.
2. 잘못된 루브릭 점수를 warning만 하고 통과시킬 수 있다.
3. 새로 추가된 `GradeResponse`, `normalize_raw_response`, `validate_against_rubric`를 실제로 사용하지 않는다.

### 작업

`services/llm_service.py`에 다음 import를 추가한다.

```python
from models.grading_response_model import normalize_raw_response, validate_against_rubric
```

`parse_response()`는 다음 흐름으로 정리한다.

```python
def parse_response(self, response_text: str, rubric: Rubric) -> Dict[str, Any]:
    print(f"DEBUG: API Response (length: {len(response_text)})")
    print(f"DEBUG: API Response content: {repr(response_text)}")

    parsed = self._extract_json_object(response_text)
    if parsed is None:
        raise ValueError("No JSON found in response")

    structured = normalize_raw_response(parsed)
    return validate_against_rubric(structured, rubric)
```

주의:

- 디버그 출력은 유지한다.
- `total_score`는 필수 필드에서 제거한다.
- 루브릭에 없는 평가요소, 누락된 평가요소, 허용되지 않은 점수는 실패 처리한다.
- 기존 legacy 응답 형태 `{scores, reasoning, feedback}`도 `normalize_raw_response()`가 처리할 수 있어야 한다.

### 완료 기준

1. `parse_response()`가 `normalize_raw_response()`를 호출한다.
2. `parse_response()`가 `validate_against_rubric()`를 호출한다.
3. `required_fields = ['scores', 'reasoning', 'feedback', 'total_score']` 같은 코드는 제거된다.
4. 잘못된 점수에 대해 warning만 하고 통과시키는 코드가 제거된다.

### 검증

간단한 단위 스크립트를 작성하거나 REPL로 다음을 확인한다.

```python
from services.llm_service import LLMService
from models.rubric_model import Rubric, RubricElement, ScoringCriteria

rubric = Rubric(
    name="test",
    elements=[
        RubricElement(
            name="개념 이해",
            max_score=2,
            criteria=[
                ScoringCriteria(score=0, description="부족"),
                ScoringCriteria(score=1, description="부분"),
                ScoringCriteria(score=2, description="충분"),
            ],
        )
    ],
)

svc = LLMService()
parsed = svc.parse_response('{"scores":{"개념 이해":2},"reasoning":{"개념 이해":"충분함"},"feedback":"좋음"}', rubric)
print(parsed)
```

---

## Commit 4: `GradingResult` 생성 일관화

### 목적

`models/result_model.py`에는 이미 `original_answer`, `status`, `error_message`가 있으므로, `llm_service.py`에서 결과를 만들 때 이를 항상 채운다.

### 작업

`grade_student_sequential()`에서 먼저 원본 답안을 정한다.

```python
original_answer = student.answer if grading_type == GradingType.DESCRIPTIVE else (student.image_path or "")
```

성공 결과:

```python
result = GradingResult(
    student_name=student.name,
    student_class_number=student.class_number,
    original_answer=original_answer,
    grading_time_seconds=elapsed_time,
    overall_feedback=parsed_result["feedback"],
    status="success",
)
```

실패 결과:

```python
result = GradingResult(
    student_name=student.name,
    student_class_number=student.class_number,
    original_answer=original_answer,
    grading_time_seconds=elapsed_time,
    overall_feedback=f"채점 중 오류가 발생했습니다: {str(e)}",
    status="failed",
    error_message=str(e),
)
```

### 완료 기준

1. 성공 결과에 `original_answer`와 `status="success"`가 명시된다.
2. 실패 결과에 `original_answer`, `status="failed"`, `error_message`가 명시된다.
3. 기존 `GradingEngine._is_success_result()` 방어 로직과 충돌하지 않는다.

### 검증

```bash
python -m compileall .
```

---

## Commit 5: 의존성 파일 정리

### 목적

코드 마이그레이션 후 `requirements.txt`와 `pyproject.toml`을 실제 사용 코드와 일치시킨다.

### 작업 순서

1. `google-generativeai` 사용처 검색.

```bash
grep -R "google.generativeai\|google-generativeai\|GenerativeModel\|genai.configure" -n .
```

2. 코드 사용처가 없으면 `requirements.txt`, `pyproject.toml`에서 `google-generativeai` 제거.
3. `PyPDF2` 사용처 검색.

```bash
grep -R "PyPDF2\|pypdf2" -n .
```

4. 사용처가 없으면 `requirements.txt`, `pyproject.toml`에서 `pypdf2` 제거.
5. `pypdf`는 유지한다.
6. `google-genai`는 유지한다.
7. `pydantic>=2`는 `models/grading_response_model.py` 때문에 유지한다.
8. `requirements.txt`와 `pyproject.toml` dependency 목록을 동기화한다.

### 예상 최종 requirements.txt 예시

```txt
streamlit>=1.49.1
google-genai
openai>=2.6.0
pydantic>=2
pandas>=2.3.2
openpyxl>=3.1.5
python-docx>=1.2.0
pypdf
plotly>=5.17.0
python-dotenv>=1.1.1

# RAG 및 임베딩 관련
langchain-community>=0.3.0
langchain-huggingface>=0.1.0
sentence-transformers>=5.1.0
faiss-cpu>=1.12.0
tiktoken>=0.8.0
```

PIL Image 방식으로 Gemini 이미지 입력을 구현했다면 아래도 명시 추가한다.

```txt
Pillow>=10.0.0
```

### 검증

새 가상환경 기준으로 테스트한다.

```bash
python -m venv .venv-test
source .venv-test/bin/activate  # Windows는 .venv-test\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
python -m compileall .
```

---

## Commit 6: `grading_execution_ui.py` 상태관리 보강

### 목적

Streamlit rerun 중 `SequentialGradingEngine` 인스턴스를 잃지 않게 한다.
디버그 출력은 유지해도 된다.

### 현재 문제

`GradingExecutionUI.__init__()`에서 매번 다음이 실행된다.

```python
self.grading_engine = None
```

Streamlit은 rerun마다 UI 객체를 다시 만들 수 있으므로 엔진은 `st.session_state`에 저장해야 한다.

### 작업

1. `initialize_session_state()`에 `grading_engine` 기본값을 추가한다.

```python
if 'grading_engine' not in st.session_state:
    st.session_state.grading_engine = None
```

2. `__init__()`에서 다음처럼 연결한다.

```python
self.grading_engine = st.session_state.get('grading_engine')
```

3. `start_grading()`에서 엔진 생성 후 저장한다.

```python
self.grading_engine = SequentialGradingEngine()
st.session_state.grading_engine = self.grading_engine
```

4. `pause_grading()`, `stop_grading()`, `retry_failed_students()`는 `self.grading_engine`만 믿지 말고 `st.session_state.get('grading_engine')`를 우선 사용한다.

5. `start_grading()` 시작 시 queue와 상태를 초기화한다.

```python
st.session_state.student_results = []
st.session_state.grading_progress = None
st.session_state.grading_errors = []
st.session_state.grading_completed = False
st.session_state.completed_count = 0
```

6. retry 결과는 append만 하지 말고 `(student_name, student_class_number)` 기준으로 기존 결과를 replace한다.

### 완료 기준

1. `grading_engine`이 `st.session_state`에 저장된다.
2. stop/retry가 rerun 후에도 엔진을 찾을 수 있다.
3. retry 성공 시 같은 학생 결과가 중복 append되지 않는다.
4. 디버그 출력은 유지해도 된다.

### 검증

```bash
python -m compileall .
streamlit run app.py
```

수동 확인:

1. 채점 시작 버튼 클릭.
2. 진행 중 rerun이 발생해도 세션이 유지되는지 확인.
3. 현재 학생 후 정지 버튼이 동작하는지 확인.
4. 실패 재시도 시 결과가 중복되지 않는지 확인.

---

## Commit 7: 로컬 실행 검증 문서 또는 스크립트 추가 선택 사항

필수는 아니지만, 개발자가 쉽게 테스트하도록 `scripts/setup_local.ps1`, `scripts/setup_local.sh` 또는 README 섹션을 추가해도 된다.

Windows PowerShell 예시:

```powershell
git clone https://github.com/GEOeduHJ/goe_assess_web4.git
cd goe_assess_web4
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
copy .env.example .env
notepad .env
python -m compileall .
streamlit run app.py
```

macOS/Linux 예시:

```bash
git clone https://github.com/GEOeduHJ/goe_assess_web4.git
cd goe_assess_web4
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
cp .env.example .env
${EDITOR:-nano} .env
python -m compileall .
streamlit run app.py
```

---

## 4. 최종 검증 체크리스트

Codex는 작업 완료 전 아래를 모두 실행하고 결과를 보고할 것.

```bash
python -m compileall .
```

가능하면 새 venv에서:

```bash
python -m venv .venv-test
source .venv-test/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
python -m compileall .
```

검색 검증:

```bash
grep -R "google.generativeai\|google-generativeai\|GenerativeModel\|genai.configure" -n .
grep -R "PyPDF2\|pypdf2" -n .
grep -R "ErrorType.CONFIGURATION\|ErrorType.FILE_OPERATION\|ErrorType.TIMEOUT" -n .
```

기대 결과:

1. Google legacy SDK 검색 결과 없음.
2. PyPDF2/pypdf2 검색 결과 없음. 단 과거 문서나 task 파일에만 남아 있으면 삭제하거나 명시적으로 무시.
3. 존재하지 않는 ErrorType 검색 결과 없음.
4. `python -m compileall .` 성공.
5. `streamlit run app.py`로 UI 시작 가능.

---

## 5. 완료 보고 형식

Codex는 완료 후 다음 형식으로 보고할 것.

```md
## 완료 요약
- 커밋 1: <sha> <message>
- 커밋 2: <sha> <message>
...

## 변경 파일
- services/llm_service.py
- requirements.txt
- pyproject.toml
- ui/grading_execution_ui.py
...

## 검증 결과
- python -m compileall .: 성공/실패
- pip install -r requirements.txt: 성공/실패
- legacy google SDK 검색: 결과 없음/있음
- pypdf2 검색: 결과 없음/있음
- streamlit run app.py: 실행 확인/미확인

## 남은 이슈
- 있으면 작성
- 없으면 "없음"
```

---

## 6. 핵심 요약

이번 작업의 가장 중요한 결론은 다음이다.

```text
디버그 출력은 유지한다.
우선순위는 Google GenAI SDK 마이그레이션과 의존성 정리다.
그 다음 structured output 검증과 GradingResult 생성 일관화를 완료한다.
마지막으로 Streamlit 실행 상태관리를 보강한다.
```
