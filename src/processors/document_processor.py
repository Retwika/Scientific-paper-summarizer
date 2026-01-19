"""
Document processing module for extracting text from various file formats.

Supports PDF, TXT, and DOCX files commonly used for scientific papers.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import PyPDF2
import pdfplumber

from ..utils.logger import logger


class DocumentProcessor(ABC):
    """Abstract base class for document processors."""
    
    @abstractmethod
    def extract_text(self, file_path: Path) -> str:
        """
        Extract text from a document.
        
        Args:
            file_path: Path to the document
            
        Returns:
            Extracted text as string
        """
        pass
    
    @abstractmethod
    def can_process(self, file_path: Path) -> bool:
        """
        Check if this processor can handle the given file.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if processor can handle this file type
        """
        pass


class PDFProcessor(DocumentProcessor):
    """
    Process PDF documents using pdfplumber for better extraction quality.
    
    Falls back to PyPDF2 if pdfplumber fails.
    """
    
    def can_process(self, file_path: Path) -> bool:
        """Check if file is a PDF."""
        return file_path.suffix.lower() == '.pdf'
    
    def extract_text(self, file_path: Path) -> str:
        """
        Extract text from PDF using pdfplumber (preferred) or PyPDF2 (fallback).
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extracted text
            
        Raises:
            Exception: If extraction fails with both methods
        """
        logger.info(f"Extracting text from PDF: {file_path.name}")
        
        # Try pdfplumber first (better quality)
        try:
            text = self._extract_with_pdfplumber(file_path)
            if text.strip():
                logger.info(f"Successfully extracted {len(text)} characters using pdfplumber")
                return text
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
        
        # Fall back to PyPDF2
        try:
            text = self._extract_with_pypdf2(file_path)
            if text.strip():
                logger.info(f"Successfully extracted {len(text)} characters using PyPDF2")
                return text
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            raise Exception(f"Failed to extract text from PDF: {file_path}")
        
        raise Exception(f"No text extracted from PDF: {file_path}")
    
    def _extract_with_pdfplumber(self, file_path: Path) -> str:
        """Extract text using pdfplumber."""
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return '\n'.join(text_parts)
    
    def _extract_with_pypdf2(self, file_path: Path) -> str:
        """Extract text using PyPDF2."""
        text_parts = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return '\n'.join(text_parts)


class TextProcessor(DocumentProcessor):
    """Process plain text files."""
    
    def can_process(self, file_path: Path) -> bool:
        """Check if file is a text file."""
        return file_path.suffix.lower() in ['.txt', '.text', '.md']
    
    def extract_text(self, file_path: Path) -> str:
        """
        Extract text from plain text file.
        
        Args:
            file_path: Path to text file
            
        Returns:
            File contents as string
        """
        logger.info(f"Reading text file: {file_path.name}")
        
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    text = file.read()
                logger.info(f"Successfully read {len(text)} characters")
                return text
            except UnicodeDecodeError:
                continue
        
        raise Exception(f"Failed to read text file with any encoding: {file_path}")


class DOCXProcessor(DocumentProcessor):
    """Process Microsoft Word documents."""
    
    def can_process(self, file_path: Path) -> bool:
        """Check if file is a DOCX file."""
        return file_path.suffix.lower() == '.docx'
    
    def extract_text(self, file_path: Path) -> str:
        """
        Extract text from DOCX file.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            Extracted text
        """
        logger.info(f"Extracting text from DOCX: {file_path.name}")
        
        try:
            from docx import Document
            doc = Document(file_path)
            text_parts = [paragraph.text for paragraph in doc.paragraphs]
            text = '\n'.join(text_parts)
            logger.info(f"Successfully extracted {len(text)} characters")
            return text
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            raise Exception(f"Failed to extract text from DOCX: {file_path}")


class DocumentProcessorFactory:
    """
    Factory for creating appropriate document processors.
    
    Automatically selects the right processor based on file type.
    """
    
    def __init__(self):
        self.processors = [
            PDFProcessor(),
            TextProcessor(),
            DOCXProcessor()
        ]
    
    def get_processor(self, file_path: Path) -> Optional[DocumentProcessor]:
        """
        Get the appropriate processor for a file.
        
        Args:
            file_path: Path to document
            
        Returns:
            DocumentProcessor instance or None if no processor found
        """
        for processor in self.processors:
            if processor.can_process(file_path):
                return processor
        return None
    
    def extract_text(self, file_path: Path) -> str:
        """
        Extract text from a document using the appropriate processor.
        
        Args:
            file_path: Path to document
            
        Returns:
            Extracted text
            
        Raises:
            ValueError: If no processor can handle the file type
            Exception: If extraction fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        processor = self.get_processor(file_path)
        if not processor:
            raise ValueError(f"No processor available for file type: {file_path.suffix}")
        
        return processor.extract_text(file_path)
