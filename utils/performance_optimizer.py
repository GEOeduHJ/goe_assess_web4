"""
Performance Optimization Utilities for Geography Auto-Grading System

This module provides performance optimization features including:
- Memory usage monitoring and optimization
- API call performance tuning
- UI responsiveness improvements
- Caching mechanisms
"""

import gc
import time
import psutil
import threading
from typing import Dict, Any, Optional, List, Callable
from functools import wraps, lru_cache
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import streamlit as st

from config import config


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    memory_usage_mb: float
    cpu_usage_percent: float
    api_call_count: int
    api_response_time_avg: float
    ui_render_time: float
    cache_hit_rate: float
    timestamp: datetime


class MemoryOptimizer:
    """Memory usage optimization utilities."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.memory_threshold_mb = config.MAX_MEMORY_USAGE_MB
        self.cleanup_callbacks: List[Callable] = []
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics."""
        memory_info = self.process.memory_info()
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size
            "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            "percent": self.process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / 1024 / 1024
        }
    
    def check_memory_threshold(self) -> bool:
        """Check if memory usage exceeds threshold."""
        memory_usage = self.get_memory_usage()
        return memory_usage["rss_mb"] > self.memory_threshold_mb
    
    def optimize_memory(self, force: bool = False) -> Dict[str, Any]:
        """
        Optimize memory usage by cleaning up resources.
        
        Args:
            force: Force cleanup even if threshold not exceeded
            
        Returns:
            Dictionary with optimization results
        """
        memory_before = self.get_memory_usage()
        
        if not force and not self.check_memory_threshold():
            return {
                "optimized": False,
                "reason": "Memory usage within threshold",
                "memory_before": memory_before
            }
        
        logger.info(f"Starting memory optimization. Current usage: {memory_before['rss_mb']:.1f}MB")
        
        # Run cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.warning(f"Cleanup callback failed: {e}")
        
        # Clear Streamlit cache
        if hasattr(st, 'cache_data'):
            st.cache_data.clear()
        if hasattr(st, 'cache_resource'):
            st.cache_resource.clear()
        
        # Force garbage collection
        collected = gc.collect()
        
        memory_after = self.get_memory_usage()
        memory_saved = memory_before["rss_mb"] - memory_after["rss_mb"]
        
        logger.info(f"Memory optimization completed. Saved: {memory_saved:.1f}MB, Collected: {collected} objects")
        
        return {
            "optimized": True,
            "memory_before": memory_before,
            "memory_after": memory_after,
            "memory_saved_mb": memory_saved,
            "objects_collected": collected
        }
    
    def register_cleanup_callback(self, callback: Callable):
        """Register a cleanup callback for memory optimization."""
        self.cleanup_callbacks.append(callback)
    
    def monitor_memory_usage(self, interval: int = 30):
        """
        Start background memory monitoring.
        
        Args:
            interval: Monitoring interval in seconds
        """
        def monitor():
            while True:
                try:
                    if self.check_memory_threshold():
                        logger.warning(f"Memory threshold exceeded: {self.get_memory_usage()['rss_mb']:.1f}MB")
                        self.optimize_memory()
                    
                    time.sleep(interval)
                except Exception as e:
                    logger.error(f"Memory monitoring error: {e}")
                    break
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        logger.info(f"Memory monitoring started with {interval}s interval")


class APIPerformanceOptimizer:
    """API call performance optimization."""
    
    def __init__(self):
        self.call_history: List[Dict[str, Any]] = []
        self.rate_limiter = RateLimiter()
        self.response_cache = ResponseCache()
    
    def track_api_call(self, api_name: str, duration: float, success: bool):
        """Track API call performance."""
        self.call_history.append({
            "api_name": api_name,
            "duration": duration,
            "success": success,
            "timestamp": datetime.now()
        })
        
        # Keep only recent history (last 1000 calls)
        if len(self.call_history) > 1000:
            self.call_history = self.call_history[-1000:]
    
    def get_performance_stats(self, api_name: Optional[str] = None) -> Dict[str, Any]:
        """Get API performance statistics."""
        if api_name:
            calls = [c for c in self.call_history if c["api_name"] == api_name]
        else:
            calls = self.call_history
        
        if not calls:
            return {"error": "No API calls recorded"}
        
        durations = [c["duration"] for c in calls if c["success"]]
        success_rate = sum(1 for c in calls if c["success"]) / len(calls) * 100
        
        return {
            "total_calls": len(calls),
            "success_rate": success_rate,
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "recent_calls": len([c for c in calls if c["timestamp"] > datetime.now() - timedelta(minutes=5)])
        }
    
    def optimize_api_calls(self, func: Callable) -> Callable:
        """
        Decorator to optimize API calls with caching and rate limiting.
        
        Args:
            func: API function to optimize
            
        Returns:
            Optimized function
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            api_name = func.__name__
            
            # Check cache first
            cache_key = self.response_cache.generate_key(args, kwargs)
            cached_response = self.response_cache.get(cache_key)
            if cached_response:
                logger.debug(f"Cache hit for {api_name}")
                return cached_response
            
            # Apply rate limiting
            self.rate_limiter.wait_if_needed(api_name)
            
            # Execute API call with timing
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Cache successful response
                self.response_cache.set(cache_key, result)
                
                # Track performance
                self.track_api_call(api_name, duration, True)
                
                return result
            
            except Exception as e:
                duration = time.time() - start_time
                self.track_api_call(api_name, duration, False)
                raise
        
        return wrapper


class RateLimiter:
    """Rate limiting for API calls."""
    
    def __init__(self):
        self.call_times: Dict[str, List[float]] = {}
        self.limits = {
            "gemini": {"calls": 60, "window": 60},  # 60 calls per minute
            "groq": {"calls": 30, "window": 60}     # 30 calls per minute
        }
    
    def wait_if_needed(self, api_name: str):
        """Wait if rate limit would be exceeded."""
        if api_name not in self.limits:
            return
        
        current_time = time.time()
        limit_config = self.limits[api_name]
        
        # Initialize call history for this API
        if api_name not in self.call_times:
            self.call_times[api_name] = []
        
        # Remove old calls outside the window
        window_start = current_time - limit_config["window"]
        self.call_times[api_name] = [
            t for t in self.call_times[api_name] if t > window_start
        ]
        
        # Check if we need to wait
        if len(self.call_times[api_name]) >= limit_config["calls"]:
            oldest_call = min(self.call_times[api_name])
            wait_time = oldest_call + limit_config["window"] - current_time
            
            if wait_time > 0:
                logger.info(f"Rate limit reached for {api_name}. Waiting {wait_time:.1f}s")
                time.sleep(wait_time)
        
        # Record this call
        self.call_times[api_name].append(current_time)


class ResponseCache:
    """Response caching for API calls."""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
    
    def generate_key(self, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function arguments."""
        import hashlib
        import json
        
        # Create a deterministic string from args and kwargs
        key_data = {
            "args": str(args),
            "kwargs": sorted(kwargs.items())
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached response if valid."""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if time.time() - entry["timestamp"] > self.ttl_seconds:
            del self.cache[key]
            return None
        
        return entry["data"]
    
    def set(self, key: str, data: Any):
        """Cache response data."""
        # Implement LRU eviction if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest_key]
        
        self.cache[key] = {
            "data": data,
            "timestamp": time.time()
        }
    
    def clear(self):
        """Clear all cached responses."""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        valid_entries = sum(
            1 for entry in self.cache.values()
            if current_time - entry["timestamp"] <= self.ttl_seconds
        )
        
        return {
            "total_entries": len(self.cache),
            "valid_entries": valid_entries,
            "cache_size_mb": self._estimate_size(),
            "hit_rate": getattr(self, '_hit_count', 0) / max(getattr(self, '_access_count', 1), 1) * 100
        }
    
    def _estimate_size(self) -> float:
        """Estimate cache size in MB."""
        import sys
        total_size = sum(sys.getsizeof(entry) for entry in self.cache.values())
        return total_size / 1024 / 1024


class UIPerformanceOptimizer:
    """UI responsiveness optimization."""
    
    def __init__(self):
        self.render_times: List[float] = []
        self.component_cache = {}
    
    def measure_render_time(self, func: Callable) -> Callable:
        """Decorator to measure UI component render time."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            render_time = time.time() - start_time
            
            self.render_times.append(render_time)
            if len(self.render_times) > 100:
                self.render_times = self.render_times[-100:]
            
            if render_time > 0.5:  # Log slow renders
                logger.warning(f"Slow UI render: {func.__name__} took {render_time:.2f}s")
            
            return result
        
        return wrapper
    
    @lru_cache(maxsize=50)
    def cached_component(self, component_id: str, data_hash: str, render_func: Callable):
        """Cache UI component rendering."""
        return render_func()
    
    def optimize_dataframe_display(self, df, max_rows: int = 1000):
        """Optimize large dataframe display."""
        if len(df) > max_rows:
            st.warning(f"Displaying first {max_rows} rows of {len(df)} total rows for performance")
            return df.head(max_rows)
        return df
    
    def get_render_stats(self) -> Dict[str, float]:
        """Get UI rendering statistics."""
        if not self.render_times:
            return {"error": "No render times recorded"}
        
        return {
            "avg_render_time": sum(self.render_times) / len(self.render_times),
            "max_render_time": max(self.render_times),
            "min_render_time": min(self.render_times),
            "total_renders": len(self.render_times)
        }


class PerformanceMonitor:
    """Comprehensive performance monitoring."""
    
    def __init__(self):
        self.memory_optimizer = MemoryOptimizer()
        self.api_optimizer = APIPerformanceOptimizer()
        self.ui_optimizer = UIPerformanceOptimizer()
        self.metrics_history: List[PerformanceMetrics] = []
        self.monitoring_active = False
    
    def start_monitoring(self, interval: int = 30):
        """Start comprehensive performance monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        
        def monitor():
            while self.monitoring_active:
                try:
                    metrics = self.collect_metrics()
                    self.metrics_history.append(metrics)
                    
                    # Keep only recent metrics (last 100 samples)
                    if len(self.metrics_history) > 100:
                        self.metrics_history = self.metrics_history[-100:]
                    
                    # Auto-optimize if needed
                    self.auto_optimize(metrics)
                    
                    time.sleep(interval)
                
                except Exception as e:
                    logger.error(f"Performance monitoring error: {e}")
                    break
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        logger.info(f"Performance monitoring started with {interval}s interval")
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring_active = False
        logger.info("Performance monitoring stopped")
    
    def collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics."""
        memory_usage = self.memory_optimizer.get_memory_usage()
        api_stats = self.api_optimizer.get_performance_stats()
        ui_stats = self.ui_optimizer.get_render_stats()
        cache_stats = self.api_optimizer.response_cache.get_stats()
        
        return PerformanceMetrics(
            memory_usage_mb=memory_usage["rss_mb"],
            cpu_usage_percent=psutil.cpu_percent(),
            api_call_count=api_stats.get("total_calls", 0),
            api_response_time_avg=api_stats.get("avg_duration", 0),
            ui_render_time=ui_stats.get("avg_render_time", 0),
            cache_hit_rate=cache_stats.get("hit_rate", 0),
            timestamp=datetime.now()
        )
    
    def auto_optimize(self, metrics: PerformanceMetrics):
        """Automatically optimize based on metrics."""
        # Memory optimization
        if metrics.memory_usage_mb > config.MAX_MEMORY_USAGE_MB:
            logger.info("Auto-optimizing memory usage")
            self.memory_optimizer.optimize_memory()
        
        # Cache cleanup if hit rate is low
        if metrics.cache_hit_rate < 10 and len(self.api_optimizer.response_cache.cache) > 50:
            logger.info("Clearing cache due to low hit rate")
            self.api_optimizer.response_cache.clear()
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        if not self.metrics_history:
            return {"error": "No performance data available"}
        
        recent_metrics = self.metrics_history[-10:]  # Last 10 samples
        
        return {
            "current_metrics": self.collect_metrics().__dict__,
            "memory": {
                "current_mb": recent_metrics[-1].memory_usage_mb,
                "avg_mb": sum(m.memory_usage_mb for m in recent_metrics) / len(recent_metrics),
                "max_mb": max(m.memory_usage_mb for m in recent_metrics),
                "threshold_mb": config.MAX_MEMORY_USAGE_MB
            },
            "api_performance": self.api_optimizer.get_performance_stats(),
            "ui_performance": self.ui_optimizer.get_render_stats(),
            "cache_stats": self.api_optimizer.response_cache.get_stats(),
            "recommendations": self.generate_recommendations()
        }
    
    def generate_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        if not self.metrics_history:
            return recommendations
        
        recent_metrics = self.metrics_history[-5:]
        avg_memory = sum(m.memory_usage_mb for m in recent_metrics) / len(recent_metrics)
        avg_api_time = sum(m.api_response_time_avg for m in recent_metrics) / len(recent_metrics)
        
        if avg_memory > config.MAX_MEMORY_USAGE_MB * 0.8:
            recommendations.append("Consider reducing batch size or enabling more aggressive memory cleanup")
        
        if avg_api_time > 10:
            recommendations.append("API response times are high. Consider using caching or reducing request frequency")
        
        cache_stats = self.api_optimizer.response_cache.get_stats()
        if cache_stats.get("hit_rate", 0) < 20:
            recommendations.append("Cache hit rate is low. Consider adjusting cache TTL or key generation")
        
        return recommendations


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def optimize_performance(func: Callable) -> Callable:
    """
    Comprehensive performance optimization decorator.
    
    Args:
        func: Function to optimize
        
    Returns:
        Optimized function with monitoring and caching
    """
    # Apply multiple optimizations
    func = performance_monitor.memory_optimizer.optimize_memory(func)
    func = performance_monitor.api_optimizer.optimize_api_calls(func)
    func = performance_monitor.ui_optimizer.measure_render_time(func)
    
    return func


def get_performance_dashboard() -> Dict[str, Any]:
    """Get performance dashboard data for UI display."""
    return performance_monitor.get_performance_report()


def start_performance_monitoring():
    """Start global performance monitoring."""
    performance_monitor.start_monitoring()


def stop_performance_monitoring():
    """Stop global performance monitoring."""
    performance_monitor.stop_monitoring()