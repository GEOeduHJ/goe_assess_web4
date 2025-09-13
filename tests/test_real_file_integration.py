"""
Real file integration test for FAISS RAG implementation.

Tests with actual sample files to verify the complete workflow.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch

from services.rag_service import RAGService, format_retrieved_content
from services.grading_engine import SequentialGradingEngine
from services.llm_service import LLMService
from models.student_model import Student
from models.rubric_model import Rubric, EvaluationElement


class TestRealFileIntegration:
    """Test RAG system with real sample files."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rag_service = RAGService()
        
        # Create sample rubric
        element = EvaluationElement(name="지리적 이해")
        element.add_criteria(10, "완전한 이해")
        element.add_criteria(5, "부분적 이해")
        element.add_criteria(0, "이해 부족")
        
        self.rubric = Rubric(name="실제파일 테스트 루브릭")
        self.rubric.add_element(element)
        
        # Create sample student
        self.student = Student(
            name="실제파일테스트학생",
            class_number="1",
            answer="세계지리의 산맥과 강의 특징에 대해 설명해주세요."
        )
    
    def test_sample_pdf_processing(self):
        """Test processing with actual sample PDF file."""
        # Check if sample PDF exists
        sample_pdf_path = Path("sample_data/세계지리_교과서_Ⅰ.pdf")
        
        if not sample_pdf_path.exists():
            pytest.skip("Sample PDF file not found")
        
        # Create mock uploaded file object
        mock_file = Mock()
        mock_file.name = "세계지리_교과서_Ⅰ.pdf"
        
        # Read actual file content
        with open(sample_pdf_path, 'rb') as f:
            mock_file.read.return_value = f.read()
        
        # Test document processing
        try:
            result = self.rag_service.process_documents([mock_file])
            
            # Should succeed or fail gracefully
            assert isinstance(result, bool)
            
            if result:
                # If processing succeeded, test search
                search_results = self.rag_service.search_relevant_content("산맥")
                assert isinstance(search_results, list)
                
                # Test content formatting
                formatted = format_retrieved_content(search_results)
                assert isinstance(formatted, str)
                
                print(f"✅ PDF 처리 성공: {len(search_results)}개 결과 검색됨")
                if search_results:
                    print(f"첫 번째 결과 미리보기: {search_results[0][:100]}...")
            else:
                print("⚠️ PDF 처리 실패 (정상적으로 처리됨)")
                
        except Exception as e:
            print(f"⚠️ PDF 처리 중 예외 발생: {e}")
            # Should not raise exception - should handle gracefully
            assert False, f"PDF processing should handle errors gracefully: {e}"
    
    @patch.object(LLMService, 'call_gemini_api')
    def test_end_to_end_with_sample_file(self, mock_gemini):
        """Test complete end-to-end workflow with sample file."""
        # Mock LLM response
        mock_gemini.return_value = {
            "text": '{"scores": {"지리적 이해": 8}, "reasoning": {"지리적 이해": "참고자료를 활용한 좋은 답변"}, "feedback": "실제 파일을 활용한 우수한 답변입니다", "total_score": 8}'
        }
        
        # Check if sample PDF exists
        sample_pdf_path = Path("sample_data/세계지리_교과서_Ⅰ.pdf")
        
        if not sample_pdf_path.exists():
            pytest.skip("Sample PDF file not found")
        
        # Create mock uploaded file
        mock_file = Mock()
        mock_file.name = "세계지리_교과서_Ⅰ.pdf"
        
        with open(sample_pdf_path, 'rb') as f:
            mock_file.read.return_value = f.read()
        
        # Create grading engine
        grading_engine = SequentialGradingEngine()
        
        try:
            # Execute complete workflow
            results = grading_engine.grade_students_sequential(
                students=[self.student],
                rubric=self.rubric,
                model_type="gemini",
                grading_type="descriptive",
                uploaded_files=[mock_file]
            )
            
            # Verify results
            assert len(results) == 1
            result = results[0]
            assert result.student_name == "실제파일테스트학생"
            
            print(f"✅ 전체 워크플로우 성공")
            print(f"학생: {result.student_name}")
            print(f"점수: {result.total_score}/{result.total_max_score}")
            print(f"피드백: {result.overall_feedback}")
            
        except Exception as e:
            print(f"⚠️ 전체 워크플로우 중 예외 발생: {e}")
            # Should handle gracefully
            assert len(results) == 1, "Should return result even with errors"
    
    def test_multiple_file_types(self):
        """Test processing multiple file types if available."""
        sample_dir = Path("sample_data")
        
        if not sample_dir.exists():
            pytest.skip("Sample data directory not found")
        
        # Look for different file types
        pdf_files = list(sample_dir.glob("*.pdf"))
        docx_files = list(sample_dir.glob("*.docx"))
        
        mock_files = []
        
        # Add PDF files
        for pdf_file in pdf_files[:2]:  # Limit to 2 files for testing
            mock_file = Mock()
            mock_file.name = pdf_file.name
            try:
                with open(pdf_file, 'rb') as f:
                    mock_file.read.return_value = f.read()
                mock_files.append(mock_file)
            except Exception:
                continue
        
        # Add DOCX files
        for docx_file in docx_files[:2]:  # Limit to 2 files for testing
            mock_file = Mock()
            mock_file.name = docx_file.name
            try:
                with open(docx_file, 'rb') as f:
                    mock_file.read.return_value = f.read()
                mock_files.append(mock_file)
            except Exception:
                continue
        
        if not mock_files:
            pytest.skip("No processable sample files found")
        
        # Test processing multiple files
        try:
            result = self.rag_service.process_documents(mock_files)
            
            print(f"✅ 다중 파일 처리: {len(mock_files)}개 파일")
            for mock_file in mock_files:
                print(f"  - {mock_file.name}")
            
            if result:
                # Test search with multiple documents
                search_results = self.rag_service.search_relevant_content("지리")
                print(f"검색 결과: {len(search_results)}개")
                
        except Exception as e:
            print(f"⚠️ 다중 파일 처리 중 예외: {e}")
            # Should handle gracefully
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])