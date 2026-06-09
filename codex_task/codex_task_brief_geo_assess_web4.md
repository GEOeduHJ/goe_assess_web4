# Codex Task Brief: Clean Up LLM Providers, Stabilize RAG, and Improve Grading Flow

## Repository

`GEOeduHJ/goe_assess_web4`

## Goal

Refactor the project to keep only Gemini and OpenAI GPT as LLM providers, remove obsolete Groq code, stabilize the RAG pipeline, and fix grading-flow reliability issues. The main priority is correctness and maintainability. Do not make broad UI redesigns unless needed to remove obsolete branches or fix broken behavior.

## High-Level Requirements

1. Remove all Groq-related runtime code, UI branches, configuration keys, dependency entries, and docs.
2. Keep Gemini and OpenAI GPT model support.
3. Update API key validation so the app does not require Groq and only validates the selected provider at grading time.
4. Make RAG settings actually follow `config.py` / environment values.
5. Improve RAG retrieval structure without introducing paid services.
6. Make LLM responses more reliable by using structured output where practical.
7. Fix grading-flow issues around Streamlit state, failed results, relative grades, and exported results.
8. Preserve the current user-facing workflow: select grading type, upload files, configure rubric, run grading, view/export results.

---

## Current Problems Found

### 1. Groq is still present in runtime code

Groq is hidden/commented out in part of the UI, but it still exists in:

- `config.py`
- `.env.example`
- `requirements.txt`
- `pyproject.toml`
- `services/llm_service.py`
- `services/grading_engine.py`
- `ui/main_ui.py`
- `ui/grading_execution_ui.py`
- README/reference docs if they mention Groq

This can break app startup because `Config.validate_api_keys()` still treats `GROQ_API_KEY` as required.

### 2. RAG configuration is inconsistent

`.env.example` sets:

```env
EMBEDDING_MODEL=nlpai-lab/KURE-v1
FAISS_INDEX_TYPE=IndexFlatIP
CHUNK_SIZE=300
CHUNK_OVERLAP=50
TOP_K_RETRIEVAL=3
```

But `services/rag_service.py` hardcodes:

```python
HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
```

and uses hardcoded chunk defaults:

```python
chunk_tokens: int = 500
overlap_tokens: int = 100
```

### 3. LLM JSON parsing is fragile

`parse_response()` extracts JSON by finding the first `{` and last `}`. This should be replaced or at least guarded by provider structured outputs and stricter validation.

### 4. Grading engine depends directly on Streamlit session state

`services/grading_engine.py` imports Streamlit inside the grading flow to read `reference_image_path`. Service/engine code should not read UI session state directly.

### 5. Failed grading results can disappear

When a student fails after retries, `_grade_student_with_retries()` returns `None`. The failed student may be missing from result export and summary.

### 6. Relative grade calculation is not guaranteed before export

`GradingResult.grade_letter` returns `"미정"` and relative grade is set later via `set_relative_grade()`. Export should always calculate and set relative grades before writing any sheet.

### 7. Pause/resume UI is misleading

`pause_grading()` cancels the engine, while `resume_grading()` only shows a message and does not resume from the last processed student.

---

## Implementation Tasks

## Phase 1: Remove Groq Completely

### Files to update

- `config.py`
- `.env.example`
- `requirements.txt`
- `pyproject.toml`
- `services/llm_service.py`
- `services/grading_engine.py`
- `ui/main_ui.py`
- `ui/grading_execution_ui.py`
- `app.py`
- README/reference docs if applicable

### Required changes

#### `config.py`

Remove:

```python
GROQ_API_KEY
```

Change `validate_api_keys()` behavior.

Current behavior requires Google and Groq. Replace it with a provider-aware validation API:

```python
@classmethod
def validate_available_api_keys(cls) -> dict:
    available = {
        "gemini": bool(cls.GOOGLE_API_KEY),
        "gpt-5-mini": bool(cls.OPENAI_API_KEY),
    }
    return {
        "valid": any(available.values()),
        "available": available,
        "missing_keys": [
            key for key, ok in {
                "GOOGLE_API_KEY": bool(cls.GOOGLE_API_KEY),
                "OPENAI_API_KEY": bool(cls.OPENAI_API_KEY),
            }.items()
            if not ok
        ],
    }

@classmethod
def validate_model_api_key(cls, model_type: str) -> dict:
    required = {
        "gemini": ("GOOGLE_API_KEY", cls.GOOGLE_API_KEY),
        "gpt-5-mini": ("OPENAI_API_KEY", cls.OPENAI_API_KEY),
    }
    if model_type not in required:
        return {
            "valid": False,
            "missing_keys": [],
            "message": f"Unsupported model type: {model_type}",
        }

    key_name, value = required[model_type]
    return {
        "valid": bool(value),
        "missing_keys": [] if value else [key_name],
    }
```

Keep backward compatibility only if needed, but do not require Groq anywhere.

#### `app.py`

Change startup validation:

- Do not block app startup if Groq is missing.
- Allow app startup if at least one supported API key exists.
- Show warnings for missing Gemini/OpenAI keys, but only block when no supported key exists.

Update the API key help text to show only:

```env
GOOGLE_API_KEY=...
OPENAI_API_KEY=...
```

#### `services/llm_service.py`

Remove all Groq code:

- `import groq._base_client`
- Groq monkey patch
- `from groq import Groq`
- `self.groq_client`
- `LLMModelType.GROQ`
- Groq client initialization
- `get_selected_groq_model()`
- `call_groq_api()`
- Groq fallback logic in `select_model()`
- Groq branch in `grade_student_sequential()`
- Groq entry in `validate_api_availability()`

Expected model enum:

```python
class LLMModelType:
    GEMINI = "gemini"
    GPT5_MINI = "gpt-5-mini"
```

Expected selection behavior:

```python
def select_model(self, model_type: str, grading_type: str) -> str:
    if model_type == LLMModelType.GEMINI and config.GOOGLE_API_KEY:
        return LLMModelType.GEMINI

    if model_type == LLMModelType.GPT5_MINI and self.openai_client:
        return LLMModelType.GPT5_MINI

    if config.GOOGLE_API_KEY:
        return LLMModelType.GEMINI

    if self.openai_client:
        return LLMModelType.GPT5_MINI

    raise ValueError("No supported LLM models available. Configure GOOGLE_API_KEY or OPENAI_API_KEY.")
```

For map grading, both Gemini and GPT-5-mini can remain available if their clients exist.

#### `services/grading_engine.py`

Remove all `groq_model_name` parameters and pass-through arguments.

Update method signatures:

```python
grade_students_sequential(..., reference_image_path: Optional[str] = None)
_grade_student_with_retries(..., reference_image_path: Optional[str] = None)
retry_failed_students(..., reference_image_path: Optional[str] = None)
```

Do not import or read `streamlit` inside this service. Pass `reference_image_path` from UI to engine explicitly.

#### `ui/main_ui.py`

Remove:

- `LLMModel.GROQ`
- Groq display names
- Groq model detail selectbox
- `selected_groq_model` session state usage
- Groq status text in requirements summary

Model options should only include:

```python
{
    "gemini": {
        "name": "Google Gemini 2.5 Flash",
        "description": "...",
        "icon": "🔥",
    },
    "gpt-5-mini": {
        "name": "OpenAI GPT-5 Mini",
        "description": "...",
        "icon": "⚡",
    },
}
```

#### `ui/grading_execution_ui.py`

Remove:

- `groq_model` from `GradingSession`
- Groq display branch
- `switch_model_and_retry()` switching Gemini to Groq
- `selected_groq_model` usage
- `groq_model_name` local variables
- `groq_model` function arguments

Update alternative retry behavior:

- If current model is Gemini and OpenAI key exists, switch to `gpt-5-mini`.
- If current model is GPT and Gemini key exists, switch to `gemini`.
- If no alternative configured, show a clear warning.

#### Dependencies

Remove from both `requirements.txt` and `pyproject.toml`:

```text
groq
```

Update `.env.example`:

```env
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

Remove all Groq comments.

---

## Phase 2: Stabilize Gemini/OpenAI LLM Calls

### Gemini SDK

Replace legacy `google-generativeai` with `google-genai` if feasible.

Update dependencies:

```text
google-genai
```

Remove:

```text
google-generativeai
```

If this migration is too large for one PR, leave a TODO and keep current SDK for now, but still remove Groq.

### Structured output

Add Pydantic response models, for example in `models/grading_response_model.py` or inside `services/llm_service.py`:

```python
from pydantic import BaseModel, Field
from typing import List

class ElementGrade(BaseModel):
    element_name: str
    score: int
    reasoning: str

class GradeResponse(BaseModel):
    scores: List[ElementGrade]
    feedback: str
```

Do not trust model-generated `total_score`. Compute totals from element scores.

Expected behavior:

- Gemini call should request JSON/structured output if the selected SDK supports it.
- OpenAI call should use structured output if feasible.
- `parse_response()` may remain as fallback, but primary path should return validated structured data.

Validation rules:

1. Every rubric element must have exactly one score.
2. Score must be one of the allowed rubric criterion scores.
3. Missing reasoning should be filled with a default Korean message.
4. Invalid output should trigger retry or repair once before returning failure.

### Temperature

Change Gemini generation config:

```python
temperature=0.0
```

or at most:

```python
temperature=0.1
```

Current `temperature=1` conflicts with the comment about consistent grading.

### Logging

Remove full prompt logging from production path.

Replace:

```python
logger.info(final_prompt)
```

with:

```python
logger.debug("Generated grading prompt: length=%s, rubric_elements=%s, references=%s", ...)
```

Do not log student answers, full references, or image paths at info level.

---

## Phase 3: Fix RAG Configuration and Retrieval

### Files to update

- `services/rag_service.py`
- `config.py`
- `.env.example`
- optionally add `services/document_loader.py`
- optionally add `services/hybrid_retriever.py`

### Required changes in `RAGService`

Use config values:

```python
from config import config

self.embeddings = HuggingFaceEmbeddings(
    model_name=config.EMBEDDING_MODEL,
    encode_kwargs={
        "normalize_embeddings": True,
        "batch_size": config.EMBEDDING_BATCH_SIZE,
    },
)
```

Use config for chunking and retrieval:

```python
chunks = self._chunk_document(
    content,
    chunk_tokens=config.CHUNK_SIZE,
    overlap_tokens=config.CHUNK_OVERLAP,
)

relevant_content = self.search_relevant_content(
    student_answer,
    k=config.TOP_K_RETRIEVAL,
)
```

### Fix `.env.example`

Choose one default and keep it consistent. Prefer one of:

#### Faster default

```env
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

#### Korean quality default

```env
EMBEDDING_MODEL=nlpai-lab/KURE-v1
```

If using Korean quality default, ensure it actually loads in the target deployment environment.

### Improve metadata

When building chunks, preserve:

```python
metadata={
    "source": file_obj.name,
    "chunk_id": i,
}
```

If page number or document section can be extracted, include:

```python
"page": page_number
"section": section_name
```

### Avoid aggressive text cleaning

Current `clean_text()` removes many symbols. Make it less destructive.

Requirements:

- Keep arrows, slash, percent, degree, parentheses, brackets, colons, semicolons.
- Do not remove table separators that may help geography explanations.
- Normalize whitespace, but avoid deleting meaningful characters.

### Optional hybrid retrieval

Add BM25 only if the change remains simple and low-risk.

Recommended library:

```text
bm25s
```

Proposed retrieval:

```text
dense_top = FAISS top 8
sparse_top = BM25 top 8
merged = reciprocal rank fusion
final = top config.TOP_K_RETRIEVAL
```

Do not add a heavy vector database unless needed. FAISS is fine for uploaded reference documents.

### Optional query improvement

Instead of using only the raw student answer, query per rubric element:

```python
query = f"{rubric_element.name}\n{criteria_descriptions}\nStudent answer: {student.answer}"
```

If this is too large for one PR, keep current student-answer query but add TODO.

---

## Phase 4: Fix Grading Flow Reliability

### Remove service-layer Streamlit dependency

In `services/grading_engine.py`, remove:

```python
import streamlit as st
reference_image_path = st.session_state.get(...)
```

Pass `reference_image_path` from `ui/grading_execution_ui.py` to engine.

### Failed results should be retained

When all retries fail, return a `GradingResult` with explicit failure information instead of `None`.

Example:

```python
result = GradingResult(
    student_name=student.name,
    student_class_number=student.class_number,
    original_answer=student.answer or student.image_path or "",
    grading_time_seconds=elapsed_time,
    overall_feedback=f"채점 중 오류가 발생했습니다: {error_message}",
)
for element in rubric.elements:
    result.add_element_score(
        element_name=element.name,
        score=0,
        max_score=element.max_score,
        feedback="채점 오류로 인해 점수를 부여할 수 없습니다.",
        reasoning="채점 처리 중 오류 발생",
    )
```

Add a field only if model changes are acceptable:

```python
status: str = "success" | "failed"
error_message: str = ""
```

If not adding fields, preserve failure in `overall_feedback`.

### Store original answer

When creating `GradingResult`, set:

```python
original_answer=student.answer if grading_type == GradingType.DESCRIPTIVE else (student.image_path or "")
```

### Relative grades before export

In `ExportService.create_results_excel()`, before creating sheets:

```python
grade_mapping = GradingResult.calculate_relative_grades(results)
for result in results:
    key = f"{result.student_name}_{result.student_class_number}"
    if key in grade_mapping:
        result.set_relative_grade(grade_mapping[key])
```

Then use:

```python
result.get_relative_grade()
```

instead of direct `_relative_grade` access.

### Pause/resume behavior

Current pause/resume is misleading.

Choose one:

#### Option A: Remove pause/resume for now

Keep only:

- Start grading
- Stop grading
- Retry failed students

This is preferred for a simple reliable PR.

#### Option B: Implement real resume

Track processed student index and resume from remaining students.

Do not keep the current fake resume behavior.

### Thread/state cleanup

Ensure:

- `grading_completed` is reset when starting a new grading session.
- previous queues are cleared when starting fresh.
- temporary image/reference files are cleaned after completion or stop.

---

## Phase 5: Tests and Validation

Add or update tests if test infrastructure exists.

Minimum manual checks:

1. App starts with only `GOOGLE_API_KEY`.
2. App starts with only `OPENAI_API_KEY`.
3. App shows a clear error if no supported API key exists.
4. Groq is not mentioned in app UI, `.env.example`, dependencies, or runtime logs.
5. Text grading works with Gemini.
6. Text grading works with GPT.
7. Map grading works with Gemini if image inputs exist.
8. Map grading works with GPT if image inputs exist.
9. RAG uses `config.EMBEDDING_MODEL`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, and `TOP_K_RETRIEVAL`.
10. Failed student grading appears in result summary and Excel export.
11. Excel export always includes relative grades.
12. No full student answer or full prompt is logged at info level.

Useful commands:

```bash
grep -R "groq\|Groq\|GROQ" .
grep -R "selected_groq_model\|groq_model" .
python -m compileall .
pytest
```

If no tests exist, at least run:

```bash
python -m compileall .
```

---

## Acceptance Criteria

The PR is acceptable when all of the following are true:

- No runtime Groq dependency remains.
- `requirements.txt` and `pyproject.toml` no longer include `groq`.
- `.env.example` only documents Gemini/OpenAI provider keys.
- App startup no longer requires Groq.
- Selected model validation works for Gemini and GPT only.
- RAG uses configurable embedding model, chunk size, overlap, top-k, and batch size.
- Full prompts/student answers are not logged at info level.
- Failed grading attempts are represented in final results instead of silently disappearing.
- Exported Excel files include computed relative grades.
- Service layer no longer reads `st.session_state` directly.
- Pause/resume is either removed or implemented correctly.
- Existing core workflow remains usable.
