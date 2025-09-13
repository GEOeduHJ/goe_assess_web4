"""
RAG (Retrieval-Augmented Generation) Service for Geography Auto-Grading System

Simplified RAG service using LangChain FAISS for document processing and similarity search.
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
    """Result from RAG processing."""
    success: bool
    content: List[str] = field(default_factory=list)
    error_message: str = ""


class RAGService:
    """
    Simplified RAG service using LangChain FAISS for document processing and similarity search.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RAGService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize RAG service with HuggingFace embeddings."""
        if not RAGService._initialized:
            self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            self.vector_store = None
            self.logger = logging.getLogger(__name__)
            RAGService._initialized = True
        
    def process_documents(self, uploaded_files: List) -> bool:
        """
        Process uploaded reference documents and create FAISS vector store.
        
        Args:
            uploaded_files: List of uploaded file objects from Streamlit
            
        Returns:
            True if processing successful, False otherwise
        """
        try:
            documents = []
            
            for file_obj in uploaded_files:
                try:
                    # Extract text content
                    content = self._extract_document_content(file_obj)
                    if content:
                        # Create chunks
                        chunks = self._chunk_document(content)
                        
                        # Convert to LangChain Document objects
                        for i, chunk in enumerate(chunks):
                            doc = LangChainDocument(
                                page_content=chunk,
                                metadata={"source": file_obj.name, "chunk_id": i}
                            )
                            documents.append(doc)
                            
                except Exception:
                    # Skip problematic files
                    continue
            
            if not documents:
                return False
            
            # Create FAISS vector store from documents
            self.vector_store = FAISS.from_documents(documents, self.embeddings)
            return True
            
        except Exception:
            return False
    
    def search_relevant_content(self, query: str, k: int = 3) -> List[str]:
        """
        Search for relevant content based on query.
        
        Args:
            query: Query text to search for
            k: Number of similar chunks to retrieve
            
        Returns:
            List of relevant text chunks
        """
        try:
            if not self.vector_store or not query or not query.strip():
                return []
            
            # Perform similarity search
            docs = self.vector_store.similarity_search(query.strip(), k=k)
            
            # Extract text content from documents
            return [doc.page_content for doc in docs]
            
        except Exception:
            return []
    
    def process_documents_for_student(self, uploaded_files: List, student_answer: str) -> RAGResult:
        """
        Process documents and search for content relevant to a specific student answer.
        
        Args:
            uploaded_files: List of uploaded file objects
            student_answer: Student's answer text to search against
            
        Returns:
            RAGResult with success status and relevant content
        """
        try:
            # Process documents if not already done
            if not self.vector_store:
                success = self.process_documents(uploaded_files)
                if not success:
                    return RAGResult(success=False, error_message="Failed to process documents")
            
            # Search for relevant content using student answer as query
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
        Extract text content from PDF or DOCX file.
        
        Args:
            file_obj: Uploaded file object
            
        Returns:
            Extracted text content or None if extraction fails
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
        """Extract text content from PDF file."""
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
        """Extract text content from DOCX file."""
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
        Split document content into simple overlapping chunks.
        
        Args:
            content: Document text content
            chunk_size: Maximum number of characters per chunk (default: 300)
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        if not content or len(content.strip()) == 0:
            return []
        
        content = content.strip()
        chunks = []
        
        # Simple character-based chunking with overlap
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
    Factory function to create a RAG service instance.
    
    Returns:
        Configured RAG service instance
    """
    return RAGService()


def format_retrieved_content(content: List[str]) -> str:
    """
    Format retrieved RAG content for inclusion in LLM prompts.
    
    Args:
        content: List of retrieved text chunks
        
    Returns:
        Formatted string for prompt inclusion
    """
    if not content:
        return ""
    
    formatted_chunks = []
    for i, chunk in enumerate(content, 1):
        # Limit each chunk to 300 characters to prevent prompt bloat
        truncated_chunk = chunk.strip()
        if len(truncated_chunk) > 300:
            truncated_chunk = truncated_chunk[:300] + "..."
        
        formatted_chunks.append(f"참고자료 {i}:\n{truncated_chunk}")
    
    return "\n\n".join(formatted_chunks)