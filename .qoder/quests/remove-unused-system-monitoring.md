# Remove Unused System Monitoring Features

## Overview

This design document outlines the plan to remove unused system monitoring and performance dashboard features from the geography auto-grading platform. These features are not directly related to the core auto-grading functionality and should be removed to simplify the codebase and reduce unnecessary complexity.

The features to be removed include:
1. Performance dashboard UI components
2. Performance monitoring utilities and services
3. Related configuration settings
4. UI elements that reference performance monitoring

## Architecture

### Components to Remove

1. **UI Components**:
   - `ui/performance_dashboard_ui.py` - Entire file containing performance dashboard UI implementation
   - Performance monitoring references in `ui/main_ui.py`

2. **Utility Modules**:
   - `utils/performance_optimizer.py` - Entire file containing performance monitoring and optimization utilities

3. **Configuration Settings**:
   - Performance-related settings in `config.py`

4. **Application Entry Point**:
   - Performance monitoring initialization in `app.py`
   - Performance dashboard page routing in `app.py`

### Dependencies to Update

The following files have dependencies on the performance monitoring components that need to be removed:

1. `app.py` - Main application entry point
2. `ui/main_ui.py` - Main UI controller
3. `services/llm_service.py` - LLM service with performance optimization decorators
4. `services/rag_service.py` - RAG service with performance monitoring references
5. `ui/grading_execution_ui.py` - Grading execution UI with performance optimization decorators

## Implementation Plan

### Phase 1: Remove UI Components

1. Delete `ui/performance_dashboard_ui.py`
2. Remove performance dashboard navigation buttons from `ui/main_ui.py`
3. Remove performance monitoring widget from sidebar in `app.py`

### Phase 2: Remove Utility Modules

1. Delete `utils/performance_optimizer.py`
2. Remove all imports and references to performance monitoring in dependent files

### Phase 3: Update Configuration

1. Remove performance-related configuration settings from `config.py`

### Phase 4: Clean Up Application Entry Point

1. Remove performance monitoring initialization code from `app.py`
2. Remove performance dashboard page routing from `app.py`

## Files to be Modified

### 1. app.py
- Remove performance monitoring imports
- Remove performance monitoring initialization
- Remove performance dashboard page routing
- Remove sidebar performance widget

### 2. ui/main_ui.py
- Remove performance dashboard navigation button
- Remove related session state handling

### 3. services/llm_service.py
- Remove performance optimization decorators
- Remove performance monitoring imports

### 4. services/rag_service.py
- Remove performance monitoring imports
- Remove performance monitoring callbacks

### 5. ui/grading_execution_ui.py
- Remove performance optimization decorators
- Remove performance monitoring imports

### 6. config.py
- Remove performance-related configuration settings

## Files to be Deleted

1. `ui/performance_dashboard_ui.py`
2. `utils/performance_optimizer.py`

## Testing Strategy

### Unit Testing
1. Verify that all performance monitoring related unit tests are removed
2. Ensure core auto-grading functionality still works correctly
3. Confirm that no import errors occur after removing dependencies

### Integration Testing
1. Test file upload functionality for both descriptive and map-based grading
2. Verify rubric configuration and saving
3. Test grading execution for both question types
4. Confirm results display and export functionality

### UI Testing
1. Verify main UI navigation works without performance dashboard
2. Confirm sidebar displays correctly without performance widget
3. Test both descriptive and map-based grading flows
4. Ensure no broken links or missing functionality

## Expected Outcomes

### Positive Impacts
1. **Reduced Code Complexity**: Removal of unused performance monitoring features simplifies the codebase
2. **Improved Maintainability**: Fewer files and dependencies to maintain
3. **Faster Development**: Less code to understand and modify for future enhancements
4. **Reduced Resource Usage**: Eliminates background performance monitoring processes

### Potential Risks
1. **Loss of Performance Insights**: No monitoring of system performance (but not required per user request)
2. **Possible Integration Issues**: Risk of breaking dependencies if not all references are removed

## Rollback Plan

If issues arise after removing the performance monitoring features:

1. Restore the deleted files from version control
2. Revert changes to modified files
3. Re-enable performance monitoring through configuration
4. Test application to confirm full functionality is restored