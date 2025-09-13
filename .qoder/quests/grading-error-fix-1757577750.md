# Grading Error Fix Design Document

## 1. Overview

This document outlines fixes for critical errors in the geography auto-grading system:

1. `PerformanceMonitor.auto_optimize() missing 1 required positional argument: 'metrics'` in RAG service
2. `'dict' object has no attribute '__name__'` in LLM service
3. Support for Korean Excel column headers: "학생", "반", "답안"

## 2. System Architecture

The system follows a modular architecture:
- **UI Layer**: Streamlit-based interface
- **Service Layer**: Grading engine, LLM service, RAG service
- **Model Layer**: Student, rubric, and grading result models
- **Utility Layer**: Performance optimization and error handling

Error flow: UI → Grading Engine → RAG Service → LLM Service → Error

## 3. Error Analysis

### 3.1 RAG Service Error
```
ERROR:services.rag_service:Error processing documents for student: PerformanceMonitor.auto_optimize() missing 1 required positional argument: 'metrics'
```

**Root Cause**: `process_documents_for_student` calls `performance_monitor.auto_optimize()` without required `metrics` parameter.

**Location**: Line 520 in `services/rag_service.py`

### 3.2 LLM Service Error
```
ERROR:services.llm_service:Failed to grade student: 'dict' object has no attribute '__name__'
```

**Root Cause**: Code accesses `__name__` attribute on a dictionary instead of a callable.

### 3.3 Excel File Format Issue

**Issue**: System needs to support Korean column headers:
- "학생" (Student Name)
- "반" (Class)
- "답안" (Answer)

## 4. Solution Design

### 4.1 Fix RAG Service Auto-Optimize Call

**Problem**: `performance_monitor.auto_optimize()` called without required `PerformanceMetrics` parameter.

**Solution**: 
1. Remove explicit call to `performance_monitor.auto_optimize()` in `process_documents_for_student` method
2. Performance monitor handles optimization automatically through its monitoring thread

### 4.2 Fix LLM Service Dictionary Error

**Problem**: Code tries to access `__name__` attribute on a dictionary.

**Root Cause**: Error handling mechanism treats dictionary as callable object in retry mechanism.

**Solution**:
1. Review retry_with_backoff calls in LLM service
2. Ensure only callable objects are passed to retry mechanisms

### 4.3 Update Excel File Processing

**Problem**: File service expects Korean column headers but users may upload files with English headers.

**Solution**:
1. Add support for English column names by mapping to Korean equivalents
2. Update validation to accept both Korean and English column names
3. Map English headers to Korean internally for consistent processing

## 5. Detailed Implementation Plan

### 5.1 RAG Service Fix

**File**: `services/rag_service.py`
**Method**: `process_documents_for_student`
**Line**: 410

**Issue**: `performance_monitor.auto_optimize()` called without required `PerformanceMetrics` parameter.

**Change**:
1. Remove the call to `performance_monitor.auto_optimize()` on line 410
2. The performance monitor automatically handles optimization through its monitoring thread

### 5.2 LLM Service Fix

**File**: `services/llm_service.py`
**Issue**: Dictionary object being treated as callable with `__name__` attribute

**Root Cause**: In error handling or retry mechanisms, a dictionary is being passed where a callable is expected

**Change**:
1. Review error handling code in LLM service
2. Ensure only callable objects are passed to retry mechanisms

### 5.3 Excel Processing Enhancement

**File**: `services/file_service.py`
**Methods**: `validate_excel_format` and `_validate_excel_data`

**Observation**: File service already supports Korean column names

**Change**:
1. Add support for English column names by mapping to Korean equivalents
2. Update validation to accept both Korean and English column names

## 6. Implementation Details

### 6.1 RAG Service Fix

In `services/rag_service.py`, line 410, remove the problematic call:
```python
# Remove this line:
performance_monitor.auto_optimize()
```

The performance monitor automatically handles optimization through its monitoring thread, so this explicit call is unnecessary and incorrectly implemented.

### 6.2 LLM Service Fix

In `services/llm_service.py`, review all calls to `retry_with_backoff` to ensure only callable objects are passed. The error suggests a dictionary is being passed where a callable is expected.

### 6.3 Excel Processing Enhancement

In `services/file_service.py`, modify the column validation to accept both Korean and English headers:

1. Add English column name mappings:
   - "학생" → "Student"
   - "반" → "Class"
   - "답안" → "Answer"

2. Update `validate_excel_format` method to detect header language and map English headers to Korean equivalents before validation.

3. Maintain backward compatibility with existing Korean header format.

## 7. Testing Strategy

### 7.1 Unit Tests
1. Test RAG service without performance monitor call errors
2. Test LLM service error handling with various object types
3. Test file service with both Korean and English column headers

### 7.2 Integration Tests
1. End-to-end grading with Korean and English Excel files
2. Error recovery scenarios
3. Performance optimization verification

## 8. Error Handling Improvements

### 8.1 Enhanced Error Messages
- Provide more specific error information for debugging
- Include context about which student caused the error

### 8.2 Graceful Degradation
- Continue processing other students when one fails
- Provide partial results when possible