# Requirements Document

## Introduction

The geography auto-grading platform needs a simplified RAG system using LangChain FAISS. The current custom FAISS implementation is complex and the RAG content isn't properly reaching the LLM prompts. This spec simplifies the RAG pipeline to use standard LangChain patterns.

## Requirements

### Requirement 1

**User Story:** As a developer, I want to replace the custom FAISS implementation with LangChain's FAISS vector store, so that the code is simpler and more maintainable.

#### Acceptance Criteria

1. WHEN documents are processed THEN the system SHALL use LangChain FAISS.from_documents() method
2. WHEN similarity search is performed THEN the system SHALL use vector_store.similarity_search() method
3. WHEN embeddings are needed THEN the system SHALL use HuggingFaceEmbeddings from LangChain
4. WHEN the RAG service is initialized THEN the system SHALL create a simple FAISS vector store

### Requirement 2

**User Story:** As a user, I want RAG content to be included in grading prompts, so that reference materials help with accurate grading.

#### Acceptance Criteria

1. WHEN a student answer is graded THEN the system SHALL search for relevant document chunks
2. WHEN relevant chunks are found THEN the system SHALL add them to the LLM prompt
3. WHEN no relevant content is found THEN the system SHALL grade without reference materials
4. WHEN RAG fails THEN the system SHALL continue grading normally

### Requirement 3

**User Story:** As a developer, I want a simple document processing pipeline, so that uploaded files are easily converted to searchable chunks.

#### Acceptance Criteria

1. WHEN PDF files are uploaded THEN the system SHALL extract text and create chunks
2. WHEN DOCX files are uploaded THEN the system SHALL extract text and create chunks  
3. WHEN documents are chunked THEN the system SHALL create LangChain Document objects
4. WHEN processing fails THEN the system SHALL skip the problematic document