"""
Configuration settings for the Scientific Paper Summarizing Agent.

This module uses Pydantic for settings management, allowing configuration
through environment variables or direct modification.
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings with support for environment variables.
    
    Attributes:
        google_api_key: API key for Google's Generative AI
        model_name: The Gemini model to use
        temperature: Creativity level (0.0-1.0)
        max_tokens: Maximum tokens in response
        chunk_size: Size of text chunks for processing
        chunk_overlap: Overlap between chunks
        output_dir: Directory for saving summaries
        data_dir: Directory for input papers
    """
    # API Configuration
    google_api_key: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""),
        description="Google API Key for Generative AI"
    )
    
    # Model Configuration
    model_name: str = Field(
        # Can be overridden via the MODEL_NAME environment variable.
        default="gemini-2.5-flash",
        description="Gemini model to use"
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Model temperature for response generation"
    )
    max_tokens: int = Field(
        default=16384,
        description="Maximum tokens in model response"
    )
    
    
    # Section Priorities (for scientific papers)
    priority_sections: List[str] = Field(
        default=[
            "methods",
            "methodology",
            "results"
        ],
        description="Sections to prioritize in summarization"
    )
    
    # Output Configuration
    summary_max_words: int = Field(
        default=800,
        description="Target word count for summary"
    )
    include_key_findings: bool = Field(
        default=True,
        description="Whether to extract key findings separately"
    )
    include_methodology: bool = Field(
        default=True,
        description="Whether to include methodology summary"
    )
    
    # Directory Configuration
    output_dir: Path = Field(
        default=Path("outputs"),
        description="Directory for output summaries"
    )
    data_dir: Path = Field(
        default=Path("data"),
        description="Directory for input papers"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_api_key(self) -> bool:
        """Validate that API key is set."""
        return bool(self.google_api_key and len(self.google_api_key) > 10)


# Global settings instance
settings = Settings()
