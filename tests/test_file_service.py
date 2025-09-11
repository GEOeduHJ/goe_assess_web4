"""
파일 처리 서비스 테스트 모듈
"""

import os
import tempfile
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock

from services.file_service import FileService, FileProcessingError
from models.student_model import Student


class TestFileService:
    """FileService 테스트 클래스"""
    
    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        self.file_service = FileService()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """각 테스트 메서드 실행 후 정리"""
        # 임시 파일들 정리
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_excel(self, data: dict, filename: str = "test.xlsx") -> str:
        """테스트용 Excel 파일 생성"""
        file_path = os.path.join(self.temp_dir, filename)
        df = pd.DataFrame(data)
        df.to_excel(file_path, index=False)
        return file_path
    
    def test_validate_excel_format_descriptive_success(self):
        """서술형 Excel 파일 형식 검증 성공 테스트"""
        # 올바른 서술형 데이터
        data = {
            '학생 이름': ['김철수', '이영희', '박민수'],
            '반': ['1', '2', '1'],
            '답안': ['지구온난화는 온실가스 증가로 인한 현상입니다.', 
                   '산업혁명 이후 화석연료 사용이 증가했습니다.',
                   '기후변화는 전 지구적 문제입니다.']
        }
        
        file_path = self.create_test_excel(data)
        result = self.file_service.validate_excel_format(file_path, 'descriptive')
        
        assert result['success'] is True
        assert '올바릅니다' in result['message']
        assert result['data'] is not None
        assert len(result['data']) == 3
    
    def test_validate_excel_format_map_success(self):
        """백지도형 Excel 파일 형식 검증 성공 테스트"""
        # 올바른 백지도형 데이터
        data = {
            '학생 이름': ['김철수', '이영희', '박민수'],
            '반': ['1', '2', '1']
        }
        
        file_path = self.create_test_excel(data)
        result = self.file_service.validate_excel_format(file_path, 'map')
        
        assert result['success'] is True
        assert '올바릅니다' in result['message']
        assert result['data'] is not None
        assert len(result['data']) == 3
    
    def test_validate_excel_format_missing_columns(self):
        """필수 컬럼 누락 테스트"""
        # 필수 컬럼 누락된 데이터
        data = {
            '학생 이름': ['김철수', '이영희'],
            '반': ['1', '2']
            # '답안' 컬럼 누락
        }
        
        file_path = self.create_test_excel(data)
        result = self.file_service.validate_excel_format(file_path, 'descriptive')
        
        assert result['success'] is False
        assert '필수 컬럼이 누락' in result['message']
        assert '답안' in result['message']
    
    def test_validate_excel_format_duplicate_names(self):
        """중복 학생 이름 테스트"""
        data = {
            '학생 이름': ['김철수', '김철수', '이영희'],  # 중복된 이름
            '반': ['1', '2', '1'],
            '답안': ['답안1', '답안2', '답안3']
        }
        
        file_path = self.create_test_excel(data)
        result = self.file_service.validate_excel_format(file_path, 'descriptive')
        
        assert result['success'] is False
        assert '중복된 학생 이름' in result['message']
        assert '김철수' in result['message']
    
    def test_validate_excel_format_short_answers(self):
        """너무 짧은 답안 테스트"""
        data = {
            '학생 이름': ['김철수', '이영희'],
            '반': ['1', '2'],
            '답안': ['짧음', '이것은 충분히 긴 답안입니다.']  # 첫 번째 답안이 너무 짧음
        }
        
        file_path = self.create_test_excel(data)
        result = self.file_service.validate_excel_format(file_path, 'descriptive')
        
        assert result['success'] is False
        assert '답안이 너무 짧습니다' in result['message']
    
    def test_validate_excel_format_file_not_found(self):
        """존재하지 않는 파일 테스트"""
        result = self.file_service.validate_excel_format('nonexistent.xlsx', 'descriptive')
        
        assert result['success'] is False
        assert '파일을 찾을 수 없습니다' in result['message']
    
    def test_process_student_data_descriptive(self):
        """서술형 학생 데이터 처리 테스트"""
        data = {
            '학생 이름': ['김철수', '이영희'],
            '반': ['1', '2'],
            '답안': ['지구온난화에 대한 답안입니다.', '기후변화에 대한 설명입니다.']
        }
        
        file_path = self.create_test_excel(data)
        result = self.file_service.process_student_data(file_path, 'descriptive')
        
        assert result['success'] is True
        assert len(result['students']) == 2
        
        student1 = result['students'][0]
        assert student1.name == '김철수'
        assert student1.class_number == '1'
        assert student1.answer == '지구온난화에 대한 답안입니다.'
        assert student1.image_path is None
    
    def test_match_images_to_students_success(self):
        """이미지-학생 매칭 성공 테스트"""
        student_names = ['김철수', '이영희', '박민수']
        image_files = [
            '/path/to/김철수_답안.jpg',
            '/path/to/이영희.png',
            '/path/to/박민수_지도.jpeg'
        ]
        
        result = self.file_service.match_images_to_students(student_names, image_files)
        
        assert result['success'] is True
        assert len(result['mapping']) == 3
        assert result['mapping']['김철수'] == '/path/to/김철수_답안.jpg'
        assert result['mapping']['이영희'] == '/path/to/이영희.png'
        assert result['mapping']['박민수'] == '/path/to/박민수_지도.jpeg'
    
    def test_match_images_to_students_unmatched(self):
        """매칭되지 않는 이미지 테스트"""
        student_names = ['김철수', '이영희']
        image_files = [
            '/path/to/김철수.jpg',
            '/path/to/다른학생.png'  # 매칭되지 않는 이미지
        ]
        
        result = self.file_service.match_images_to_students(student_names, image_files)
        
        assert result['success'] is False
        assert '이영희' in result['message']
        assert '찾을 수 없습니다' in result['message']
    
    def test_clean_name_for_matching(self):
        """이름 정규화 테스트"""
        # 공백과 특수문자 제거 테스트
        assert self.file_service._clean_name_for_matching('김 철 수') == '김철수'
        assert self.file_service._clean_name_for_matching('이영희_답안') == '이영희답안'
        assert self.file_service._clean_name_for_matching('박민수(1반)') == '박민수1반'
    
    def test_is_name_match(self):
        """이름 매칭 로직 테스트"""
        # 완전 일치
        assert self.file_service._is_name_match('김철수', '김철수') is True
        
        # 포함 관계
        assert self.file_service._is_name_match('김철수', '김철수답안') is True
        assert self.file_service._is_name_match('김철수답안', '김철수') is True
        
        # 성씨 제외 매칭
        assert self.file_service._is_name_match('김철수', '철수') is True
        
        # 매칭되지 않는 경우
        assert self.file_service._is_name_match('김철수', '이영희') is False 
   
    def test_extract_document_content_unsupported_format(self):
        """지원하지 않는 문서 형식 테스트"""
        # 텍스트 파일 생성 (지원하지 않는 형식)
        txt_file = os.path.join(self.temp_dir, 'test.txt')
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write('테스트 내용')
        
        result = self.file_service.extract_document_content(txt_file)
        
        assert result['success'] is False
        assert '지원하지 않는 문서 형식' in result['message']
    
    @patch('services.file_service.docx.Document')
    def test_extract_docx_content_success(self, mock_docx):
        """DOCX 내용 추출 성공 테스트"""
        # Mock 설정
        mock_doc = MagicMock()
        mock_paragraph1 = MagicMock()
        mock_paragraph1.text = '첫 번째 문단입니다.'
        mock_paragraph2 = MagicMock()
        mock_paragraph2.text = '두 번째 문단입니다.'
        
        mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2]
        mock_doc.tables = []  # 빈 테이블 리스트
        mock_docx.return_value = mock_doc
        
        # 임시 DOCX 파일 생성 (실제로는 mock이 사용됨)
        docx_file = os.path.join(self.temp_dir, 'test.docx')
        with open(docx_file, 'w') as f:
            f.write('dummy')  # 파일 존재만 확인
        
        result = self.file_service.extract_document_content(docx_file)
        
        assert result['success'] is True
        assert '첫 번째 문단입니다.' in result['content']
        assert '두 번째 문단입니다.' in result['content']
    
    @patch('services.file_service.PdfReader')
    def test_extract_pdf_content_success(self, mock_pdf_reader):
        """PDF 내용 추출 성공 테스트"""
        # Mock 설정
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = '첫 번째 페이지 내용'
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = '두 번째 페이지 내용'
        
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader
        
        # 임시 PDF 파일 생성
        pdf_file = os.path.join(self.temp_dir, 'test.pdf')
        with open(pdf_file, 'wb') as f:
            f.write(b'dummy pdf content')
        
        result = self.file_service.extract_document_content(pdf_file)
        
        assert result['success'] is True
        assert '첫 번째 페이지 내용' in result['content']
        assert '두 번째 페이지 내용' in result['content']
        assert '페이지 1' in result['content']
        assert '페이지 2' in result['content']
    
    def test_validate_image_files_success(self):
        """이미지 파일 검증 성공 테스트"""
        # 임시 이미지 파일들 생성
        image_files = []
        for i, ext in enumerate(['.jpg', '.png', '.jpeg']):
            image_file = os.path.join(self.temp_dir, f'test{i}{ext}')
            with open(image_file, 'wb') as f:
                f.write(b'dummy image content')
            image_files.append(image_file)
        
        result = self.file_service.validate_image_files(image_files)
        
        assert result['success'] is True
        assert len(result['valid_files']) == 3
        assert '3개의 이미지 파일이 유효합니다' in result['message']
    
    def test_validate_image_files_invalid_format(self):
        """유효하지 않은 이미지 형식 테스트"""
        # 지원하지 않는 형식의 파일 생성
        invalid_file = os.path.join(self.temp_dir, 'test.txt')
        with open(invalid_file, 'w') as f:
            f.write('not an image')
        
        result = self.file_service.validate_image_files([invalid_file])
        
        assert result['success'] is False
        assert '지원하지 않는 형식' in result['message']
    
    def test_validate_image_files_file_not_found(self):
        """존재하지 않는 이미지 파일 테스트"""
        result = self.file_service.validate_image_files(['nonexistent.jpg'])
        
        assert result['success'] is False
        assert '파일 없음' in result['message']
    
    def test_get_file_info_success(self):
        """파일 정보 조회 성공 테스트"""
        # 테스트 파일 생성
        test_file = os.path.join(self.temp_dir, 'test.xlsx')
        test_content = 'A' * 1024  # 1KB 내용
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        result = self.file_service.get_file_info(test_file)
        
        assert result['exists'] is True
        assert result['name'] == 'test.xlsx'
        assert result['extension'] == '.xlsx'
        assert result['size_bytes'] == 1024
        assert result['size_mb'] == 0.0  # 1KB는 0.0MB로 반올림
    
    def test_get_file_info_not_found(self):
        """존재하지 않는 파일 정보 조회 테스트"""
        result = self.file_service.get_file_info('nonexistent.txt')
        
        assert result['exists'] is False
        assert '파일이 존재하지 않습니다' in result['message']
    
    def test_file_processing_error_handling(self):
        """FileProcessingError 예외 처리 테스트"""
        # pandas.read_excel 오류는 딕셔너리로 반환됨
        with patch('os.path.exists', return_value=True), \
             patch('pandas.read_excel', side_effect=Exception('Test error')):
            result = self.file_service.validate_excel_format('test.xlsx', 'descriptive')
            assert result['success'] is False
            assert 'Excel 파일을 읽을 수 없습니다' in result['message']
    
    def test_process_student_data_with_images(self):
        """이미지가 포함된 학생 데이터 처리 테스트"""
        # Excel 데이터 생성
        data = {
            '학생 이름': ['김철수', '이영희'],
            '반': ['1', '2']
        }
        file_path = self.create_test_excel(data)
        
        # 이미지 파일 생성
        image_files = []
        for name in ['김철수', '이영희']:
            image_file = os.path.join(self.temp_dir, f'{name}.jpg')
            with open(image_file, 'wb') as f:
                f.write(b'dummy image')
            image_files.append(image_file)
        
        result = self.file_service.process_student_data(file_path, 'map', image_files)
        
        assert result['success'] is True
        assert len(result['students']) == 2
        
        # 첫 번째 학생 확인
        student1 = result['students'][0]
        assert student1.name == '김철수'
        assert student1.class_number == '1'
        assert student1.answer == ""  # 백지도형은 답안이 빈 문자열
        assert student1.image_path is not None
        assert '김철수' in student1.image_path
    
    def test_edge_cases_empty_excel(self):
        """빈 Excel 파일 테스트"""
        # 빈 DataFrame으로 Excel 파일 생성
        empty_file = os.path.join(self.temp_dir, 'empty.xlsx')
        pd.DataFrame().to_excel(empty_file, index=False)
        
        result = self.file_service.validate_excel_format(empty_file, 'descriptive')
        
        assert result['success'] is False
        assert 'Excel 파일이 비어있습니다' in result['message']
    
    def test_edge_cases_null_values(self):
        """NULL 값이 포함된 데이터 테스트"""
        import numpy as np
        
        data = {
            '학생 이름': ['김철수', np.nan, '박민수'],  # NULL 값 포함
            '반': ['1', '2', '1'],
            '답안': ['답안1', '답안2', '답안3']
        }
        
        file_path = self.create_test_excel(data)
        result = self.file_service.validate_excel_format(file_path, 'descriptive')
        
        assert result['success'] is False
        assert '빈 값이 있습니다' in result['message']


if __name__ == '__main__':
    pytest.main([__file__])