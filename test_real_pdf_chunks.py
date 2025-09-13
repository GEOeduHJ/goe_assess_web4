import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, r'c:\Users\Hong Jun\Desktop\geo_assess_web4')

from services.rag_service import RAGService, format_retrieved_content
from models.rubric_model import Rubric, EvaluationElement, EvaluationCriteria
from models.student_model import Student
from services.llm_service import LLMService

def create_sample_rubric():
    """Create a sample rubric for testing."""
    criteria1 = EvaluationCriteria(score=2, description="정확한 위치 표시")
    criteria2 = EvaluationCriteria(score=1, description="대략적인 위치 표시")
    criteria3 = EvaluationCriteria(score=0, description="위치 표시 없음")
    
    element1 = EvaluationElement(
        name="위치 정확도",
        max_score=2,
        criteria=[criteria1, criteria2, criteria3]
    )
    
    criteria4 = EvaluationCriteria(score=2, description="명확한 레이블")
    criteria5 = EvaluationCriteria(score=1, description="일부 레이블")
    criteria6 = EvaluationCriteria(score=0, description="레이블 없음")
    
    element2 = EvaluationElement(
        name="레이블 완전성",
        max_score=2,
        criteria=[criteria4, criteria5, criteria6]
    )
    
    return Rubric(name="테스트 루브릭", elements=[element1, element2])

def test_real_pdf_chunk_limits():
    """Test chunk limits with real PDF file."""
    print("=" * 60)
    print("Real PDF Chunk Limit Test")
    print("=" * 60)
    
    # Check if PDF file exists
    pdf_path = Path("sample_data/세계지리_교과서_Ⅰ.pdf")
    if pdf_path.exists():
        print(f"Testing with PDF: {pdf_path}")
    else:
        print(f"PDF not found: {pdf_path}")
        # Try the new PDF
        pdf_path = Path("sample_data/세계지리_지도서_Ⅱ.pdf")
        if pdf_path.exists():
            print(f"Testing with PDF: {pdf_path}")
        else:
            print("No PDF files found for testing")
            return
    
    # Create mock uploaded files object
    class MockFile:
        def __init__(self, path):
            self.name = path.name
            self.file_path = str(path)
            
        def read(self):
            with open(self.file_path, 'rb') as f:
                return f.read()
    
    uploaded_files = [MockFile(pdf_path)]
    
    # Create sample student answer
    student_answer = "한국의 지리적 특성과 기후에 대해 설명하고, 주요 도시들의 위치와 역할을 분석해주세요."
    
    print(f"\n1. Student answer: {student_answer}")
    print(f"2. Processing PDF: {pdf_path}")
    
    # Initialize RAG service
    try:
        rag_service = RAGService()
        
        # Process documents for student
        result = rag_service.process_documents_for_student(uploaded_files, student_answer)
        
        if result.success:
            print(f"\n3. RAG processing successful!")
            print(f"   Number of chunks retrieved: {len(result.content)}")
            
            # Format content with chunk limits
            formatted_content = format_retrieved_content(result.content)
            
            print(f"\n4. Formatted content analysis:")
            print(f"   Total formatted length: {len(formatted_content)} characters")
            print(f"   Estimated tokens: {len(formatted_content) // 4}")
            
            # Show each chunk length BEFORE formatting
            for i, chunk in enumerate(result.content, 1):
                print(f"   Original Chunk {i} length: {len(chunk)} characters")
                if len(chunk) > 300:
                    print(f"     WARNING: Original Chunk {i} exceeds 300 characters!")
            
            # Show each formatted chunk length AFTER formatting
            formatted_lines = formatted_content.split('\n\n')
            for i, formatted_chunk in enumerate(formatted_lines, 1):
                clean_chunk = formatted_chunk.replace(f'참고자료 {i}:\n', '').strip()
                print(f"   Formatted Chunk {i} length: {len(clean_chunk)} characters")
                if len(clean_chunk) > 300:
                    print(f"     ERROR: Formatted Chunk {i} still exceeds 300 characters!")
                else:
                    print(f"     ✅ Formatted Chunk {i} is within limit!")
                
            print(f"\n5. Formatted content preview:")
            print("-" * 40)
            print(formatted_content[:1000] + "..." if len(formatted_content) > 1000 else formatted_content)
            print("-" * 40)
            
            # Test with LLM service
            rubric = create_sample_rubric()
            llm_service = LLMService()
            
            prompt = llm_service.generate_prompt(
                rubric=rubric,
                student_answer=student_answer,
                references=result.content,
                grading_type="descriptive"
            )
            
            print(f"\n6. Final prompt analysis:")
            print(f"   Total prompt length: {len(prompt)} characters")
            print(f"   Estimated tokens: {len(prompt) // 4}")
            
            if len(prompt) < 2000:
                print("   ✅ Prompt length is within reasonable limits!")
            else:
                print("   ⚠️ Prompt might be too long!")
                
        else:
            print(f"\n3. RAG processing failed: {result.error_message}")
            
    except Exception as e:
        print(f"\n3. Error during processing: {e}")
        import traceback
        traceback.print_exc()

def main():
    test_real_pdf_chunk_limits()

if __name__ == "__main__":
    main()
