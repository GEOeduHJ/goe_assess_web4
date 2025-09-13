# Fix Configuration Issues

## Overview

This document outlines the fixes needed for the geo_assess_web4 project to resolve:
1. Missing configuration attributes that cause runtime errors
2. Leftover references to removed performance optimization features

Note: The indentation error in `main_ui.py` has already been fixed in the current version of the file.

## Issues Analysis

### 1. Indentation Error (Already Fixed)
- **File**: `ui/main_ui.py`
- **Line**: 319
- **Problem**: Missing indented block after `with` statement on line 316
- **Impact**: Application fails to start with `IndentationError`
- **Status**: This issue has been resolved in the current version of the file

### 2. Missing Configuration Attributes
- **File**: `config.py`
- **Missing Attributes**:
  - `API_CACHE_MAX_SIZE`
  - `API_CACHE_TTL_SECONDS`
- **Impact**: Runtime errors when LLM service tries to access these attributes

### 3. Leftover Performance Monitoring References
- **Files**: Multiple files contain references to removed performance monitoring features
- **Impact**: Confusing code and potential runtime errors

## Fixes Implementation

### Fix 1: Correct Indentation Error in main_ui.py (Already Fixed)

The indentation error occurs in the `render_navigation_buttons` method where a `with` statement is not properly followed by an indented block.

```python
# Current problematic code (around line 316):
col1, col2 = st.columns([1, 2])

with col1:
    # Performance dashboard button removed as part of system monitoring cleanup
    pass

with col2:
# Missing indented block here - this causes the IndentationError
```

**Status**: This issue has been resolved in the current version of the file

### Fix 2: Add Missing Configuration Attributes

Add the missing configuration attributes back to the Config class in `config.py`:

```python
# Add to Performance Optimization Settings section (around line 40)
API_CACHE_TTL_SECONDS: int = int(os.getenv("API_CACHE_TTL_SECONDS", "300"))
API_CACHE_MAX_SIZE: int = int(os.getenv("API_CACHE_MAX_SIZE", "100"))
```

### Fix 3: Update LLM Service to Handle Missing Configuration Gracefully

Modify the LLM service to provide default values when configuration attributes are missing.

## Implementation Plan

### 1. Fix Indentation Error (Already Fixed)
- Edit `ui/main_ui.py` to correct the indentation after the `with` statement
- **Status**: This issue has been resolved in the current version of the file

### 2. Restore Missing Configuration
- Add missing attributes to `config.py`

### 3. Update LLM Service
- Modify `services/llm_service.py` to handle missing configuration gracefully

## Code Changes

### Change 1: Fix Indentation in main_ui.py (Already Fixed)
The indentation error in `ui/main_ui.py` at line 319 needs to be fixed by ensuring proper indentation after the `with col2:` statement.

**Status**: This issue has been resolved in the current version of the file.

### Change 2: Add Missing Configuration Attributes
In `config.py`, add the missing configuration attributes that were accidentally removed:

```python
# Add to Performance Optimization Settings section
API_CACHE_TTL_SECONDS: int = int(os.getenv("API_CACHE_TTL_SECONDS", "300"))
API_CACHE_MAX_SIZE: int = int(os.getenv("API_CACHE_MAX_SIZE", "100"))
```

### Change 3: Update LLM Service for Graceful Degradation
In `services/llm_service.py`, modify the code to handle cases where configuration attributes might be missing:

# Replace direct config references with getattr to provide defaults
# In _get_cached_response method:
```python
if time.time() - cached_data['timestamp'] < getattr(config, 'API_CACHE_TTL_SECONDS', 300):
```

# In _cache_response method:
```python
if len(self.response_cache) >= getattr(config, 'API_CACHE_MAX_SIZE', 100):
```

# In optimize_memory_usage method:
```python
if current_time - data['timestamp'] > getattr(config, 'API_CACHE_TTL_SECONDS', 300):
```

## Testing Plan

1. **Unit Tests**:
   - Verify that the application starts without indentation errors
   - Check that configuration attributes are accessible
   - Ensure LLM service functions properly with and without configuration attributes

2. **Integration Tests**:
   - Test the full grading workflow for both descriptive and map-based questions
   - Verify that caching works correctly
   - Confirm that error handling functions properly

3. **Regression Tests**:
   - Ensure that previously working features still function correctly
   - Verify that performance optimization features that were intentionally removed stay removed

## Rollback Plan

If issues arise after deployment:
1. Revert the changes to `ui/main_ui.py`
2. Restore the original `config.py` if needed
3. Revert changes to `services/llm_service.py` if needed

## Related Files

- `config.py` - Missing configuration attributes
- `services/llm_service.py` - Uses the missing configuration attributes
- `app.py` - References the BATCH_PROCESSING_SIZE configuration