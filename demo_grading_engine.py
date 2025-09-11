#!/usr/bin/env python3
"""
Demonstration script for the Sequential Grading Engine.

This script shows how to use the grading engine with sample data.
"""

import time
from services.grading_engine import SequentialGradingEngine, GradingStatus
from services.llm_service import GradingType
from models.student_model import Student
from models.rubric_model import Rubric, EvaluationElement, EvaluationCriteria


def create_sample_data():
    """Create sample students and rubric for demonstration."""
    
    # Create sample students
    students = [
        Student(
            name="김철수", 
            class_number="1-1", 
            answer="한국의 수도는 서울이다. 서울은 한강 유역에 위치하며 조선시대부터 수도 역할을 해왔다."
        ),
        Student(
            name="이영희", 
            class_number="1-2", 
            answer="부산은 한국의 제2의 도시이다. 남동쪽 해안에 위치하며 중요한 항구도시이다."
        ),
        Student(
            name="박민수", 
            class_number="1-3", 
            answer="제주도는 한국의 남쪽에 위치한 화산섬이다. 한라산이 있으며 관광지로 유명하다."
        ),
        Student(
            name="최지혜", 
            class_number="1-4", 
            answer="인천은 서울 근처에 있는 항구도시이다."
        ),
        Student(
            name="정민호", 
            class_number="1-5", 
            answer="대구는 경상북도에 위치한 도시이다."
        )
    ]
    
    # Create sample rubric
    rubric = Rubric(name="지리 기본 지식 평가")
    
    # 정확성 평가 요소
    accuracy_element = EvaluationElement(name="정확성")
    accuracy_element.add_criteria(5, "완전히 정확한 지리적 사실")
    accuracy_element.add_criteria(3, "대체로 정확하나 일부 부정확한 내용")
    accuracy_element.add_criteria(1, "부정확한 내용이 많음")
    accuracy_element.add_criteria(0, "완전히 부정확하거나 답변 없음")
    
    # 완성도 평가 요소
    completeness_element = EvaluationElement(name="완성도")
    completeness_element.add_criteria(5, "상세하고 완전한 설명")
    completeness_element.add_criteria(3, "기본적인 설명은 포함")
    completeness_element.add_criteria(1, "매우 간단한 설명")
    completeness_element.add_criteria(0, "설명 부족 또는 답변 없음")
    
    rubric.add_element(accuracy_element)
    rubric.add_element(completeness_element)
    
    return students, rubric


def demo_progress_tracking():
    """Demonstrate progress tracking capabilities."""
    print("=== Sequential Grading Engine Demo ===\n")
    
    # Create sample data
    students, rubric = create_sample_data()
    
    print(f"📚 Created {len(students)} sample students:")
    for i, student in enumerate(students, 1):
        print(f"  {i}. {student.name} ({student.class_number}): {student.answer[:50]}...")
    
    print(f"\n📋 Created rubric '{rubric.name}' with {len(rubric.elements)} evaluation elements:")
    for element in rubric.elements:
        print(f"  - {element.name} (max: {element.max_score} points)")
    
    # Create grading engine
    engine = SequentialGradingEngine()
    
    # Set up progress tracking
    print("\n🔧 Setting up progress tracking...")
    
    def progress_callback(progress):
        print(f"📊 Progress: {progress.completed_students + progress.failed_students}/{progress.total_students} "
              f"({progress.progress_percentage:.1f}%) - "
              f"✅ {progress.completed_students} completed, "
              f"❌ {progress.failed_students} failed")
        
        if progress.average_processing_time > 0:
            print(f"   ⏱️  Average time: {progress.average_processing_time:.2f}s per student")
            if progress.estimated_completion_time:
                remaining_time = progress.estimated_completion_time - time.time()
                if remaining_time > 0:
                    print(f"   🕒 Estimated completion: {remaining_time:.1f}s remaining")
    
    def student_completed_callback(status):
        if status.status == GradingStatus.COMPLETED:
            print(f"✅ Completed: {status.student.name} "
                  f"(Score: {status.result.total_score}/{status.result.total_max_score}, "
                  f"Time: {status.processing_time:.2f}s)")
        elif status.status == GradingStatus.FAILED:
            print(f"❌ Failed: {status.student.name} "
                  f"(Attempts: {status.attempt_count}, "
                  f"Error: {status.error_message})")
    
    def error_callback(message, exception):
        print(f"🚨 Error: {message} - {exception}")
    
    engine.set_progress_callback(progress_callback)
    engine.set_student_completed_callback(student_completed_callback)
    engine.set_error_callback(error_callback)
    
    # Validate setup
    print("\n🔍 Validating grading setup...")
    validation = engine.validate_grading_setup(
        students=students,
        rubric=rubric,
        model_type="gemini",
        grading_type=GradingType.DESCRIPTIVE
    )
    
    if validation["valid"]:
        print("✅ Setup validation passed!")
        if validation["warnings"]:
            for warning in validation["warnings"]:
                print(f"⚠️  Warning: {warning}")
    else:
        print("❌ Setup validation failed:")
        for error in validation["errors"]:
            print(f"   - {error}")
        return
    
    # Note: This demo doesn't actually call the LLM APIs
    print("\n📝 Note: This demo shows the grading engine structure.")
    print("   To run actual grading, you would need valid API keys in .env file.")
    print("   The engine would call:")
    print("   - Google Gemini API for text/image analysis")
    print("   - Groq API for text-only analysis")
    
    # Show what the grading process would look like
    print(f"\n🚀 Sequential grading process would:")
    print(f"   1. Process {len(students)} students one by one")
    print(f"   2. Generate structured prompts with rubric and student answers")
    print(f"   3. Call selected LLM API for each student")
    print(f"   4. Parse and validate JSON responses")
    print(f"   5. Handle retries for failed API calls (max {engine.llm_service.validate_api_availability()})")
    print(f"   6. Track timing and progress for each student")
    print(f"   7. Generate comprehensive grading summary")
    
    # Show summary structure
    print(f"\n📈 Grading summary would include:")
    print(f"   - Total/completed/failed student counts")
    print(f"   - Success rate and average processing time")
    print(f"   - Individual student results with scores and feedback")
    print(f"   - Detailed error information for failed attempts")
    
    print(f"\n🎯 Key features demonstrated:")
    print(f"   ✅ Sequential processing with progress tracking")
    print(f"   ✅ Real-time progress callbacks and updates")
    print(f"   ✅ Automatic retry mechanism for API failures")
    print(f"   ✅ Comprehensive error handling and logging")
    print(f"   ✅ Detailed timing and performance metrics")
    print(f"   ✅ Validation and setup verification")
    print(f"   ✅ Cancellation support for long-running processes")


def demo_api_availability():
    """Demonstrate API availability checking."""
    print("\n=== API Availability Check ===")
    
    engine = SequentialGradingEngine()
    api_status = engine.llm_service.validate_api_availability()
    
    print("🔌 API Status:")
    for api_name, available in api_status.items():
        status_icon = "✅" if available else "❌"
        status_text = "Available" if available else "Not Available"
        print(f"   {status_icon} {api_name.title()}: {status_text}")
    
    if not any(api_status.values()):
        print("\n⚠️  No APIs are available. To use the grading engine:")
        print("   1. Create a .env file in the project root")
        print("   2. Add your API keys:")
        print("      GOOGLE_API_KEY=your_gemini_api_key")
        print("      GROQ_API_KEY=your_groq_api_key")
        print("   3. Restart the application")


if __name__ == "__main__":
    try:
        demo_progress_tracking()
        demo_api_availability()
        
        print("\n🎉 Demo completed successfully!")
        print("   The Sequential Grading Engine is ready for use.")
        
    except Exception as e:
        print(f"\n💥 Demo failed with error: {e}")
        print("   This is expected if API keys are not configured.")