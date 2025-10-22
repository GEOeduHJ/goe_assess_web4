"""
동적 루브릭 구성을 위한 루브릭 UI 컴포넌트
평가 기준 생성, 수정, 검증을 처리합니다.
"""

import streamlit as st
from typing import List, Dict, Any, Optional
import json

from models.rubric_model import Rubric, EvaluationElement, EvaluationCriteria


class RubricUI:
    """동적 루브릭 구성을 위한 UI 컨트롤러"""
    
    def __init__(self):
        """루브릭 UI 컨트롤러를 초기화합니다."""
        self.initialize_session_state()
    
    def initialize_session_state(self):
        """루브릭 데이터를 위한 Streamlit 세션 상태를 초기화합니다."""
        if 'rubric' not in st.session_state:
            st.session_state.rubric = Rubric(name="새 루브릭")
        
        if 'rubric_validation_errors' not in st.session_state:
            st.session_state.rubric_validation_errors = []
    
    def render_rubric_builder(self):
        """
        메인 루브릭 빌더 인터페이스를 렌더링합니다.
        요구사항 3.1, 3.2, 3.3, 3.4 구현
        """
        st.markdown("## 📋 평가 루브릭 설정")
        st.markdown("채점에 사용할 평가 요소와 채점 기준을 설정해주세요.")
        
        # 루브릭 관리 버튼
        self.render_rubric_management_buttons()
        
        # 평가 요소 섹션
        self.render_evaluation_elements()
        
        # 새 요소 추가 섹션
        self.render_add_element_section()
        
        # 루브릭 미리보기 및 검증
        self.render_rubric_preview()
        
        # 탐색 버튼
        self.render_rubric_navigation()
    
    def render_rubric_management_buttons(self):
        """Render buttons for rubric management operations."""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🆕 새 루브릭", help="새로운 루브릭을 생성합니다"):
                st.session_state.rubric = Rubric(name="새 루브릭")
                st.session_state.rubric_validation_errors = []
                st.rerun()
        
        with col2:
            if st.button("📁 예시 불러오기", help="예시 루브릭을 불러옵니다"):
                self.load_sample_rubric()
                st.rerun()
        
        with col3:
            if st.session_state.rubric.elements:
                rubric_json = json.dumps(st.session_state.rubric.to_dict(), ensure_ascii=False, indent=2)
                st.download_button(
                    "💾 루브릭 저장",
                    data=rubric_json,
                    file_name="rubric.json",
                    mime="application/json",
                    help="현재 루브릭을 JSON 파일로 저장합니다"
                )
        
        with col4:
            uploaded_rubric = st.file_uploader(
                "📂 루브릭 불러오기",
                type=['json'],
                key="rubric_upload",
                help="저장된 루브릭 JSON 파일을 불러옵니다"
            )
            
            if uploaded_rubric:
                try:
                    rubric_data = json.load(uploaded_rubric)
                    st.session_state.rubric = Rubric.from_dict(rubric_data)
                    st.success("✅ 루브릭이 성공적으로 불러와졌습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 루브릭 파일을 불러오는 중 오류가 발생했습니다: {str(e)}")
    
    def load_sample_rubric(self):
        """Load a sample rubric for demonstration."""
        sample_rubric = Rubric(name="예시 루브릭")
        
        # Sample element 1: 계절풍
        monsoon_element = EvaluationElement(name="계절풍")
        monsoon_element.add_criteria(score=1, description="모범답안과 유사하게 계절풍의 이동 방향을 \"해양에서 대륙\"으로 지시하는 화살표로 정확하게 표시함")
        monsoon_element.add_criteria(score=0, description="모범답안과 유사하게 계절풍의 이동 방향을 \"해양에서 대륙\"으로 지시하는 화살표로 정확하게 표시하지 못함")
        
        # Sample element 2: 히말라야산맥
        himalaya_element = EvaluationElement(name="히말라야산맥")
        himalaya_element.add_criteria(score=2, description="모범답안과 유사하게 히말라야 산맥이 위치한 인도 북부, 네팔 국경 일대를 중심으로 한 사각형으로 표시함")
        himalaya_element.add_criteria(score=1, description="사각형이 히말라야 산맥 일대를 포함하지만, 모범답안과 다르게 사각형의 범위가 지나치게 많은 범위를 포함하거나 지나치게 작아 판단이 어려움")
        himalaya_element.add_criteria(score=0, description="모범답안과 다르게 히말라야 산맥 일대를 사각형으로 표시하지 못함")
        
        sample_rubric.add_element(monsoon_element)
        sample_rubric.add_element(himalaya_element)
        st.session_state.rubric = sample_rubric
        
        # Also set rubric in grading session
        if 'grading_session' in st.session_state:
            st.session_state.grading_session.rubric = sample_rubric
        
        st.success("✅ 예시 루브릭을 불러왔습니다!")
    
    def render_evaluation_elements(self):
        """Render existing evaluation elements with edit/delete functionality."""
        if not st.session_state.rubric.elements:
            st.info("📝 아직 평가 요소가 없습니다. 아래에서 새로운 평가 요소를 추가해주세요.")
            return
        
        st.markdown("### 📊 현재 평가 요소")
        
        for i, element in enumerate(st.session_state.rubric.elements):
            with st.expander(f"📋 {element.name} (최대 {element.max_score}점)", expanded=True):
                self.render_element_editor(i, element)
    
    def render_element_editor(self, element_index: int, element: EvaluationElement):
        """Render editor for a single evaluation element."""
        # Element name editor
        col1, col2 = st.columns([3, 1])
        
        with col1:
            new_name = st.text_input(
                "평가 요소 이름",
                value=element.name,
                key=f"element_name_{element_index}",
                help="평가 요소의 이름을 입력하세요"
            )
            if new_name != element.name:
                element.name = new_name
        
        with col2:
            if st.button(
                "🗑️ 삭제",
                key=f"delete_element_{element_index}",
                help="이 평가 요소를 삭제합니다",
                type="secondary"
            ):
                st.session_state.rubric.elements.pop(element_index)
                # Update rubric total score after deleting element
                st.session_state.rubric.update_total_score()
                st.rerun()
        
        # Criteria editor
        st.markdown("**채점 기준:**")
        
        # Display existing criteria
        for j, criteria in enumerate(element.criteria):
            self.render_criteria_editor(element_index, j, criteria)
        
        # Add new criteria button
        if st.button(
            "➕ 채점 기준 추가",
            key=f"add_criteria_{element_index}",
            help="새로운 채점 기준을 추가합니다"
        ):
            element.add_criteria(score=0, description="기준을 입력하세요")
            # Update rubric total score after adding new criteria
            st.session_state.rubric.update_total_score()
            st.rerun()
    
    def render_criteria_editor(self, element_index: int, criteria_index: int, criteria: EvaluationCriteria):
        """Render editor for a single evaluation criteria."""
        col1, col2, col3 = st.columns([1, 4, 1])
        
        with col1:
            new_score = st.number_input(
                "점수",
                min_value=0,
                max_value=100,
                value=criteria.score,
                key=f"criteria_score_{element_index}_{criteria_index}",
                help="이 기준에 해당하는 점수를 입력하세요"
            )
            if new_score != criteria.score:
                criteria.score = new_score
                # Update element max score and rubric total score
                st.session_state.rubric.elements[element_index]._calculate_max_score()
                st.session_state.rubric.update_total_score()
        
        with col2:
            new_description = st.text_area(
                "기준 설명",
                value=criteria.description,
                key=f"criteria_desc_{element_index}_{criteria_index}",
                help="채점 기준에 대한 상세한 설명을 입력하세요",
                height=60
            )
            if new_description != criteria.description:
                criteria.description = new_description
        
        with col3:
            if st.button(
                "🗑️",
                key=f"delete_criteria_{element_index}_{criteria_index}",
                help="이 채점 기준을 삭제합니다"
            ):
                st.session_state.rubric.elements[element_index].criteria.pop(criteria_index)
                # Update element max score and rubric total score after deletion
                st.session_state.rubric.elements[element_index]._calculate_max_score()
                st.session_state.rubric.update_total_score()
                st.rerun()
    
    def render_add_element_section(self):
        """Render section for adding new evaluation elements."""
        st.markdown("---")
        st.markdown("### ➕ 새 평가 요소 추가")
        
        with st.form("add_element_form"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                new_element_name = st.text_input(
                    "평가 요소 이름",
                    placeholder="예: 내용 정확성, 설명의 질, 논리성 등",
                    help="새로운 평가 요소의 이름을 입력하세요"
                )
            
            with col2:
                submitted = st.form_submit_button("➕ 추가", use_container_width=True)
            
            if submitted and new_element_name.strip():
                # Check for duplicate names
                existing_names = [element.name for element in st.session_state.rubric.elements]
                if new_element_name.strip() in existing_names:
                    st.error("❌ 이미 존재하는 평가 요소 이름입니다.")
                else:
                    new_element = EvaluationElement(name=new_element_name.strip())
                    # Add default criteria
                    new_element.add_criteria(score=0, description="기준을 입력하세요")
                    st.session_state.rubric.add_element(new_element)
                    # Update total score after adding element with criteria
                    st.session_state.rubric.update_total_score()
                    st.success(f"✅ '{new_element_name}' 평가 요소가 추가되었습니다!")
                    st.rerun()
            elif submitted and not new_element_name.strip():
                st.error("❌ 평가 요소 이름을 입력해주세요.")
    
    def render_rubric_preview(self):
        """Render rubric preview and validation results."""
        st.markdown("---")
        st.markdown("### 👀 루브릭 미리보기")
        
        # Validate rubric
        validation_errors = self.validate_rubric()
        st.session_state.rubric_validation_errors = validation_errors
        
        if validation_errors:
            st.error("❌ 루브릭 검증 실패:")
            for error in validation_errors:
                st.write(f"• {error}")
        else:
            st.success("✅ 루브릭이 올바르게 설정되었습니다!")
        
        # Display rubric summary
        if st.session_state.rubric.elements:
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("평가 요소 수", len(st.session_state.rubric.elements))
            
            with col2:
                st.metric("총점", f"{st.session_state.rubric.total_max_score}점")
            
            # Detailed preview
            with st.expander("📋 상세 루브릭 미리보기"):
                for i, element in enumerate(st.session_state.rubric.elements, 1):
                    st.markdown(f"**{i}. {element.name}** (최대 {element.max_score}점)")
                    
                    # Sort criteria by score in descending order
                    sorted_criteria = sorted(element.criteria, key=lambda x: x.score, reverse=True)
                    
                    for criteria in sorted_criteria:
                        st.write(f"   • {criteria.score}점: {criteria.description}")
                    
                    if i < len(st.session_state.rubric.elements):
                        st.markdown("---")
        else:
            st.info("📝 루브릭이 비어있습니다. 평가 요소를 추가해주세요.")
    
    def validate_rubric(self) -> List[str]:
        """
        Validate the current rubric configuration.
        Implements Requirement 3.3
        
        Returns:
            List[str]: List of validation error messages
        """
        errors = []
        
        # Check if rubric has elements
        if not st.session_state.rubric.elements:
            errors.append("최소 1개의 평가 요소가 필요합니다.")
            return errors
        
        # Validate each element
        for i, element in enumerate(st.session_state.rubric.elements, 1):
            # Check element name
            if not element.name.strip():
                errors.append(f"평가 요소 {i}의 이름이 비어있습니다.")
            
            # Check criteria
            if not element.criteria:
                errors.append(f"평가 요소 '{element.name}'에 채점 기준이 없습니다.")
                continue
            
            # Validate criteria
            for j, criteria in enumerate(element.criteria, 1):
                if not criteria.description.strip():
                    errors.append(f"평가 요소 '{element.name}'의 {j}번째 기준 설명이 비어있습니다.")
                
                if criteria.score < 0:
                    errors.append(f"평가 요소 '{element.name}'의 {j}번째 기준 점수가 음수입니다.")
            
            # Check for duplicate scores within element
            scores = [c.score for c in element.criteria]
            if len(scores) != len(set(scores)):
                errors.append(f"평가 요소 '{element.name}'에 중복된 점수가 있습니다.")
        
        # Check for duplicate element names
        element_names = [element.name.strip() for element in st.session_state.rubric.elements]
        if len(element_names) != len(set(element_names)):
            errors.append("중복된 평가 요소 이름이 있습니다.")
        
        return errors
    
    def render_rubric_navigation(self):
        """Render navigation buttons for rubric completion."""
        st.markdown("---")
        st.markdown("### 🚀 다음 단계")
        
        # Check if rubric is valid
        is_valid = len(st.session_state.rubric_validation_errors) == 0 and st.session_state.rubric.elements
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if is_valid:
                if st.button(
                    "✅ 루브릭 완료 및 채점 준비",
                    key="complete_rubric",
                    use_container_width=True,
                    type="primary"
                ):
                    # Save rubric to session state and grading session
                    st.session_state.rubric_data = st.session_state.rubric.to_dict()
                    
                    # Set rubric in grading session
                    if 'grading_session' in st.session_state:
                        st.session_state.grading_session.rubric = st.session_state.rubric
                    
                    st.success("✅ 루브릭이 저장되었습니다! 이제 채점 준비가 완료되었습니다.")
                    st.session_state.current_page = "grading"
                    st.rerun()
            else:
                st.button(
                    "✅ 루브릭 완료 및 채점 준비",
                    key="complete_rubric_disabled",
                    use_container_width=True,
                    disabled=True,
                    help="루브릭을 올바르게 설정한 후 진행할 수 있습니다."
                )
        
        # Show rubric status
        self.show_rubric_status()
    
    def show_rubric_status(self):
        """Show current rubric configuration status."""
        st.markdown("#### ✅ 루브릭 설정 상태")
        
        if st.session_state.rubric.elements:
            st.success(f"✅ 평가 요소: {len(st.session_state.rubric.elements)}개")
            st.success(f"✅ 총점: {st.session_state.rubric.total_max_score}점")
            
            if st.session_state.rubric_validation_errors:
                st.error(f"❌ 검증 오류: {len(st.session_state.rubric_validation_errors)}개")
            else:
                st.success("✅ 루브릭 검증 완료")
        else:
            st.error("❌ 평가 요소를 추가해주세요")


def create_rubric_ui() -> RubricUI:
    """
    Factory function to create RubricUI instance.
    
    Returns:
        RubricUI: Configured RubricUI instance
    """
    return RubricUI()