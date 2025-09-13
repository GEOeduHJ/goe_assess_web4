# Fix Indentation Error and BATCH_PROCESSING_SIZE Attribute Issue

## Overview

This document outlines the fixes needed for two critical issues in the geography auto-grading platform:

1. An indentation error in [main_ui.py](file://c:\Users\Hong%20Jun\Desktop\geo_assess_web4\ui\main_ui.py) at line 319 that prevents the application from running
2. A missing attribute error related to `BATCH_PROCESSING_SIZE` in the Config class

## Issues Analysis

### Issue 1: Indentation Error in main_ui.py

**Error Message:**
```
IndentationError: expected an indented block after 'with' statement on line 316
```

**Location:** [ui/main_ui.py](file://c:\Users\Hong%20Jun\Desktop\geo_assess_web4\ui\main_ui.py), line 319

**Root Cause:** 
In the `render_navigation_buttons` method, there's a `with col1:` block that contains only a `pass` statement. In Python, when a block contains only a `pass` statement, it still requires proper indentation. However, the real issue is that the code was likely intended to have actual content in this block but was left empty during a cleanup process.

Looking at the code, there was a comment indicating that a "Performance dashboard button" was removed as part of system monitoring cleanup, but the `with col1:` block was left with only a `pass` statement.

### Issue 2: Missing BATCH_PROCESSING_SIZE Attribute

**Error Message:**
```
AttributeError: 'Config' object has no attribute 'BATCH_PROCESSING_SIZE'
```

**Location:** [app.py](file://c:\Users\Hong%20Jun\Desktop\geo_assess_web4\app.py), line 179

**Root Cause:**
In [config.py](file://c:\Users\Hong%20Jun\Desktop\geo_assess_web4\config.py), the `BATCH_PROCESSING_SIZE` attribute is defined in the Config class, but there appears to be a discrepancy in how it's being accessed in [app.py](file://c:\Users\Hong%20Jun\Desktop\geo_assess_web4\app.py). Looking at the code, the attribute is properly defined as `BATCH_PROCESSING_SIZE: int = int(os.getenv("BATCH_PROCESSING_SIZE", "10"))` in the Config class.

## Solution Design

### Fix 1: Resolve Indentation Error in main_ui.py

The indentation error in [main_ui.py](file://c:\Users\Hong%20Jun\Desktop\geo_assess_web4\ui\main_ui.py) needs to be fixed by properly handling the empty `with col1:` block. There are two approaches:

1. **Remove the empty block entirely:** Since there's no content in the `col1` section, we can remove the entire `with col1:` block.
2. **Add a proper placeholder:** If the UI layout requires the column to exist, we can add a meaningful placeholder.

We'll go with approach 1 since the comment indicates the performance dashboard button was intentionally removed.

### Fix 2: Verify BATCH_PROCESSING_SIZE Access

The `BATCH_PROCESSING_SIZE` attribute is correctly defined in the Config class. The issue might be in how it's accessed. We need to verify that the attribute is accessed correctly as `config.BATCH_PROCESSING_SIZE` rather than trying to access it as an attribute of a different object.

## Implementation Plan

### Fix 1: main_ui.py Indentation Error

1. Locate the `render_navigation_buttons` method in [ui/main_ui.py](file://c:\Users\Hong%20Jun\Desktop\geo_assess_web4\ui\main_ui.py)
2. Remove the empty `with col1:` block that contains only a `pass` statement
3. Adjust the column layout to account for the removed column

### Fix 2: BATCH_PROCESSING_SIZE Attribute Access

1. Verify the correct access pattern in [app.py](file://c:\Users\Hong%20Jun\Desktop\geo_assess_web4\app.py) for the BATCH_PROCESSING_SIZE attribute
2. Ensure it's accessed as `config.BATCH_PROCESSING_SIZE` rather than through a different object reference

## Code Changes

### Change 1: Fix Indentation Error in main_ui.py

We'll keep the original column structure but properly handle the empty column:

```python
def render_navigation_buttons(self):
    """
    Render navigation buttons for proceeding to next steps.
    """
    st.markdown("---")
    st.markdown("### 🚀 다음 단계")
    
    # Check if required files are uploaded
    can_proceed = self.check_required_files()
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Performance dashboard button removed as part of system monitoring cleanup
        # Keep empty column for layout consistency
        st.empty()
    
    with col2:
        if can_proceed:
            if st.button(
                "📋 루브릭 설정하기",
                key="proceed_to_rubric",
                use_container_width=True,
                type="primary"
            ):
                # Process files before proceeding
                self.process_uploaded_files()
                st.session_state.current_page = "rubric"
                st.rerun()
        else:
            st.button(
                "📋 루브릭 설정하기",
                key="proceed_to_rubric_disabled",
                use_container_width=True,
                disabled=True,
                help="필수 파일을 모두 업로드한 후 진행할 수 있습니다."
            )
    
    # Show requirements status
    self.show_requirements_status()
```

### Change 2: Verify BATCH_PROCESSING_SIZE Access

In [app.py](file://c:\Users\Hong%20Jun\Desktop\geo_assess_web4\app.py), ensure the attribute is accessed correctly:

```python
# In the render_sidebar function
with st.expander("🔧 현재 설정"):
    st.write("**임베딩 모델:**", config.EMBEDDING_MODEL)
    st.write("**최대 파일 크기:**", f"{config.MAX_FILE_SIZE_MB}MB")
    st.write("**최대 재시도 횟수:**", config.MAX_RETRIES)
    st.write("**검색 결과 수:**", config.TOP_K_RETRIEVAL)
    # Performance-related configuration removed as part of system monitoring cleanup
    st.write("**배치 처리 크기:**", config.BATCH_PROCESSING_SIZE)
```

## Testing Plan

1. **Syntax Check:** Run Python syntax checker on modified files
2. **Application Startup:** Verify that the Streamlit application starts without errors
3. **UI Navigation:** Test navigation between different pages of the application
4. **File Upload:** Test file upload functionality for both descriptive and map grading types
5. **Configuration Display:** Verify that all configuration settings display correctly in the sidebar

## Rollback Plan

If issues arise after deployment:

1. Revert the changes to [main_ui.py](file://c:\Users\Hong%20Jun\Desktop\geo_assess_web4\ui\main_ui.py)
2. Revert any changes to [app.py](file://c:\Users\Hong%20Jun\Desktop\geo_assess_web4\app.py) if made
3. Restart the Streamlit application

## Conclusion

These fixes will resolve the immediate errors preventing the application from running. The indentation error in [main_ui.py](file://c:\Users\Hong%20Jun\Desktop\geo_assess_web4\ui\main_ui.py) is a syntax error that must be fixed for the application to start, while the BATCH_PROCESSING_SIZE issue needs verification to ensure proper attribute access.