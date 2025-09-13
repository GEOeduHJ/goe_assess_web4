# AttributeError: 'Config' object has no attribute 'BATCH_PROCESSING_SIZE' - Design Document

## Overview

This document outlines the solution for fixing the AttributeError that occurs when the application tries to access `config.BATCH_PROCESSING_SIZE` which has been commented out in the configuration but is still referenced in the UI components.

## Problem Analysis

### Error Details
```
AttributeError: 'Config' object has no attribute 'BATCH_PROCESSING_SIZE'
File "C:\Users\Hong Jun\Desktop\geo_assess_web4\app.py", line 179, in render_sidebar
    st.write("**배치 처리 크기:**", config.BATCH_PROCESSING_SIZE)
```

### Root Cause
The `BATCH_PROCESSING_SIZE` attribute was commented out in the `config.py` file as part of a "system monitoring cleanup" but is still being referenced in:
1. `app.py` line 179 - in the sidebar rendering
2. `ui/grading_execution_ui.py` line 58 - in the GradingExecutionUI class initialization

### Impact
The application fails to start because it cannot render the sidebar due to the missing configuration attribute.

## Solution Design

### Approach 1: Restore the Configuration Attribute (Recommended)

Add the `BATCH_PROCESSING_SIZE` attribute back to the Config class with appropriate default value and environment variable support.

#### Implementation Steps:
1. Uncomment and restore the `BATCH_PROCESSING_SIZE` attribute in `config.py`
2. Ensure the attribute is properly initialized with a default value
3. Add support for environment variable configuration

### Approach 2: Remove All References

Remove all references to `BATCH_PROCESSING_SIZE` from the codebase.

#### Implementation Steps:
1. Remove the reference in `app.py` sidebar rendering
2. Remove the usage in `ui/grading_execution_ui.py`

## Recommended Implementation

The recommended approach is to restore the configuration attribute since it's being used in the grading execution UI for batch processing functionality. This maintains the intended functionality of the application.

### Changes Required

#### 1. Update `config.py`
Restore the `BATCH_PROCESSING_SIZE` attribute in the Config class by modifying the file around line 48:

Find the commented section:
```python
    # Performance Optimization Settings (removed as part of system monitoring cleanup)
    # MAX_MEMORY_USAGE_MB: int = int(os.getenv("MAX_MEMORY_USAGE_MB", "512"))
    # ENABLE_PERFORMANCE_MONITORING: bool = os.getenv("ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true"
    # PERFORMANCE_MONITORING_INTERVAL: int = int(os.getenv("PERFORMANCE_MONITORING_INTERVAL", "30"))
    # API_CACHE_TTL_SECONDS: int = int(os.getenv("API_CACHE_TTL_SECONDS", "300"))
    # API_CACHE_MAX_SIZE: int = int(os.getenv("API_CACHE_MAX_SIZE", "100"))
    # UI_RENDER_TIMEOUT_SECONDS: int = int(os.getenv("UI_RENDER_TIMEOUT_SECONDS", "30"))
    # BATCH_PROCESSING_SIZE: int = int(os.getenv("BATCH_PROCESSING_SIZE", "10"))
```

Replace with:
```python
    # Performance Optimization Settings (removed as part of system monitoring cleanup)
    # MAX_MEMORY_USAGE_MB: int = int(os.getenv("MAX_MEMORY_USAGE_MB", "512"))
    # ENABLE_PERFORMANCE_MONITORING: bool = os.getenv("ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true"
    # PERFORMANCE_MONITORING_INTERVAL: int = int(os.getenv("PERFORMANCE_MONITORING_INTERVAL", "30"))
    # API_CACHE_TTL_SECONDS: int = int(os.getenv("API_CACHE_TTL_SECONDS", "300"))
    # API_CACHE_MAX_SIZE: int = int(os.getenv("API_CACHE_MAX_SIZE", "100"))
    # UI_RENDER_TIMEOUT_SECONDS: int = int(os.getenv("UI_RENDER_TIMEOUT_SECONDS", "30"))
    
    # Batch Processing Settings
    BATCH_PROCESSING_SIZE: int = int(os.getenv("BATCH_PROCESSING_SIZE", "10"))
```

#### 2. Verification
Ensure that the restored attribute is properly used in:
- `app.py` sidebar display
- `ui/grading_execution_ui.py` batch processing

## Alternative Implementation (If Batch Processing Not Needed)

If the batch processing functionality is no longer required, then remove all references:

#### 1. Update `app.py`
Remove the line that references `config.BATCH_PROCESSING_SIZE` in the sidebar.

#### 2. Update `ui/grading_execution_ui.py`
Remove or replace the usage of `config.BATCH_PROCESSING_SIZE` with a hardcoded value or alternative configuration.

## Implementation Plan

1. Restore the `BATCH_PROCESSING_SIZE` attribute in `config.py`
2. Verify the application starts correctly
3. Test the batch processing functionality in the grading execution UI
4. Confirm the sidebar displays the configuration properly

## Testing Strategy

1. Unit testing:
   - Verify Config class properly loads the BATCH_PROCESSING_SIZE attribute
   - Test with and without environment variable configuration

2. Integration testing:
   - Verify application starts without AttributeError
   - Confirm sidebar displays the batch processing size
   - Test grading execution UI with batch processing

3. Manual testing:
   - Start the application and verify no AttributeError occurs
   - Check that the sidebar shows the correct batch processing size
   - Run a sample grading process to verify batch processing works

## Environment Variables

To customize the batch processing size, add the following to your `.env` file:
```
BATCH_PROCESSING_SIZE=10
```

## Rollback Plan

If issues occur after implementing this fix:
1. Comment out the BATCH_PROCESSING_SIZE line in config.py again
2. Remove the BATCH_PROCESSING_SIZE line from .env if added
3. Restart the application