"""Source package for the summarizing agent."""

from .agent import SummarizingAgent
from .summarizers import ScientificPaperSummarizer, Summary
from .processors import DocumentProcessorFactory
from .code_generator import CodeGenerator

__version__ = "1.0.0"

__all__ = [
    "SummarizingAgent",
    "ScientificPaperSummarizer",
    "Summary",
    "DocumentProcessorFactory",
    "CodeGenerator"
]
