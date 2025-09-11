"""
RAG (Retrieval-Augmented Generation) Service for Geography Auto-Grading System

This service handles document processing, embedding generation, and similarity search
for descriptive question grading using the KURE-v1 embedding model.
"""

import os
import tempfile
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import PyPDF2
from docx import Document

from models.student_model import Student


class RAGService:
    """
    RAG service for processing reference documents and performing similarity search
    for descriptive question grading.
    """
    
    def __init__(self, model_name: str = "nlpai-lab/KURE-v1"):
        """
        Initialize RAG service with KURE-v1 embedding model.
        
        Args:
            model_name: Name of the embedding model to use
        """
        self.model_name = model_name
        self.embedding_model = None
        self.faiss_index = None
        self.document_chunks = []
        self.chunk_metadata = []
        self.embedding_dimension = 768  # KURE-v1 embedding dimension
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
    def _load_embedding_model(self) -> None:
        """Load the KURE-v1 embedding model."""
        try:
            if self.embedding_model is None:
                self.logger.info(f"Loading embedding model: {self.model_name}")
                self.embedding_model = SentenceTransformer(self.model_name)
                self.logger.info("Embedding model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {e}")
            raise RuntimeError(f"Failed to load embedding model: {e}")
    
    def process_reference_documents(self, uploaded_files: List) -> Dict[str, any]:
        """
        Process uploaded reference documents (PDF, DOCX) and create FAISS index.
        
        Args:
            uploaded_files: List of uploaded file objects from Streamlit
            
        Returns:
            Dictionary with processing results and statistics
        """
        try:
            self.logger.info(f"Processing {len(uploaded_files)} reference documents")
            
            # Extract text from all documents
            all_text_content = []
            file_sources = []
            
            for file_obj in uploaded_files:
                file_content = self._extract_document_content(file_obj)
                if file_content:
                    all_text_content.append(file_content)
                    file_sources.append(file_obj.name)
            
            if not all_text_content:
                return {
                    "success": False,
                    "message": "No valid content extracted from uploaded documents",
                    "chunks_created": 0
                }
            
            # Chunk documents
            all_chunks = []
            chunk_sources = []
            
            for content, source in zip(all_text_content, file_sources):
                chunks = self._chunk_document(content)
                all_chunks.extend(chunks)
                chunk_sources.extend([source] * len(chunks))
            
            # Create embeddings and FAISS index
            self._create_embeddings_and_index(all_chunks, chunk_sources)
            
            return {
                "success": True,
                "message": f"Successfully processed {len(uploaded_files)} documents",
                "chunks_created": len(all_chunks),
                "files_processed": file_sources
            }
            
        except Exception as e:
            self.logger.error(f"Error processing reference documents: {e}")
            return {
                "success": False,
                "message": f"Error processing documents: {str(e)}",
                "chunks_created": 0
            }
    
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
                self.logger.warning(f"Unsupported file format: {file_extension}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error extracting content from {file_obj.name}: {e}")
            return None
    
    def _extract_pdf_content(self, file_obj) -> str:
        """Extract text content from PDF file."""
        try:
            # Create a temporary file to work with PyPDF2
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(file_obj.read())
                tmp_file_path = tmp_file.name
            
            # Extract text using PyPDF2
            text_content = []
            with open(tmp_file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_content.append(page_text)
            
            # Clean up temporary file
            os.unlink(tmp_file_path)
            
            return '\n\n'.join(text_content)
            
        except Exception as e:
            self.logger.error(f"Error extracting PDF content: {e}")
            raise
    
    def _extract_docx_content(self, file_obj) -> str:
        """Extract text content from DOCX file."""
        try:
            # Create a temporary file to work with python-docx
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
                tmp_file.write(file_obj.read())
                tmp_file_path = tmp_file.name
            
            # Extract text using python-docx
            doc = Document(tmp_file_path)
            text_content = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)
            
            # Clean up temporary file
            os.unlink(tmp_file_path)
            
            return '\n\n'.join(text_content)
            
        except Exception as e:
            self.logger.error(f"Error extracting DOCX content: {e}")
            raise  
  
    def _chunk_document(self, content: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split document content into overlapping chunks for better retrieval.
        
        Args:
            content: Document text content
            chunk_size: Maximum number of characters per chunk
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        if not content or len(content.strip()) == 0:
            return []
        
        # Clean and normalize text
        content = content.strip()
        
        # Split into sentences first to avoid breaking sentences
        sentences = content.split('.')
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Add sentence to current chunk
            potential_chunk = current_chunk + ". " + sentence if current_chunk else sentence
            
            # If chunk would be too large, save current chunk and start new one
            if len(potential_chunk) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap
                if overlap > 0 and len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:] + ". " + sentence
                else:
                    current_chunk = sentence
            else:
                current_chunk = potential_chunk
        
        # Add the last chunk if it exists
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Filter out very short chunks
        chunks = [chunk for chunk in chunks if len(chunk.strip()) > 20]
        
        self.logger.info(f"Created {len(chunks)} chunks from document")
        return chunks
    
    def _create_embeddings_and_index(self, chunks: List[str], sources: List[str]) -> None:
        """
        Create embeddings for document chunks and build FAISS index.
        
        Args:
            chunks: List of text chunks
            sources: List of source file names for each chunk
        """
        try:
            # Load embedding model if not already loaded
            self._load_embedding_model()
            
            if not chunks:
                raise ValueError("No chunks provided for embedding")
            
            self.logger.info(f"Creating embeddings for {len(chunks)} chunks")
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(
                chunks,
                convert_to_numpy=True,
                show_progress_bar=True
            )
            
            # Ensure embeddings are float32 for FAISS
            embeddings = embeddings.astype(np.float32)
            
            # Create FAISS index
            self.faiss_index = faiss.IndexFlatIP(self.embedding_dimension)
            self.faiss_index.add(embeddings)
            
            # Store chunks and metadata
            self.document_chunks = chunks
            self.chunk_metadata = [{"source": source, "chunk_id": i} 
                                 for i, source in enumerate(sources)]
            
            self.logger.info(f"FAISS index created with {self.faiss_index.ntotal} vectors")
            
        except Exception as e:
            self.logger.error(f"Error creating embeddings and index: {e}")
            raise
    
    def search_relevant_content(self, query: str, top_k: int = 3) -> List[Dict[str, any]]:
        """
        Search for relevant content based on student answer query.
        
        Args:
            query: Student answer or query text
            top_k: Number of top similar chunks to retrieve (default: 3)
            
        Returns:
            List of relevant content with metadata and similarity scores
        """
        try:
            if not self.faiss_index or not self.document_chunks:
                self.logger.warning("No FAISS index or document chunks available")
                return []
            
            if not query or not query.strip():
                self.logger.warning("Empty query provided")
                return []
            
            # Load embedding model if not already loaded
            self._load_embedding_model()
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(
                [query.strip()],
                convert_to_numpy=True
            ).astype(np.float32)
            
            # Perform similarity search
            similarities, indices = self.faiss_index.search(query_embedding, top_k)
            
            # Prepare results
            results = []
            for i, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
                if idx < len(self.document_chunks):  # Ensure valid index
                    result = {
                        "content": self.document_chunks[idx],
                        "similarity_score": float(similarity),
                        "rank": i + 1,
                        "metadata": self.chunk_metadata[idx] if idx < len(self.chunk_metadata) else {}
                    }
                    results.append(result)
            
            self.logger.info(f"Retrieved {len(results)} relevant chunks for query")
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching relevant content: {e}")
            return []
    
    def get_index_stats(self) -> Dict[str, any]:
        """
        Get statistics about the current FAISS index and document chunks.
        
        Returns:
            Dictionary with index statistics
        """
        return {
            "index_exists": self.faiss_index is not None,
            "total_vectors": self.faiss_index.ntotal if self.faiss_index else 0,
            "total_chunks": len(self.document_chunks),
            "embedding_dimension": self.embedding_dimension,
            "model_name": self.model_name
        }
    
    def clear_index(self) -> None:
        """Clear the current FAISS index and document chunks."""
        self.faiss_index = None
        self.document_chunks = []
        self.chunk_metadata = []
        self.logger.info("FAISS index and document chunks cleared")
    
    def is_ready(self) -> bool:
        """
        Check if the RAG service is ready for similarity search.
        
        Returns:
            True if FAISS index and document chunks are available
        """
        return (self.faiss_index is not None and 
                len(self.document_chunks) > 0)


# Utility functions for RAG service
def create_rag_service() -> RAGService:
    """
    Factory function to create a RAG service instance.
    
    Returns:
        Configured RAG service instance
    """
    return RAGService()


def format_retrieved_content(retrieved_results: List[Dict[str, any]]) -> str:
    """
    Format retrieved content for inclusion in LLM prompts.
    
    Args:
        retrieved_results: List of retrieved content with metadata
        
    Returns:
        Formatted string for prompt inclusion
    """
    if not retrieved_results:
        return ""
    
    formatted_parts = []
    for i, result in enumerate(retrieved_results, 1):
        content = result.get("content", "")
        source = result.get("metadata", {}).get("source", "Unknown")
        score = result.get("similarity_score", 0.0)
        
        formatted_parts.append(
            f"참고자료 {i} (출처: {source}, 유사도: {score:.3f}):\n{content}"
        )
    
    return "\n\n".join(formatted_parts)