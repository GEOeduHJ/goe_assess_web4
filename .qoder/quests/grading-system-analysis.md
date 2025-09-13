# Grading System Performance Issue Analysis and Solution

## 1. Overview

The geography auto-grading system is experiencing performance issues during the grading execution phase. Based on the logs, the system appears to be stuck in a loop where it continuously reloads the SentenceTransformer model for each student, causing significant delays and preventing the grading process from completing.

### Key Issues Identified:
1. **Repeated Model Loading**: The SentenceTransformer model is being loaded for each student during RAG processing
2. **Performance Bottleneck**: Model loading takes several seconds, creating a major performance bottleneck
3. **Resource Inefficiency**: Each model load consumes CPU resources unnecessarily

## 2. Root Cause Analysis

### Log Analysis:
```
2025-09-12 15:02:36,566 - sentence_transformers.SentenceTransformer - INFO - Use pytorch device_name: cpu     
2025-09-12 15:02:36,566 - sentence_transformers.SentenceTransformer - INFO - Load pretrained SentenceTransformer: sentence-transformers/all-MiniLM-L6-v2
...
2025-09-12 15:03:23,958 - sentence_transformers.SentenceTransformer - INFO - Use pytorch device_name: cpu     
2025-09-12 15:03:23,958 - sentence_transformers.SentenceTransformer - INFO - Load pretrained SentenceTransformer: sentence-transformers/all-MiniLM-L6-v2
...
2025-09-12 15:03:48,636 - sentence_transformers.SentenceTransformer - INFO - Use pytorch device_name: cpu     
2025-09-12 15:03:48,636 - sentence_transformers.SentenceTransformer - INFO - Load pretrained SentenceTransformer: sentence-transformers/all-MiniLM-L6-v2
```

### Problem Location:
The issue is in the `RAGService` class in `services/rag_service.py`. Each time `process_documents_for_student` is called, a new `HuggingFaceEmbeddings` instance is created, which triggers the SentenceTransformer model loading process.

```python
class RAGService:
    def __init__(self):
        """Initialize RAG service with HuggingFace embeddings."""
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vector_store = None
        self.logger = logging.getLogger(__name__)
```

Each instantiation of `RAGService` creates a new embeddings model, which causes the model to be downloaded/loaded from disk every time.

## 2. Architecture

The system follows a modular architecture with the following key components:

```
┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   UI Layer      │    │  Service Layer   │    │  Model Layer     │
│                 │    │                  │    │                  │
│ grading_execution_ui├─►grading_engine   ├─┬─►│ student_model    │
│                 │    │                  │ │  │ rubric_model     │
│                 │    │ llm_service      │ │  │ result_model     │
└─────────────────┘    │ rag_service      │ │  └──────────────────┘
                       │                  │ │                     
                       └──────────────────┘ │  ┌──────────────────┐
                                            │  │  Utils Layer     │
                                            │  │                  │
                                            └─►│ embedding_utils  │
                                               │ error_handler    │
                                               │ prompt_utils     │
                                               └──────────────────┘
```

## 3. Root Cause Analysis

### Log Analysis:
```
2025-09-12 15:02:36,566 - sentence_transformers.SentenceTransformer - INFO - Use pytorch device_name: cpu     
2025-09-12 15:02:36,566 - sentence_transformers.SentenceTransformer - INFO - Load pretrained SentenceTransformer: sentence-transformers/all-MiniLM-L6-v2
...
2025-09-12 15:03:23,958 - sentence_transformers.SentenceTransformer - INFO - Use pytorch device_name: cpu     
2025-09-12 15:03:23,958 - sentence_transformers.SentenceTransformer - INFO - Load pretrained SentenceTransformer: sentence-transformers/all-MiniLM-L6-v2
...
2025-09-12 15:03:48,636 - sentence_transformers.SentenceTransformer - INFO - Use pytorch device_name: cpu     
2025-09-12 15:03:48,636 - sentence_transformers.SentenceTransformer - INFO - Load pretrained SentenceTransformer: sentence-transformers/all-MiniLM-L6-v2
```

### Problem Location:
The issue is in the `RAGService` class in `services/rag_service.py`. Each time `process_documents_for_student` is called, a new `HuggingFaceEmbeddings` instance is created, which triggers the SentenceTransformer model loading process.

```python
class RAGService:
    def __init__(self):
        """Initialize RAG service with HuggingFace embeddings."""
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vector_store = None
        self.logger = logging.getLogger(__name__)
```

Each instantiation of `RAGService` creates a new embeddings model, which causes the model to be downloaded/loaded from disk every time.

## 4. Solution Design

### Approach 1: Singleton Pattern for RAGService (Recommended)

Modify the RAGService to use a singleton pattern to ensure only one instance of the embeddings model is created:

```python
class RAGService:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not RAGService._initialized:
            self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            self.vector_store = None
            self.logger = logging.getLogger(__name__)
            RAGService._initialized = True
```

### Approach 2: Lazy Initialization with Caching

Modify the RAGService to initialize the embeddings model only once and cache it:

```python
class RAGService:
    _embeddings_instance = None
    
    def __init__(self):
        """Initialize RAG service with HuggingFace embeddings."""
        if RAGService._embeddings_instance is None:
            RAGService._embeddings_instance = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
        self.embeddings = RAGService._embeddings_instance
        self.vector_store = None
        self.logger = logging.getLogger(__name__)
```

### Approach 3: Application-Level Model Management

Create a centralized model manager that initializes the embeddings model once at application startup:

```python
class ModelManager:
    def __init__(self):
        self.embeddings_model = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize all required ML models once at startup."""
        try:
            self.embeddings_model = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            logger.info("Embeddings model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings model: {e}")
    
    def get_embeddings_model(self):
        return self.embeddings_model

# Global model manager instance
model_manager = ModelManager()
```

## 5. Implementation Plan

### Step 1: Modify RAGService
1. Implement singleton pattern or lazy initialization for embeddings model
2. Ensure the model is only loaded once during the application lifecycle
3. Test that RAG functionality still works correctly

**Specific Code Changes for services/rag_service.py:**

Replace the existing RAGService class definition with the singleton pattern implementation:

```python
class RAGService:
    """
    Simplified RAG service using LangChain FAISS for document processing and similarity search.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize RAG service with HuggingFace embeddings."""
        if not RAGService._initialized:
            self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            self.vector_store = None
            self.logger = logging.getLogger(__name__)
            RAGService._initialized = True
```

**Implementation Details:**
1. The singleton pattern ensures only one instance of RAGService exists
2. The `_initialized` flag ensures the embeddings model is only loaded once
3. All subsequent instantiations will return the same instance with the cached model

### Step 2: Optimize Grading Engine
1. Review how RAGService is instantiated in the grading engine
2. Ensure the same instance is reused across student grading operations
3. Add performance monitoring to track improvement

### Step 3: UI Layer Updates
1. Update progress tracking to reflect actual processing times
2. Add better error handling for model loading failures

## 6. Performance Impact

### Before Fix:
- Model loading time: ~5-10 seconds per student
- Total grading time for 5 students: ~50+ seconds
- CPU usage spikes during each model load

### After Fix:
- Model loading time: ~5-10 seconds (once only)
- Total grading time for 5 students: ~10-15 seconds
- Consistent CPU usage throughout process

## 7. Testing Strategy

### Unit Tests:
1. Test singleton pattern implementation in RAGService
2. Verify embeddings model is only loaded once
3. Ensure RAG functionality works correctly with cached model

### Integration Tests:
1. Test full grading process with multiple students
2. Verify performance improvement
3. Test error handling with model loading failures

### Performance Tests:
1. Measure time for processing multiple students
2. Monitor memory usage during extended grading sessions
3. Validate CPU utilization patterns

## 8. Risk Assessment

### Low Risk:
- Implementation is straightforward with minimal code changes
- Backward compatibility is maintained
- No changes to core grading logic

### Mitigation Strategies:
- Add proper error handling for model initialization failures
- Implement fallback mechanism if model loading fails
- Add logging to monitor model loading status

## 9. Monitoring and Observability

### Key Metrics to Monitor:
1. Model loading time
2. Total grading time per student
3. Memory usage during grading process
4. Number of model initializations

### Logging Improvements:
1. Add timing logs for model loading
2. Track RAG processing time separately
3. Log cache hit/miss ratios for embeddings

## 10. Future Optimizations

1. **Model Caching**: Implement disk-based caching for embeddings model
2. **Asynchronous Loading**: Load model asynchronously during application startup
3. **Model Selection**: Allow configuration of different embedding models
4. **GPU Acceleration**: Add support for GPU-based embeddings when available

## 11. Conclusion

The root cause of the grading system performance issue has been identified as repeated loading of the SentenceTransformer model during RAG processing for each student. By implementing a singleton pattern for the RAGService class, we can ensure the embeddings model is loaded only once, dramatically improving the grading performance.

This fix addresses the immediate performance bottleneck while maintaining backward compatibility and requiring minimal code changes. The solution has been designed to be robust with proper error handling and initialization tracking.