# Design Document

## Overview

This design simplifies the RAG system by replacing the custom FAISS implementation with LangChain's standard FAISS vector store. The new design focuses on minimal code changes while fixing the core issues: proper LangChain integration and RAG content reaching LLM prompts.

## Architecture

```
Uploaded Files → Document Processing → LangChain FAISS → Similarity Search → LLM Prompt
```

### Key Changes
- Replace custom FAISS with `langchain_community.vectorstores.FAISS`
- Use `HuggingFaceEmbeddings` instead of direct SentenceTransformer
- Simplify document processing to create LangChain Document objects
- Fix RAG content integration in grading pipeline

## Components and Interfaces

### RAGService (Simplified)
```python
class RAGService:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vector_store = None
    
    def process_documents(self, uploaded_files) -> bool
    def search_relevant_content(self, query: str, k: int = 3) -> List[str]
```

### Document Processing
- Extract text from PDF/DOCX files
- Create simple text chunks (500 chars with 50 char overlap)
- Convert to LangChain Document objects with metadata
- Build FAISS vector store using `FAISS.from_documents()`

### Integration Points
- `grading_engine.py`: Call RAG service before LLM grading
- `llm_service.py`: Include RAG content in prompt generation

## Data Models

### Document Structure
```python
Document(
    page_content="text chunk",
    metadata={"source": "filename.pdf", "chunk_id": 0}
)
```

### RAG Response
```python
List[str]  # Simple list of relevant text chunks
```

## Error Handling

- **File Processing Errors**: Skip problematic files, continue with others
- **Embedding Errors**: Fall back to grading without RAG
- **Search Errors**: Return empty results, continue grading
- **Memory Issues**: Use smaller chunk sizes, limit document count

## Testing Strategy

1. **Unit Tests**: Test document processing with sample PDF/DOCX files
2. **Integration Tests**: Test RAG content appearing in LLM prompts
3. **Error Tests**: Test graceful handling when RAG fails
4. **Performance Tests**: Ensure processing time is reasonable for typical document sets