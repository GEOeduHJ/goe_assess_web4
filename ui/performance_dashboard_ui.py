"""
Performance Dashboard UI for Geography Auto-Grading System

This module provides UI components for displaying performance metrics,
system status, and optimization controls.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pandas as pd

from utils.performance_optimizer import performance_monitor, get_performance_dashboard
from config import config


class PerformanceDashboardUI:
    """UI components for performance monitoring and optimization."""
    
    def __init__(self):
        """Initialize performance dashboard UI."""
        self.refresh_interval = 5  # seconds
    
    def render_performance_dashboard(self):
        """Render the main performance dashboard."""
        st.markdown("## 📊 성능 모니터링 대시보드")
        
        # Get performance data
        perf_data = get_performance_dashboard()
        
        if "error" in perf_data:
            st.warning("⚠️ 성능 데이터를 사용할 수 없습니다. 모니터링을 시작해주세요.")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 모니터링 시작", type="primary"):
                    from utils.performance_optimizer import start_performance_monitoring
                    start_performance_monitoring()
                    st.success("✅ 성능 모니터링이 시작되었습니다.")
                    st.rerun()
            
            with col2:
                if st.button("🔄 새로고침"):
                    st.rerun()
            
            return
        
        # Performance overview cards
        self.render_performance_overview(perf_data)
        
        # Detailed metrics
        col1, col2 = st.columns(2)
        
        with col1:
            self.render_memory_metrics(perf_data)
            self.render_cache_metrics(perf_data)
        
        with col2:
            self.render_api_metrics(perf_data)
            self.render_ui_metrics(perf_data)
        
        # Recommendations
        self.render_recommendations(perf_data)
        
        # Control panel
        self.render_control_panel()
    
    def render_performance_overview(self, perf_data: Dict[str, Any]):
        """Render performance overview cards."""
        st.markdown("### 📈 성능 개요")
        
        current_metrics = perf_data.get("current_metrics", {})
        memory_info = perf_data.get("memory", {})
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            memory_usage = memory_info.get("current_mb", 0)
            memory_threshold = memory_info.get("threshold_mb", config.MAX_MEMORY_USAGE_MB)
            memory_percent = (memory_usage / memory_threshold) * 100
            
            # Color based on usage
            if memory_percent < 70:
                color = "normal"
            elif memory_percent < 90:
                color = "warning"
            else:
                color = "error"
            
            st.metric(
                label="💾 메모리 사용량",
                value=f"{memory_usage:.0f}MB",
                delta=f"{memory_percent:.1f}% of limit"
            )
            
            if color == "error":
                st.error("⚠️ 메모리 사용량 높음")
            elif color == "warning":
                st.warning("⚠️ 메모리 사용량 주의")
        
        with col2:
            cpu_usage = current_metrics.get("cpu_usage_percent", 0)
            st.metric(
                label="🖥️ CPU 사용률",
                value=f"{cpu_usage:.1f}%"
            )
            
            if cpu_usage > 80:
                st.error("⚠️ CPU 사용률 높음")
            elif cpu_usage > 60:
                st.warning("⚠️ CPU 사용률 주의")
        
        with col3:
            api_stats = perf_data.get("api_performance", {})
            api_calls = api_stats.get("total_calls", 0)
            success_rate = api_stats.get("success_rate", 0)
            
            st.metric(
                label="🔗 API 호출",
                value=f"{api_calls}회",
                delta=f"{success_rate:.1f}% 성공률"
            )
            
            if success_rate < 90:
                st.error("⚠️ API 성공률 낮음")
            elif success_rate < 95:
                st.warning("⚠️ API 성공률 주의")
        
        with col4:
            cache_stats = perf_data.get("cache_stats", {})
            hit_rate = cache_stats.get("hit_rate", 0)
            
            st.metric(
                label="💨 캐시 적중률",
                value=f"{hit_rate:.1f}%"
            )
            
            if hit_rate < 20:
                st.warning("⚠️ 캐시 효율성 낮음")
    
    def render_memory_metrics(self, perf_data: Dict[str, Any]):
        """Render memory usage metrics."""
        st.markdown("#### 💾 메모리 사용량")
        
        memory_info = perf_data.get("memory", {})
        
        if memory_info:
            # Memory usage chart
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=memory_info.get("current_mb", 0),
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "메모리 사용량 (MB)"},
                delta={'reference': memory_info.get("avg_mb", 0)},
                gauge={
                    'axis': {'range': [None, memory_info.get("threshold_mb", 1024)]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, memory_info.get("threshold_mb", 1024) * 0.7], 'color': "lightgray"},
                        {'range': [memory_info.get("threshold_mb", 1024) * 0.7, memory_info.get("threshold_mb", 1024) * 0.9], 'color': "yellow"},
                        {'range': [memory_info.get("threshold_mb", 1024) * 0.9, memory_info.get("threshold_mb", 1024)], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': memory_info.get("threshold_mb", 1024)
                    }
                }
            ))
            
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
            
            # Memory details
            with st.expander("📊 메모리 상세 정보"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**현재 사용량:** {memory_info.get('current_mb', 0):.1f}MB")
                    st.write(f"**평균 사용량:** {memory_info.get('avg_mb', 0):.1f}MB")
                with col2:
                    st.write(f"**최대 사용량:** {memory_info.get('max_mb', 0):.1f}MB")
                    st.write(f"**임계값:** {memory_info.get('threshold_mb', 0):.1f}MB")
    
    def render_api_metrics(self, perf_data: Dict[str, Any]):
        """Render API performance metrics."""
        st.markdown("#### 🔗 API 성능")
        
        api_stats = perf_data.get("api_performance", {})
        
        if api_stats and "error" not in api_stats:
            # API response time chart
            response_times = [
                api_stats.get("min_duration", 0),
                api_stats.get("avg_duration", 0),
                api_stats.get("max_duration", 0)
            ]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=["최소", "평균", "최대"],
                    y=response_times,
                    marker_color=['green', 'blue', 'red']
                )
            ])
            
            fig.update_layout(
                title="API 응답 시간 (초)",
                yaxis_title="시간 (초)",
                height=300
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # API details
            with st.expander("📊 API 상세 정보"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**총 호출 수:** {api_stats.get('total_calls', 0)}회")
                    st.write(f"**성공률:** {api_stats.get('success_rate', 0):.1f}%")
                with col2:
                    st.write(f"**평균 응답시간:** {api_stats.get('avg_duration', 0):.2f}초")
                    st.write(f"**최근 5분 호출:** {api_stats.get('recent_calls', 0)}회")
        else:
            st.info("📊 API 호출 데이터가 없습니다.")
    
    def render_cache_metrics(self, perf_data: Dict[str, Any]):
        """Render cache performance metrics."""
        st.markdown("#### 💨 캐시 성능")
        
        cache_stats = perf_data.get("cache_stats", {})
        
        if cache_stats and "error" not in cache_stats:
            # Cache hit rate pie chart
            hit_rate = cache_stats.get("hit_rate", 0)
            miss_rate = 100 - hit_rate
            
            fig = go.Figure(data=[go.Pie(
                labels=['캐시 적중', '캐시 미스'],
                values=[hit_rate, miss_rate],
                hole=.3,
                marker_colors=['green', 'red']
            )])
            
            fig.update_layout(
                title="캐시 적중률",
                height=300
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Cache details
            with st.expander("📊 캐시 상세 정보"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**총 엔트리:** {cache_stats.get('total_entries', 0)}개")
                    st.write(f"**유효 엔트리:** {cache_stats.get('valid_entries', 0)}개")
                with col2:
                    st.write(f"**캐시 크기:** {cache_stats.get('cache_size_mb', 0):.2f}MB")
                    st.write(f"**적중률:** {hit_rate:.1f}%")
        else:
            st.info("📊 캐시 데이터가 없습니다.")
    
    def render_ui_metrics(self, perf_data: Dict[str, Any]):
        """Render UI performance metrics."""
        st.markdown("#### 🖥️ UI 성능")
        
        ui_stats = perf_data.get("ui_performance", {})
        
        if ui_stats and "error" not in ui_stats:
            # UI render time metrics
            render_times = {
                "평균 렌더링 시간": ui_stats.get("avg_render_time", 0),
                "최대 렌더링 시간": ui_stats.get("max_render_time", 0),
                "최소 렌더링 시간": ui_stats.get("min_render_time", 0)
            }
            
            fig = go.Figure(data=[
                go.Bar(
                    x=list(render_times.keys()),
                    y=list(render_times.values()),
                    marker_color=['blue', 'red', 'green']
                )
            ])
            
            fig.update_layout(
                title="UI 렌더링 시간 (초)",
                yaxis_title="시간 (초)",
                height=300
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # UI details
            with st.expander("📊 UI 상세 정보"):
                st.write(f"**총 렌더링 횟수:** {ui_stats.get('total_renders', 0)}회")
                st.write(f"**평균 렌더링 시간:** {ui_stats.get('avg_render_time', 0):.3f}초")
                
                if ui_stats.get('avg_render_time', 0) > 0.5:
                    st.warning("⚠️ UI 렌더링이 느립니다. 최적화가 필요할 수 있습니다.")
        else:
            st.info("📊 UI 성능 데이터가 없습니다.")
    
    def render_recommendations(self, perf_data: Dict[str, Any]):
        """Render performance optimization recommendations."""
        recommendations = perf_data.get("recommendations", [])
        
        if recommendations:
            st.markdown("#### 💡 최적화 권장사항")
            
            for i, recommendation in enumerate(recommendations, 1):
                st.info(f"**{i}.** {recommendation}")
        else:
            st.success("✅ 현재 시스템 성능이 양호합니다.")
    
    def render_control_panel(self):
        """Render performance control panel."""
        st.markdown("---")
        st.markdown("#### 🎛️ 성능 제어판")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🧹 메모리 최적화", help="메모리 사용량을 최적화합니다"):
                with st.spinner("메모리 최적화 중..."):
                    result = performance_monitor.memory_optimizer.optimize_memory(force=True)
                    if result["optimized"]:
                        st.success(f"✅ {result['memory_saved_mb']:.1f}MB 메모리 절약")
                    else:
                        st.info("ℹ️ 최적화가 필요하지 않습니다")
        
        with col2:
            if st.button("🗑️ 캐시 정리", help="API 응답 캐시를 정리합니다"):
                performance_monitor.api_optimizer.response_cache.clear()
                st.success("✅ 캐시가 정리되었습니다")
        
        with col3:
            if st.button("📊 성능 리포트", help="상세한 성능 리포트를 생성합니다"):
                self.show_detailed_report()
        
        with col4:
            monitoring_status = performance_monitor.monitoring_active
            if monitoring_status:
                if st.button("⏹️ 모니터링 중지", help="성능 모니터링을 중지합니다"):
                    from utils.performance_optimizer import stop_performance_monitoring
                    stop_performance_monitoring()
                    st.success("✅ 성능 모니터링이 중지되었습니다")
                    st.rerun()
            else:
                if st.button("▶️ 모니터링 시작", help="성능 모니터링을 시작합니다"):
                    from utils.performance_optimizer import start_performance_monitoring
                    start_performance_monitoring()
                    st.success("✅ 성능 모니터링이 시작되었습니다")
                    st.rerun()
    
    def show_detailed_report(self):
        """Show detailed performance report."""
        perf_data = get_performance_dashboard()
        
        with st.expander("📋 상세 성능 리포트", expanded=True):
            st.json(perf_data)
    
    def render_compact_performance_widget(self):
        """Render a compact performance widget for sidebar."""
        st.markdown("### 📊 성능 상태")
        
        perf_data = get_performance_dashboard()
        
        if "error" not in perf_data:
            memory_info = perf_data.get("memory", {})
            current_memory = memory_info.get("current_mb", 0)
            threshold_memory = memory_info.get("threshold_mb", config.MAX_MEMORY_USAGE_MB)
            memory_percent = (current_memory / threshold_memory) * 100
            
            # Memory usage progress bar
            st.write("💾 메모리 사용량")
            st.progress(min(memory_percent / 100, 1.0))
            st.caption(f"{current_memory:.0f}MB / {threshold_memory:.0f}MB ({memory_percent:.1f}%)")
            
            # API performance
            api_stats = perf_data.get("api_performance", {})
            if "error" not in api_stats:
                success_rate = api_stats.get("success_rate", 0)
                st.write("🔗 API 성공률")
                st.progress(success_rate / 100)
                st.caption(f"{success_rate:.1f}%")
            
            # Cache hit rate
            cache_stats = perf_data.get("cache_stats", {})
            if "error" not in cache_stats:
                hit_rate = cache_stats.get("hit_rate", 0)
                st.write("💨 캐시 적중률")
                st.progress(hit_rate / 100)
                st.caption(f"{hit_rate:.1f}%")
        else:
            st.warning("성능 데이터 없음")


def create_performance_dashboard_ui() -> PerformanceDashboardUI:
    """
    Factory function to create PerformanceDashboardUI instance.
    
    Returns:
        PerformanceDashboardUI: Configured UI instance
    """
    return PerformanceDashboardUI()