"""
파일 처리 서비스 통합 테스트
실제 파일을 사용한 통합 테스트를 수행합니다.
"""

import os
import tempfile
import pandas as pd
from pathlib import Path

from services.file_service import FileService
from models.student_model import Student


def test_file_service_integration():
    """파일 서비스 통합 테스트"""
    file_service = FileService()
    
    # 임시 디렉토리 생성
    with tempfile.TemporaryDirectory() as temp_dir:
        # 테스트용 Excel 파일 생성
        excel_data = {
            '학생 이름': ['김철수', '이영희', '박민수'],
            '반': ['1', '2', '1'],
            '답안': [
                '지구온난화는 온실가스 증가로 인한 현상입니다.',
                '산업혁명 이후 화석연료 사용이 증가했습니다.',
                '기후변화는 전 지구적 문제입니다.'
            ]
        }
        
        excel_file = os.path.join(temp_dir, 'students.xlsx')
        df = pd.DataFrame(excel_data)
        df.to_excel(excel_file, index=False)
        
        # 파일 처리 테스트
        result = file_service.process_student_data(excel_file, 'descriptive')
        
        # 결과 검증
        assert result['success'] is True
        assert len(result['students']) == 3
        
        # 첫 번째 학생 검증
        student1 = result['students'][0]
        assert isinstance(student1, Student)
        assert student1.name == '김철수'
        assert student1.class_number == '1'
        assert '지구온난화' in student1.answer
        assert student1.image_path is None
        
        print("✅ 파일 서비스 통합 테스트 성공!")


def test_image_matching_integration():
    """이미지 매칭 통합 테스트"""
    file_service = FileService()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 테스트용 Excel 파일 생성 (백지도형)
        excel_data = {
            '학생 이름': ['김철수', '이영희'],
            '반': ['1', '2']
        }
        
        excel_file = os.path.join(temp_dir, 'students_map.xlsx')
        df = pd.DataFrame(excel_data)
        df.to_excel(excel_file, index=False)
        
        # 테스트용 이미지 파일 생성
        image_files = []
        for name in ['김철수', '이영희']:
            image_file = os.path.join(temp_dir, f'{name}_답안.jpg')
            with open(image_file, 'wb') as f:
                f.write(b'dummy image content')
            image_files.append(image_file)
        
        # 이미지 매칭 테스트
        result = file_service.process_student_data(excel_file, 'map', image_files)
        
        # 결과 검증
        assert result['success'] is True
        assert len(result['students']) == 2
        
        # 학생 검증
        for student in result['students']:
            assert isinstance(student, Student)
            assert student.answer == ""  # 백지도형은 답안이 빈 문자열
            assert student.image_path is not None
            assert student.name in student.image_path
        
        print("✅ 이미지 매칭 통합 테스트 성공!")


if __name__ == '__main__':
    test_file_service_integration()
    test_image_matching_integration()
    print("🎉 모든 통합 테스트 완료!")