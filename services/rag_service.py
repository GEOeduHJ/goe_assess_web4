"""
지리 자동 채점 시스템의 RAG (검색 증강 생성) 서비스

문서 처리 및 유사성 검색을 위해 LangChain FAISS를 사용하는 간소화된 RAG 서비스입니다.
"""

import os
import tempfile
from typing import List, Optional
from dataclasses import dataclass, field
import logging
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document as LangChainDocument
import PyPDF2
from docx import Document


@dataclass
class RAGResult:
    """RAG 처리 결과"""
    success: bool
    content: List[str] = field(default_factory=list)
    error_message: str = ""


class RAGService:
    """
    문서 처리 및 유사성 검색을 위해 LangChain FAISS를 사용하는 간소화된 RAG 서비스
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """HuggingFace 임베딩으로 RAG 서비스 초기화"""
        if not RAGService._initialized:
            self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            self.vector_store = None
            self.logger = logging.getLogger(__name__)
            RAGService._initialized = True
        
    def process_documents(self, uploaded_files: List) -> bool:
        """
        업로드된 참고 문서를 처리하고 FAISS 벡터 저장소 생성
        
        Args:
            uploaded_files: Streamlit에서 업로드된 파일 객체 목록
            
        Returns:
            처리 성공 시 True, 실패 시 False
        """
        try:
            documents = []
            
            for file_obj in uploaded_files:
                try:
                    # 텍스트 내용 추출
                    content = self._extract_document_content(file_obj)
                    if content:
                        # 청크 생성
                        chunks = self._chunk_document(content)
                        
                        # LangChain Document 객체로 변환
                        for i, chunk in enumerate(chunks):
                            doc = LangChainDocument(
                                page_content=chunk,
                                metadata={"source": file_obj.name, "chunk_id": i}
                            )
                            documents.append(doc)
                            
                except Exception:
                    # 문제가 있는 파일은 건너뛰기
                    continue
            
            if not documents:
                return False
            
            # 문서들로부터 FAISS 벡터 저장소 생성
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
            return True
            
        except Exception:
            return False
    
    def search_relevant_content(self, query: str, k: int = 3) -> List[str]:
        """
        쿼리를 기반으로 관련 내용 검색
        
        Args:
            query: 검색할 쿼리 텍스트
            k: 검색할 유사 청크 수
            
        Returns:
            관련 텍스트 청크 목록
        """
        try:
            if not self.vector_store or not query or not query.strip():
                return []
            
            # 유사성 검색 수행
            docs = self.vector_store.similarity_search(query.strip(), k=k)
            
            # 문서에서 텍스트 내용 추출
            return [doc.page_content for doc in docs]
            
        except Exception:
            return []
    
    def process_documents_for_student(self, uploaded_files: List, student_answer: str) -> RAGResult:
        """
        문서를 처리하고 특정 학생 답안과 관련된 내용 검색
        
        Args:
            uploaded_files: 업로드된 파일 객체 목록
            student_answer: 검색 대상이 될 학생 답안 텍스트
            
        Returns:
            성공 상태와 관련 내용이 포함된 RAGResult
        """
        try:
            # 문서가 아직 처리되지 않았다면 처리
            if not self.vector_store:
                success = self.process_documents(uploaded_files)
                if not success:
                    return RAGResult(success=False, error_message="문서 처리 실패")
            
            # 학생 답안을 쿼리로 사용하여 관련 내용 검색
            relevant_content = self.search_relevant_content(student_answer, k=3)
            
            return RAGResult(
                success=True,
                content=relevant_content
            )
            
        except Exception as e:
            return RAGResult(
                success=False,
                error_message=str(e)
            )
    
    def _extract_document_content(self, file_obj) -> Optional[str]:
        """
        PDF 또는 DOCX 파일에서 텍스트 내용 추출
        
        Args:
            file_obj: 업로드된 파일 객체
            
        Returns:
            추출된 텍스트 내용 또는 추출 실패 시 None
        """
        try:
            file_extension = Path(file_obj.name).suffix.lower()
            
            if file_extension == '.pdf':
                return self._extract_pdf_content(file_obj)
            elif file_extension == '.docx':
                return self._extract_docx_content(file_obj)
            else:
                return None
                
        except Exception:
            return None
    
    def _extract_pdf_content(self, file_obj) -> str:
        """PDF 파일에서 텍스트 내용 추출"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(file_obj.read())
            tmp_file_path = tmp_file.name
        
        try:
            text_content = []
            with open(tmp_file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_content.append(page_text)
            
            return '\n\n'.join(text_content)
        finally:
            os.unlink(tmp_file_path)
    
    def _extract_docx_content(self, file_obj) -> str:
        """DOCX 파일에서 텍스트 내용 추출"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
            tmp_file.write(file_obj.read())
            tmp_file_path = tmp_file.name
        
        try:
            doc = Document(tmp_file_path)
            text_content = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)
            
            return '\n\n'.join(text_content)
        finally:
            os.unlink(tmp_file_path)  
    
    def _chunk_document(self, content: str, chunk_size: int = 300, overlap: int = 50) -> List[str]:
        """
        문서 내용을 간단한 겹침 청크로 분할
        
        Args:
            content: 문서 텍스트 내용
            chunk_size: 청크당 최대 문자 수 (기본값: 300)
            overlap: 청크 간 겹칠 문자 수
            
        Returns:
            텍스트 청크 목록
        """
        if not content or len(content.strip()) == 0:
            return []
        
        content = content.strip()
        chunks = []
        
        # 겹침이 있는 간단한 문자 기반 청킹
        start = 0
        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end]
            
            if chunk.strip():
                chunks.append(chunk.strip())
            
            start += chunk_size - overlap
        
        return chunks


def create_rag_service() -> RAGService:
    """
    RAG 서비스 인스턴스를 생성하는 팩토리 함수
    
    Returns:
        구성된 RAG 서비스 인스턴스
    """
    return RAGService()


def format_retrieved_content(content: List[str]) -> str:
    """
    LLM 프롬프트에 포함할 수 있도록 검색된 RAG 내용을 포맷팅
    
    Args:
        content: 검색된 텍스트 청크 목록
        
    Returns:
        프롬프트 포함용으로 포맷팅된 문자열
    """
    if not content:
        return ""
    
    formatted_chunks = []
    for i, chunk in enumerate(content, 1):
        # 프롬프트 팽창을 방지하기 위해 각 청크를 300자로 제한
        truncated_chunk = chunk.strip()
        if len(truncated_chunk) > 300:
            truncated_chunk = truncated_chunk[:300] + "..."
        
        formatted_chunks.append(f"참고자료 {i}:\n{truncated_chunk}")
    
    return "\n\n".join(formatted_chunks)