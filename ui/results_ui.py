"""
결과 표시 및 시각화 UI 컴포넌트
학생 결과 카드, 점수 시각화, 피드백 표시, 채점 시간 추적을 처리합니다.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import statistics

from models.result_model import GradingResult, ElementScore


class ResultsUI:
    """채점 결과 표시 및 시각화를 위한 UI 컨트롤러"""
    
    def __init__(self):
        """결과 UI 컨트롤러를 초기화합니다."""
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """결과 표시를 위한 Streamlit 세션 상태를 초기화합니다."""
        if 'selected_student_result' not in st.session_state:
            st.session_state.selected_student_result = None
        
        if 'results_view_mode' not in st.session_state:
            st.session_state.results_view_mode = "overview"
        
        if 'results_sort_by' not in st.session_state:
            st.session_state.results_sort_by = "total_score"
        
        if 'results_filter_grade' not in st.session_state:
            st.session_state.results_filter_grade = "all"
    
    def render_results_page(self, results: List[GradingResult]):
        """
        모든 시각화 컴포넌트가 포함된 메인 결과 페이지를 렌더링합니다.
        
        Args:
            results: 표시할 채점 결과 목록
        """
        if not results:
            st.info("📋 아직 채점 결과가 없습니다.")
            return
        
        st.markdown("## 📊 채점 결과")
        st.markdown("---")
        
        # 결과 개요 및 통계
        self.render_results_overview(results)
        
        # 보기 모드 선택
        self.render_view_mode_selector()
        
        # 선택된 보기 모드에 따라 콘텐츠 렌더링
        if st.session_state.results_view_mode == "overview":
            self.render_overview_dashboard(results)
        elif st.session_state.results_view_mode == "individual":
            self.render_individual_results(results)
        
        # 내보내기 옵션
        self.render_export_options(results)
    
    def render_results_overview(self, results: List[GradingResult]):
        """주요 지표가 포함된 상위 수준 결과 개요를 렌더링합니다."""
        st.markdown("### 📈 전체 개요")
        
        # 상대등급 계산 및 설정
        grade_mapping = GradingResult.calculate_relative_grades(results)
        for result in results:
            key = f"{result.student_name}_{result.student_class_number}"
            if key in grade_mapping:
                result.set_relative_grade(grade_mapping[key])
        
        # 요약 통계 계산
        total_students = len(results)
        avg_score = statistics.mean([r.percentage for r in results])
        avg_time = statistics.mean([r.grading_time_seconds for r in results])
        total_time = sum([r.grading_time_seconds for r in results])
        
        # 등급 분포
        grade_counts = {}
        for result in results:
            grade = result.get_relative_grade()
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        # 컬럼에 지표 표시
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "총 학생 수",
                total_students,
                help="채점이 완료된 전체 학생 수"
            )
        
        with col2:
            avg_total_score = sum(r.total_score for r in results) / len(results)
            avg_max_score = sum(r.total_max_score for r in results) / len(results)
            st.metric(
                "평균 점수",
                f"{avg_total_score:.1f}/{avg_max_score:.1f}",
                help="전체 학생의 평균 점수 (실제 점수)"
            )
        
        with col3:
            st.metric(
                "평균 채점시간",
                f"{avg_time:.1f}초",
                help="학생 1명당 평균 채점 소요시간"
            )
        
        with col4:
            minutes, seconds = divmod(int(total_time), 60)
            st.metric(
                "총 채점시간",
                f"{minutes}분 {seconds}초",
                help="전체 채점에 소요된 총 시간"
            )
        
        with col5:
            most_common_grade = max(grade_counts, key=grade_counts.get) if grade_counts else "N/A"
            st.metric(
                "최다 등급",
                f"{most_common_grade}등급",
                help="가장 많은 학생이 받은 등급"
            )
        
        # Grade distribution chart
        if grade_counts:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Create grade distribution pie chart
                fig = px.pie(
                    values=list(grade_counts.values()),
                    names=list(grade_counts.keys()),
                    title="등급 분포 (한국 내신 5등급제)",
                    color_discrete_map={
                        '1': '#28a745',  # 1등급: 녹색
                        '2': '#17a2b8',  # 2등급: 청색
                        '3': '#ffc107',  # 3등급: 황색
                        '4': '#fd7e14',  # 4등급: 주황색
                        '5': '#dc3545',  # 5등급: 적색
                        '미정': '#6c757d'  # 미정: 회색
                    }
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True, key="grade_distribution_pie")
            
            with col2:
                st.markdown("**등급별 학생 수:**")
                grade_descriptions = {
                    '1': '1등급 (상위 10%)',
                    '2': '2등급 (상위 34%)', 
                    '3': '3등급 (상위 66%)',
                    '4': '4등급 (상위 87%)',
                    '5': '5등급 (상위 100%)'
                }
                for grade in ['1', '2', '3', '4', '5']:
                    count = grade_counts.get(grade, 0)
                    if count > 0:
                        percentage = (count / total_students) * 100
                        grade_desc = grade_descriptions.get(grade, f"{grade}등급")
                        st.write(f"**{grade_desc}**: {count}명 ({percentage:.1f}%)")
    
    def render_view_mode_selector(self):
        """Render view mode selection tabs."""
        st.markdown("---")
        
        view_modes = {
            "overview": "📊 전체 보기",
            "individual": "👤 개별 결과"
        }
        
        selected_mode = st.radio(
            "보기 모드 선택:",
            options=list(view_modes.keys()),
            format_func=lambda x: view_modes[x],
            horizontal=True,
            key="view_mode_selector"
        )
        
        st.session_state.results_view_mode = selected_mode
    
    def render_overview_dashboard(self, results: List[GradingResult]):
        """Render overview dashboard with student result cards."""
        st.markdown("### 📋 학생별 결과 카드")
        
        # Sorting and filtering options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            sort_options = {
                "total_score": "총점 순",
                "percentage": "백분율 순", 
                "student_name": "이름 순",
                "grading_time_seconds": "채점시간 순"
            }
            sort_by = st.selectbox(
                "정렬 기준:",
                options=list(sort_options.keys()),
                format_func=lambda x: sort_options[x],
                key="results_sort_selector"
            )
            st.session_state.results_sort_by = sort_by
        
        with col2:
            sort_order = st.radio(
                "정렬 순서:",
                options=["desc", "asc"],
                format_func=lambda x: "내림차순" if x == "desc" else "오름차순",
                horizontal=True,
                key="sort_order"
            )
        
        with col3:
            grade_filter = st.selectbox(
                "등급 필터:",
                options=["all", "1", "2", "3", "4", "5"],
                format_func=lambda x: "전체" if x == "all" else f"{x}등급",
                key="grade_filter"
            )
            st.session_state.results_filter_grade = grade_filter
        
        # Apply sorting and filtering
        filtered_results = self.filter_and_sort_results(results, sort_by, sort_order, grade_filter)
        
        # Display result cards
        self.render_student_result_cards(filtered_results)
    
    def render_individual_results(self, results: List[GradingResult]):
        """Render detailed individual student results."""
        st.markdown("### 👤 개별 학생 상세 결과")
        
        # Student selection
        student_options = {f"{r.student_name} ({r.student_class_number})": r for r in results}
        selected_student_key = st.selectbox(
            "학생 선택:",
            options=list(student_options.keys()),
            key="individual_student_selector"
        )
        
        if selected_student_key:
            selected_result = student_options[selected_student_key]
            st.session_state.selected_student_result = selected_result
            
            # Render detailed student result
            self.render_detailed_student_result(selected_result)
    

    
    def render_student_result_cards(self, results: List[GradingResult]):
        """Render student result cards in a grid layout."""
        # Display results in cards (3 per row)
        for i in range(0, len(results), 3):
            cols = st.columns(3)
            
            for j, col in enumerate(cols):
                if i + j < len(results):
                    result = results[i + j]
                    
                    with col:
                        self.render_student_card(result)
    
    def render_student_card(self, result: GradingResult):
        """
        Render individual student result card.
        Implements Requirements 6.1, 6.2 - student result display with scores and feedback
        """
        # Determine card color based on grade
        grade_colors = {
            '1': '#d4edda',  # Light green (1등급)
            '2': '#d1ecf1',  # Light blue (2등급)
            '3': '#fff3cd',  # Light yellow (3등급)
            '4': '#ffeaa7',  # Light orange (4등급)
            '5': '#f8d7da',  # Light red (5등급)
            '미정': '#f8f9fa'  # Light gray (미정)
        }
        
        card_color = grade_colors.get(result.get_relative_grade(), '#f8f9fa')
        
        # Create card container
        with st.container():
            st.markdown(
                f"""
                <div style="
                    background-color: {card_color};
                    padding: 1rem;
                    border-radius: 0.5rem;
                    border: 1px solid #dee2e6;
                    margin-bottom: 1rem;
                ">
                """,
                unsafe_allow_html=True
            )
            
            # Student header
            st.markdown(f"**🎓 {result.student_name}** ({result.student_class_number})")
            
            # Score summary
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "총점",
                    f"{result.total_score}/{result.total_max_score}",
                    delta=f"{result.percentage:.1f}%"
                )
            
            with col2:
                grade_display = result.get_relative_grade()
                if grade_display != '미정':
                    grade_display += "등급"
                st.metric(
                    "등급",
                    grade_display,
                    delta=f"{result.grading_time_seconds:.1f}초"
                )
            
            # Element scores visualization
            if result.element_scores:
                st.markdown("**평가 요소별 점수:**")
                
                # Create mini bar chart for element scores
                element_names = [e.element_name for e in result.element_scores]
                element_percentages = [e.percentage for e in result.element_scores]
                
                # Simple progress bars for each element
                for element in result.element_scores:
                    percentage = element.percentage
                    st.progress(
                        percentage / 100,
                        text=f"{element.element_name}: {element.score}/{element.max_score} ({percentage:.1f}%)"
                    )
            
            # Feedback in expandable box
            if result.overall_feedback or result.element_scores:
                with st.expander("💬 피드백 보기"):
                    # Element-specific feedback
                    if result.element_scores:
                        for element in result.element_scores:
                            element_reasoning = getattr(element, 'reasoning', '')
                            element_feedback = getattr(element, 'feedback', '')
                            
                            if element_reasoning or element_feedback:
                                st.markdown(f"**{element.element_name}**")
                                if element_reasoning:
                                    st.markdown(f"*판단 근거:* {element_reasoning}")
                                if element_feedback:
                                    st.markdown(f"*피드백:* {element_feedback}")
                                st.markdown("---")
                    
                    # Overall feedback
                    if result.overall_feedback:
                        st.markdown("**전체 피드백**")
                        st.markdown(result.overall_feedback)
            
            # Grading time and timestamp
            col1, col2 = st.columns(2)
            
            with col1:
                st.caption(f"⏱️ 채점시간: {result.grading_time_seconds:.1f}초")
            
            with col2:
                if result.graded_at:
                    st.caption(f"📅 {result.graded_at.strftime('%H:%M:%S')}")
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    def render_detailed_student_result(self, result: GradingResult):
        """
        Render detailed view of individual student result.
        Implements Requirements 6.1, 6.2 - detailed score breakdown and feedback
        """
        # Student header with comprehensive info
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(f"## 🎓 {result.student_name} ({result.student_class_number})")
        
        with col2:
            st.metric("총점", f"{result.total_score}/{result.total_max_score}")
        
        with col3:
            grade_display = result.get_relative_grade()
            if grade_display != '미정':
                grade_display += "등급"
            st.metric("등급", grade_display)
        
        # Performance summary
        st.markdown("### 📊 성과 요약")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("획득 점수", f"{result.total_score}/{result.total_max_score}")
        
        with col2:
            st.metric("채점 소요시간", f"{result.grading_time_seconds:.1f}초")
        
        with col3:
            if result.graded_at:
                st.metric("채점 완료시각", result.graded_at.strftime('%H:%M:%S'))
        
        with col4:
            avg_element_score = statistics.mean([e.percentage for e in result.element_scores]) if result.element_scores else 0
            st.metric("평균 요소 점수", f"{avg_element_score:.1f}%")
        
        # Element scores detailed breakdown
        if result.element_scores:
            st.markdown("### 📋 평가 요소별 상세 점수")
            
            # Create detailed visualization
            self.render_element_scores_chart(result.element_scores)
            
            # Element details table
            st.markdown("#### 📝 요소별 상세 정보")
            
            for i, element in enumerate(result.element_scores):
                with st.expander(
                    f"**{element.element_name}**: {element.score}/{element.max_score}점 ({element.percentage:.1f}%)",
                    expanded=(i == 0)
                ):
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        # Score visualization
                        fig = go.Figure(go.Indicator(
                            mode = "gauge+number+delta",
                            value = element.percentage,
                            domain = {'x': [0, 1], 'y': [0, 1]},
                            title = {'text': "점수 (%)"},
                            delta = {'reference': 80},
                            gauge = {
                                'axis': {'range': [None, 100]},
                                'bar': {'color': "darkblue"},
                                'steps': [
                                    {'range': [0, 60], 'color': "lightgray"},
                                    {'range': [60, 80], 'color': "gray"},
                                    {'range': [80, 100], 'color': "lightgreen"}
                                ],
                                'threshold': {
                                    'line': {'color': "red", 'width': 4},
                                    'thickness': 0.75,
                                    'value': 90
                                }
                            }
                        ))
                        fig.update_layout(height=200)
                        st.plotly_chart(fig, use_container_width=True, key=f"element_gauge_{result.student_name}_{result.student_class_number}_{i}")
                    
                    with col2:
                        st.markdown("**점수 정보:**")
                        st.write(f"- 획득 점수: {element.score}점")
                        st.write(f"- 만점: {element.max_score}점")
                        st.write(f"- 백분율: {element.percentage:.1f}%")
                        
                        if element.feedback:
                            st.markdown("**상세 피드백:**")
                            st.info(element.feedback)
        
        # Overall feedback
        if result.overall_feedback:
            st.markdown("### 💬 전체 피드백")
            st.markdown(
                f"""
                <div style="
                    background-color: #ffffff;
                    color: #000000;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    border-left: 4px solid #007bff;
                    border: 1px solid #e0e0e0;
                ">
                    {result.overall_feedback}
                </div>
                """,
                unsafe_allow_html=True
            )
        
        # Performance insights
        self.render_student_performance_insights(result)
    
    def render_element_scores_chart(self, element_scores: List[ElementScore]):
        """Render chart visualization for element scores."""
        # Prepare data for visualization
        element_names = [e.element_name for e in element_scores]
        scores = [e.score for e in element_scores]
        max_scores = [e.max_score for e in element_scores]
        percentages = [e.percentage for e in element_scores]
        
        # Create bar chart for scores vs max scores
        fig = go.Figure()
        
        # Bar chart for scores vs max scores
        fig.add_trace(
            go.Bar(name='획득 점수', x=element_names, y=scores, marker_color='lightblue')
        )
        fig.add_trace(
            go.Bar(name='만점', x=element_names, y=max_scores, marker_color='lightgray', opacity=0.6)
        )
        
        fig.update_layout(
            height=400,
            showlegend=True,
            title_text="평가 요소별 성과 분석",
            xaxis_title="평가 요소",
            yaxis_title="점수"
        )
        
        st.plotly_chart(fig, use_container_width=True, key="element_scores_chart")
    
    def render_student_performance_insights(self, result: GradingResult):
        """Render performance insights and recommendations for the student."""
        st.markdown("### 🎯 성과 분석 및 개선 제안")
        
        if not result.element_scores:
            st.info("평가 요소 데이터가 없어 상세 분석을 제공할 수 없습니다.")
            return
        
        # Calculate insights
        element_percentages = [e.percentage for e in result.element_scores]
        avg_performance = statistics.mean(element_percentages)
        
        # Find strengths and weaknesses
        strengths = [e for e in result.element_scores if e.percentage >= 80]
        needs_improvement = [e for e in result.element_scores if e.percentage < 60]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🌟 강점 영역")
            if strengths:
                for strength in strengths:
                    st.success(f"✅ **{strength.element_name}**: {strength.percentage:.1f}% (우수)")
            else:
                st.info("80% 이상의 우수한 성과를 보인 영역이 없습니다.")
        
        with col2:
            st.markdown("#### 📈 개선 필요 영역")
            if needs_improvement:
                for weakness in needs_improvement:
                    st.warning(f"⚠️ **{weakness.element_name}**: {weakness.percentage:.1f}% (개선 필요)")
            else:
                st.success("모든 영역에서 60% 이상의 성과를 보였습니다!")
        
        # Performance level assessment
        st.markdown("#### 📊 전체 성과 수준")
        
        if avg_performance >= 90:
            st.success("🏆 **최우수**: 모든 영역에서 뛰어난 성과를 보였습니다!")
        elif avg_performance >= 80:
            st.success("🥇 **우수**: 대부분 영역에서 좋은 성과를 보였습니다.")
        elif avg_performance >= 70:
            st.info("🥈 **양호**: 전반적으로 괜찮은 성과입니다. 일부 영역의 개선이 필요합니다.")
        elif avg_performance >= 60:
            st.warning("🥉 **보통**: 기본 수준은 달성했으나 전반적인 개선이 필요합니다.")
        else:
            st.error("📚 **개선 필요**: 전반적인 학습과 복습이 필요합니다.")
        
        # 상대등급 정보 표시
        current_grade = result.get_relative_grade()
        if current_grade != '미정':
            grade_info = {
                '1': '상위 10% (1등급)',
                '2': '상위 34% (2등급)',
                '3': '상위 66% (3등급)', 
                '4': '상위 87% (4등급)',
                '5': '상위 100% (5등급)'
            }
            if current_grade in grade_info:
                st.info(f"📊 **상대등급**: {grade_info[current_grade]}")
    

    

    

    

    
    def render_export_options(self, results: List[GradingResult]):
        """Render export options for results."""
        st.markdown("---")
        st.markdown("### 📥 결과 내보내기")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button(
                "📊 Excel 다운로드",
                key="export_excel",
                use_container_width=True,
                type="primary"
            ):
                self.export_to_excel(results)
        
        with col2:
            if st.button(
                "📈 분석 리포트 생성",
                key="export_report",
                use_container_width=True
            ):
                self.generate_analysis_report(results)
        
        with col3:
            if st.button(
                "📋 요약 통계 보기",
                key="view_summary",
                use_container_width=True
            ):
                self.show_summary_statistics(results)
    
    def filter_and_sort_results(self, results: List[GradingResult], sort_by: str, sort_order: str, grade_filter: str) -> List[GradingResult]:
        """
        Filter and sort results based on user preferences.
        
        Args:
            results: List of grading results
            sort_by: Field to sort by
            sort_order: 'asc' or 'desc'
            grade_filter: Grade to filter by or 'all'
            
        Returns:
            Filtered and sorted list of results
        """
        # Apply grade filter
        filtered_results = results
        if grade_filter != "all":
            filtered_results = [r for r in results if r.get_relative_grade() == grade_filter]
        
        # Apply sorting
        reverse = (sort_order == "desc")
        
        if sort_by == "student_name":
            filtered_results.sort(key=lambda x: x.student_name, reverse=reverse)
        elif sort_by == "total_score":
            filtered_results.sort(key=lambda x: x.total_score, reverse=reverse)
        elif sort_by == "percentage":
            filtered_results.sort(key=lambda x: x.percentage, reverse=reverse)
        elif sort_by == "grading_time_seconds":
            filtered_results.sort(key=lambda x: x.grading_time_seconds, reverse=reverse)
        
        return filtered_results
    
    def export_to_excel(self, results: List[GradingResult]):
        """
        Export results to Excel file and provide download.
        Implements Requirements 6.3, 6.4 - Excel export functionality
        """
        try:
            from services.export_service import create_export_service
            
            export_service = create_export_service()
            excel_path = export_service.create_results_excel(results)
            
            # Read file for download
            with open(excel_path, 'rb') as file:
                excel_data = file.read()
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"채점결과_{timestamp}.xlsx"
            
            # Provide download button
            st.download_button(
                label="📥 Excel 파일 다운로드",
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel"
            )
            
            st.success("✅ Excel 파일이 생성되었습니다. 다운로드 버튼을 클릭하세요.")
            
        except Exception as e:
            st.error(f"❌ Excel 파일 생성 중 오류가 발생했습니다: {str(e)}")
    
    def generate_analysis_report(self, results: List[GradingResult]):
        """Generate comprehensive analysis report."""
        st.markdown("### 📈 분석 리포트")
        
        if not results:
            st.info("분석할 데이터가 없습니다.")
            return
        
        import statistics
        
        # Performance summary
        percentages = [r.percentage for r in results]
        times = [r.grading_time_seconds for r in results]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 성과 분석")
            st.write(f"- **평균 점수**: {statistics.mean(percentages):.1f}%")
            st.write(f"- **중앙값**: {statistics.median(percentages):.1f}%")
            st.write(f"- **표준편차**: {statistics.stdev(percentages) if len(percentages) > 1 else 0:.1f}")
            st.write(f"- **최고점**: {max(percentages):.1f}%")
            st.write(f"- **최저점**: {min(percentages):.1f}%")
        
        with col2:
            st.markdown("#### ⏱️ 효율성 분석")
            st.write(f"- **평균 채점시간**: {statistics.mean(times):.1f}초")
            st.write(f"- **총 채점시간**: {sum(times):.1f}초")
            st.write(f"- **최단 시간**: {min(times):.1f}초")
            st.write(f"- **최장 시간**: {max(times):.1f}초")
        
        # Grade distribution insights
        grade_counts = {}
        for result in results:
            grade = result.get_relative_grade()
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        st.markdown("#### 🎯 등급 분포 분석")
        total_students = len(results)
        
        grade_descriptions = {
            '1': '1등급 (상위 10%)',
            '2': '2등급 (상위 34%)',
            '3': '3등급 (상위 66%)',
            '4': '4등급 (상위 87%)',
            '5': '5등급 (상위 100%)'
        }
        
        for grade in ['1', '2', '3', '4', '5']:
            count = grade_counts.get(grade, 0)
            percentage = (count / total_students * 100) if total_students > 0 else 0
            if count > 0:
                grade_desc = grade_descriptions.get(grade, f"{grade}등급")
                st.write(f"- **{grade_desc}**: {count}명 ({percentage:.1f}%)")
        
        # Performance recommendations
        st.markdown("#### 💡 개선 제안")
        
        if statistics.mean(percentages) >= 80:
            st.success("🎉 전체적으로 우수한 성과를 보이고 있습니다!")
        elif statistics.mean(percentages) >= 70:
            st.info("📈 양호한 성과입니다. 일부 영역의 개선을 통해 더 나은 결과를 얻을 수 있습니다.")
        else:
            st.warning("📚 전반적인 학습 지도가 필요합니다. 기본 개념 복습을 권장합니다.")
    
    def show_summary_statistics(self, results: List[GradingResult]):
        """Show detailed summary statistics in a modal-like display."""
        st.markdown("### 📋 요약 통계")
        
        if not results:
            st.info("통계를 계산할 데이터가 없습니다.")
            return
        
        import statistics
        
        # Create comprehensive statistics
        percentages = [r.percentage for r in results]
        times = [r.grading_time_seconds for r in results]
        
        # Overall statistics table
        stats_data = {
            "지표": [
                "총 학생 수", "평균 점수 (%)", "중앙값 (%)", "표준편차", 
                "최고점 (%)", "최저점 (%)", "평균 채점시간 (초)", "총 채점시간 (초)"
            ],
            "값": [
                len(results),
                round(statistics.mean(percentages), 1),
                round(statistics.median(percentages), 1),
                round(statistics.stdev(percentages) if len(percentages) > 1 else 0, 1),
                round(max(percentages), 1),
                round(min(percentages), 1),
                round(statistics.mean(times), 1),
                round(sum(times), 1)
            ]
        }
        
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
        # Element performance statistics
        if results[0].element_scores:
            st.markdown("#### 평가 요소별 통계")
            
            element_data = {}
            for result in results:
                for element in result.element_scores:
                    if element.element_name not in element_data:
                        element_data[element.element_name] = []
                    element_data[element.element_name].append(element.percentage)
            
            element_stats = []
            for element_name, percentages in element_data.items():
                element_stats.append({
                    "평가요소": element_name,
                    "평균 (%)": round(statistics.mean(percentages), 1),
                    "중앙값 (%)": round(statistics.median(percentages), 1),
                    "표준편차": round(statistics.stdev(percentages) if len(percentages) > 1 else 0, 1),
                    "최고점 (%)": round(max(percentages), 1),
                    "최저점 (%)": round(min(percentages), 1)
                })
            
            element_df = pd.DataFrame(element_stats)
            st.dataframe(element_df, use_container_width=True, hide_index=True)
    

    
    def copy_summary_statistics(self, results: List[GradingResult]):
        """Copy summary statistics to clipboard."""
        if not results:
            st.warning("복사할 결과가 없습니다.")
            return
        
        # Generate summary text
        total_students = len(results)
        avg_score = statistics.mean([r.percentage for r in results])
        avg_time = statistics.mean([r.grading_time_seconds for r in results])
        
        grade_counts = {}
        for result in results:
            grade = result.grade_letter
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        summary_text = f"""
채점 결과 요약 통계
==================
총 학생 수: {total_students}명
평균 점수: {avg_score:.1f}%
평균 채점시간: {avg_time:.1f}초

등급 분포:
"""
        
        for grade in ['A', 'B', 'C', 'D', 'F']:
            count = grade_counts.get(grade, 0)
            if count > 0:
                percentage = (count / total_students) * 100
                summary_text += f"- {grade}등급: {count}명 ({percentage:.1f}%)\n"
        
        # Display in text area for easy copying
        st.text_area(
            "요약 통계 (복사하여 사용하세요):",
            value=summary_text,
            height=200,
            key="summary_stats_text"
        )
        
        st.info("💡 위 텍스트를 선택하여 복사할 수 있습니다.")


def create_results_ui() -> ResultsUI:
    """
    Factory function to create ResultsUI instance.
    
    Returns:
        ResultsUI: Configured ResultsUI instance
    """
    return ResultsUI()