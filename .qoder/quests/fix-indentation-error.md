# Fix Indentation Error in llm_service.py

## Overview
This document describes the issues found in the `llm_service.py` file and provides a solution to fix the IndentationError that is preventing the application from running.

## Problem Analysis
The error occurs in `services/llm_service.py` at line 847 with the following message:
```
IndentationError: unindent does not match any outer indentation level
```

Upon examining the file, several issues were identified:

1. **Incorrect indentation**: The `get_performance_stats` method at line 847 is not properly indented (indented with 1 space instead of 4 spaces)
2. **Duplicate method definitions**: There are duplicate definitions for:
   - `get_performance_stats`
   - `_calculate_cache_hit_rate`
   - `optimize_memory_usage`
3. **Incomplete code**: The file ends abruptly with incomplete code (`cache_si`)

## Root Cause
The issue is caused by:
1. A method that is not properly indented to align with other class methods
2. Duplicate method definitions that create conflicts
3. Incomplete code at the end of the file

## Solution Design

### Fix 1: Correct Method Indentation
All methods in the LLMService class must be indented with exactly 4 spaces from the class definition line.

### Fix 2: Remove Duplicate Methods
Remove the duplicate implementations and keep only the most complete and correct versions of each method.

### Fix 3: Complete Incomplete Code
Complete any cut-off methods and ensure proper file termination.

## Implementation Details

### Identifying the Problematic Code
The error specifically occurs at the `get_performance_stats` method definition which is not properly aligned with other methods in the class.

### Specific Fixes Required

1. **Fix the indentation of `get_performance_stats` method**:
   - Change the indentation from 1 space to 4 spaces to match other class methods

2. **Remove duplicate method definitions**:
   - Remove the first implementation of `get_performance_stats` (the incorrectly indented one)
   - Remove the first implementation of `_calculate_cache_hit_rate`
   - Remove the first implementation of `optimize_memory_usage`

3. **Complete the incomplete code**:
   - Complete the cut-off `optimize_memory_usage` method implementation
   - Ensure proper return statement and method termination

### Detailed Code Changes

#### Before (Problematic Code):
```python
        }   
 def get_performance_stats(self) -> Dict[str, Any]:  # Incorrect indentation (1 space)
     # First implementation - to be removed

# Later in the file - duplicate methods
def get_performance_stats(self) -> Dict[str, Any]:  # Properly indented (4 spaces)
    # Second implementation - to be kept

# Similar duplicates for _calculate_cache_hit_rate and optimize_memory_usage
# Incomplete optimize_memory_usage method ending with "cache_si"
```

#### After (Fixed Code):
```python
        }   
    def get_performance_stats(self) -> Dict[str, Any]:  # Correct indentation (4 spaces)
        # Only implementation (the better one)
        cache_info = self.generate_prompt.cache_info()
        
        return {
            "api_call_count": self.api_call_count,
            "total_processing_time": self.total_processing_time,
            "avg_processing_time": self.total_processing_time / max(self.api_call_count, 1),
            "cache_size": len(self.response_cache),
            "cache_hit_rate": self._calculate_cache_hit_rate(),
            "prompt_cache_info": {
                "hits": cache_info.hits,
                "misses": cache_info.misses,
                "maxsize": cache_info.maxsize,
                "currsize": cache_info.currsize
            }
        }

    def _calculate_cache_hit_rate(self) -> float:
        # Only implementation (the better one)
        if self._cache_requests == 0:
            return 0.0
        
        return (self._cache_hits / self._cache_requests) * 100

    def optimize_memory_usage(self) -> Dict[str, Any]:
        # Completed implementation
        cache_size = len(self.response_cache)
        
        # Clear old cache entries
        current_time = time.time()
        expired_keys = [
            key for key, data in self.response_cache.items()
            if current_time - data['timestamp'] > config.API_CACHE_TTL_SECONDS
        ]
        
        for key in expired_keys:
            del self.response_cache[key]
        
        # Clear prompt cache if it's getting large
        cache_info = self.generate_prompt.cache_info()
        if cache_info.currsize > 30:
            self.generate_prompt.cache_clear()
        
        logger.info(f"LLM memory optimization: removed {len(expired_keys)} expired cache entries, "
                   f"cleared prompt cache ({cache_info.currsize} entries)")
        
        return {
            "expired_entries_removed": len(expired_keys),
            "prompt_cache_cleared": cache_info.currsize > 30,
            "cache_size_before": cache_size,
            "cache_size_after": len(self.response_cache)
        }
```

## Verification Steps
After implementing the fixes:
1. Run syntax checking to verify the IndentationError is resolved:
   ```powershell
   python -m py_compile services/llm_service.py
   ```
2. Test LLM service functionality to ensure no regression
3. Verify that all methods in the LLMService class are accessible and functional
4. Run the application to ensure the error no longer occurs when entering rubric and executing grading

## Summary
The main issue was an indentation error in the `get_performance_stats` method which was indented with only 1 space instead of the required 4 spaces to align with other class methods. Additionally, there were duplicate method definitions that needed to be cleaned up, and an incomplete method implementation that needed to be completed.