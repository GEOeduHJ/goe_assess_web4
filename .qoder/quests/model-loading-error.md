# KURE-v1 Model Loading Error Analysis and Solution

## Overview

This document analyzes the error encountered when loading the KURE-v1 embedding model in the geography auto-grading system. The error occurs because the system is trying to load "KURE-v1" as a model name, but the actual model identifier on Hugging Face is "nlpai-lab/KURE-v1".

## Problem Analysis

### Error Details
```
ERROR:services.rag_service:Failed to load embedding model: sentence-transformers/KURE-v1 is not a local folder and is not a valid model identifier listed on 'https://huggingface.co/models'

If this is a private repository, make sure to pass a token having permission to this repo either by logging in with `hf auth login` or by passing `token=<your_token>`
```

### Root Cause
1. **Incorrect Model Name**: The RAG service is initialized with `model_name: str = "KURE-v1"` instead of the full path `"nlpai-lab/KURE-v1"`
2. **Missing Hugging Face Token**: The KURE-v1 model may require authentication for access
3. **Environment Configuration**: The `.env` file may not be properly configured with the HF_TOKEN

### Code Analysis
In `services/rag_service.py`:
```python
def __init__(self, model_name: str = "KURE-v1"):
    # ...
    self.model_name = model_name

def _load_embedding_model(self) -> None:
    try:
        if self.embedding_model is None:
            self.logger.info(f"Loading embedding model: {self.model_name}")
            # Use HF token if available for private model access
            token = config.HF_TOKEN if config.HF_TOKEN else None
            self.embedding_model = SentenceTransformer(self.model_name, token=token)
```

In `config.py`:
```python
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nlpai-lab/KURE-v1")
```

There's a mismatch between the default model name in the RAG service initialization and the configuration.

## Solution Design

### 1. Fix Model Name Configuration
Update the RAG service to use the correct model identifier:

```python
def __init__(self, model_name: str = "nlpai-lab/KURE-v1"):
    # ...
    self.model_name = model_name
```

### 2. Improve Model Loading Logic
Modify the model loading process to handle both local and remote model scenarios:

```python
def _load_embedding_model(self) -> None:
    """Load the KURE-v1 embedding model."""
    try:
        if self.embedding_model is None:
            self.logger.info(f"Loading embedding model: {self.model_name}")
            # Use HF token if available for private model access
            token = config.HF_TOKEN if config.HF_TOKEN else None
            
            # Try to load the model
            self.embedding_model = SentenceTransformer(self.model_name, token=token)
            self.logger.info("Embedding model loaded successfully")
    except Exception as e:
        self.logger.error(f"Failed to load embedding model: {e}")
        # Provide more specific error handling
        if "not a valid model identifier" in str(e):
            self.logger.error("Model identifier is invalid. Please check the model name and ensure it exists on Hugging Face.")
        elif "private repository" in str(e):
            self.logger.error("Model requires authentication. Please provide a valid HF_TOKEN in your .env file.")
        raise RuntimeError(f"Failed to load embedding model: {e}")
```

### 3. Environment Configuration
Create a proper `.env` file with the required token:

```env
# Hugging Face Token for private model access
HF_TOKEN=your_huggingface_token_here

# Other configurations...
GOOGLE_API_KEY=your_google_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

### 4. Fallback Model Strategy
Implement a fallback mechanism to use a public model if the private one fails:

```python
def _load_embedding_model(self) -> None:
    """Load the KURE-v1 embedding model with fallback options."""
    models_to_try = [
        self.model_name,  # Primary model (nlpai-lab/KURE-v1)
        "sentence-transformers/all-MiniLM-L6-v2",  # Public fallback model
    ]
    
    token = config.HF_TOKEN if config.HF_TOKEN else None
    
    for model_name in models_to_try:
        try:
            if self.embedding_model is None:
                self.logger.info(f"Loading embedding model: {model_name}")
                self.embedding_model = SentenceTransformer(model_name, token=token)
                self.logger.info(f"Embedding model '{model_name}' loaded successfully")
                return
        except Exception as e:
            self.logger.warning(f"Failed to load model '{model_name}': {e}")
            continue
    
    raise RuntimeError("Failed to load any embedding model")
```

## Implementation Steps

### Step 1: Update RAG Service Constructor
Change the default model name in `RAGService.__init__` from `"KURE-v1"` to `"nlpai-lab/KURE-v1"`

### Step 2: Improve Error Handling
Enhance the `_load_embedding_model` method with better error messages and handling

### Step 3: Configure Environment
Create a `.env` file with the proper HF_TOKEN value

### Step 4: (Optional) Add Fallback Mechanism
Implement the fallback model strategy for improved reliability

## Testing Plan

### Unit Tests
1. Test model loading with correct model name
2. Test model loading with incorrect model name (should fail gracefully)
3. Test model loading with authentication token
4. Test fallback mechanism if implemented

### Integration Tests
1. Test complete document processing workflow with the corrected model name
2. Verify that embeddings are generated correctly
3. Confirm FAISS index creation works properly

## Configuration Changes

### Environment Variables
Add the following to `.env`:
```env
HF_TOKEN=your_actual_huggingface_token_here
```

### Code Changes
1. In `services/rag_service.py`, line 33:
   ```python
   # Before
   def __init__(self, model_name: str = "KURE-v1"):
   
   # After
   def __init__(self, model_name: str = "nlpai-lab/KURE-v1"):
   ```

## Security Considerations

1. **Token Management**: The HF_TOKEN should be stored securely in the `.env` file and never committed to version control
2. **Error Messages**: Avoid exposing sensitive information in error messages that might be visible to users
3. **Access Control**: Ensure that only authorized users can access the token configuration

## Performance Impact

The solution should not negatively impact performance:
- Model loading happens once per service instance
- Fallback mechanism only activates if the primary model fails
- Error handling adds minimal overhead

## Dependencies

- sentence-transformers library (already in project dependencies)
- Hugging Face account with access to KURE-v1 model (if using the private version)
- Internet connectivity for downloading the model (if not cached locally)