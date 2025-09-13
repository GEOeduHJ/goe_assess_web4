# Implementation Plan

- [x] 1. Update dependencies and imports






  - Add langchain-community and langchain-huggingface to requirements
  - Update imports in rag_service.py to use LangChain components
  - _Requirements: 1.3_

- [x] 2. Simplify RAGService class










  - Replace custom FAISS implementation with LangChain FAISS
  - Use HuggingFaceEmbeddings instead of SentenceTransformer
  - Remove complex caching and optimization code
  - _Requirements: 1.1, 1.2_

- [x] 3. Implement simple document processing

  - Create basic text extraction for PDF and DOCX files
  - Implement simple text chunking (500 chars, 50 overlap)
  - Convert chunks to LangChain Document objects
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 4. Create FAISS vector store


  - Use FAISS.from_documents() to create vector store
  - Implement simple similarity search method
  - Return plain text chunks instead of complex objects
  - _Requirements: 1.1, 1.4_

- [x] 5. Fix RAG integration in grading pipeline



  - Update grading_engine.py to call RAG service properly
  - Ensure RAG content is passed to LLM prompts
  - Add error handling for RAG failures
  - _Requirements: 2.1, 2.2, 2.4_

- [x] 6. Update LLM prompt generation


  - Modify generate_prompt() to include RAG content
  - Format reference materials clearly in prompts
  - Handle cases when no RAG content is available
  - _Requirements: 2.2, 2.3_

- [x] 7. Add basic error handling


  - Handle file processing errors gracefully
  - Continue grading when RAG fails
  - Log errors without breaking the pipeline
  - _Requirements: 2.4, 3.4_

- [x] 8. Test the simplified implementation









  - Test document processing with sample files
  - Verify RAG content appears in LLM prompts
  - Test error handling scenarios
  - _Requirements: 2.1, 2.2, 2.3_