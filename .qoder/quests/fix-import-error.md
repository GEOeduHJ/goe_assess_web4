# Fix for ImportError in Grading Execution UI

## Problem Description

When running the geography auto-grading platform and clicking the "채점 실행" (grading execution) button after entering the rubric, the following import error occurs:

```
ImportError: cannot import name 'display_progress_with_error_handling' from 'ui.error_display_ui' 
(C:\Users\Hong Jun\Desktop\geo_assess_web4\ui\error_display_ui.py)
```

## Root Cause Analysis

After examining the codebase, the issue is identified:

1. In `ui/grading_execution_ui.py` line 21, there's an import statement:
   ```python
   from ui.error_display_ui import display_error, display_api_error, display_progress_with_error_handling
   ```

2. In `ui/error_display_ui.py`, the `display_progress_with_error_handling` function is defined as a method within the `ErrorDisplayUI` class (lines 223-259) but is not exported as a module-level convenience function like `display_error` and `display_api_error`.

3. The module only exports `display_error`, `display_file_upload_error`, `display_api_error`, and `display_validation_error` as convenience functions, but not `display_progress_with_error_handling`.

## Solution Design

### Option 1: Add Missing Convenience Function (Recommended)

Add the missing `display_progress_with_error_handling` convenience function to `ui/error_display_ui.py` to match the existing pattern of other exported functions.

### Option 2: Modify Import Statement

Change the import in `ui/grading_execution_ui.py` to access the method through the class instance.

## Implementation Plan

I recommend Option 1 as it maintains consistency with the existing codebase pattern and requires minimal changes.

### Step 1: Add Convenience Function

Add the following convenience function to `ui/error_display_ui.py`:

```python
def display_progress_with_error_handling(
    current: int, 
    total: int, 
    current_item: str = "",
    recent_errors: List[ErrorInfo] = None
) -> None:
    """
    Convenience function for displaying progress with error handling.
    
    Args:
        current: Current progress count
        total: Total items to process
        current_item: Currently processing item name
        recent_errors: List of recent errors during processing
    """
    error_display.display_progress_with_error_handling(current, total, current_item, recent_errors)
```

### Step 2: Verify Module Structure

The `ui/error_display_ui.py` file already imports `List` from typing, and the `__all__` list is not explicitly defined in the module, so we don't need to modify the imports or exports.

## Implementation Details

### File: ui/error_display_ui.py

1. Add the convenience function at the end of the file (after the existing convenience functions)
2. Ensure the function signature matches the class method exactly
3. The `List` type is already imported in the file, so no additional imports are needed

The exact code to add at the end of `ui/error_display_ui.py` is:

```python
def display_progress_with_error_handling(
    current: int, 
    total: int, 
    current_item: str = "",
    recent_errors: List[ErrorInfo] = None
) -> None:
    """
    Convenience function for displaying progress with error handling.
    
    Args:
        current: Current progress count
        total: Total items to process
        current_item: Currently processing item name
        recent_errors: List of recent errors during processing
    """
    error_display.display_progress_with_error_handling(current, total, current_item, recent_errors)
```

### Implementation Method

To implement this fix, you'll need to modify the `ui/error_display_ui.py` file by adding the convenience function shown above at the end of the file. This can be done using a text editor or IDE that can modify Python files.

## Verification

After implementing the fix:
1. The import error should be resolved
2. The grading execution functionality should work correctly
3. Progress display with error handling should function as expected