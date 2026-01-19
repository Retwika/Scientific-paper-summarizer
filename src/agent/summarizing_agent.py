"""
Core Agent for Scientific Paper Summarization.

This agent orchestrates the entire summarization pipeline:
1. Document loading and text extraction
2. Text preprocessing and cleaning
3. Section detection and analysis
4. AI-powered summarization
5. Output formatting and saving
"""

from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

from ..processors import DocumentProcessorFactory
from ..summarizers import ScientificPaperSummarizer, Summary
from ..utils.logger import logger
from config.settings import settings


class SummarizingAgent:
    """
    Main agent class for scientific paper summarization.
    
    This agent uses Google's ADK (via Generative AI) to create
    intelligent, structured summaries of scientific papers.
    
    Key Features:
    - Multi-format support (PDF, TXT, DOCX)
    - Section-aware processing
    - Iterative summarization for long documents
    - Structured output with key findings
    - Automatic output management
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        output_dir: Optional[Path] = None
    ):
        """
        Initialize the summarizing agent.
        
        Args:
            model_name: Google Gemini model to use (None = use settings default)
            output_dir: Directory for output files (None = use settings default)
        """
        self.output_dir = output_dir or settings.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.document_processor = DocumentProcessorFactory()
        self.summarizer = ScientificPaperSummarizer(model_name=model_name)
        
        logger.info("SummarizingAgent initialized successfully")
    
    def process_paper(
        self,
        file_path: Path,
        title: Optional[str] = None,
        save_output: bool = True,
        summary_max_words: Optional[int] = None,
    ) -> Summary:
        """
        Process a scientific paper and generate a summary.
        
        This is the main entry point for the agent. It handles:
        1. File loading and text extraction
        2. Text preprocessing
        3. Summary generation
        4. Output saving (optional)
        
        Args:
            file_path: Path to the paper file
            title: Paper title (auto-detected if None)
            save_output: Whether to save the summary to disk
            
        Returns:
            Summary object containing the generated summary
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is unsupported
            Exception: If processing fails
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing paper: {file_path.name}")
        logger.info(f"{'='*60}\n")
        
        # Step 1: Extract text from document
        logger.info("Step 1: Extracting text from document")
        try:
            text = self.document_processor.extract_text(file_path)
            logger.info(f"✓ Extracted {len(text)} characters")
        except Exception as e:
            logger.error(f"✗ Text extraction failed: {e}")
            raise
        
        # Step 2: Detect or use provided title
        if not title:
            title = self._detect_title(text, file_path)
        logger.info(f"Paper title: {title}")
        
        # Step 3: Generate summary
        logger.info("\nStep 2: Generating summary with AI")
        try:
            summary = self.summarizer.summarize(text, title, summary_max_words=summary_max_words)
            logger.info(f"✓ Summary generated ({summary.word_count} words)")
        except Exception as e:
            logger.error(f"✗ Summary generation failed: {e}")
            raise
        
        # Step 4: Save output
        if save_output:
            logger.info("\nStep 3: Saving output")
            try:
                output_path = self._save_summary(summary, file_path)
                logger.info(f"✓ Summary saved to: {output_path}")
            except Exception as e:
                logger.error(f"✗ Failed to save output: {e}")
        
        logger.info(f"\n{'='*60}")
        logger.info("Processing complete!")
        logger.info(f"{'='*60}\n")
        
        return summary
    
    def process_directory(
        self,
        directory: Path,
        recursive: bool = False
    ) -> Dict[str, Summary]:
        """
        Process all papers in a directory.
        
        Args:
            directory: Directory containing papers
            recursive: Whether to search subdirectories
            
        Returns:
            Dictionary mapping file names to Summary objects
        """
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")
        
        # Find all supported files
        pattern = "**/*" if recursive else "*"
        files = []
        for ext in ['.pdf', '.txt', '.docx', '.md']:
            files.extend(directory.glob(f"{pattern}{ext}"))
        
        logger.info(f"Found {len(files)} papers to process")
        
        summaries = {}
        for i, file_path in enumerate(files, 1):
            logger.info(f"\nProcessing {i}/{len(files)}: {file_path.name}")
            try:
                summary = self.process_paper(file_path)
                summaries[file_path.name] = summary
            except Exception as e:
                logger.error(f"Failed to process {file_path.name}: {e}")
                continue
        
        logger.info(f"\nBatch processing complete: {len(summaries)}/{len(files)} successful")
        return summaries
    
    def _detect_title(self, text: str, file_path: Path) -> str:
        """
        Attempt to detect paper title from text or filename.
        
        Args:
            text: Paper text
            file_path: Path to paper file
            
        Returns:
            Detected or generated title
        """
        # Try to find title in first few lines
        lines = text.split('\n')[:10]
        for line in lines:
            line = line.strip()
            if len(line) > 20 and len(line) < 200:
                # Likely a title
                return line
        
        # Fall back to filename
        return file_path.stem.replace('_', ' ').replace('-', ' ').title()
    
    def _save_summary(self, summary: Summary, original_file: Path) -> Path:
        """
        Save summary to a file.
        
        Creates a markdown file with the summary, including metadata.
        
        Args:
            summary: Summary object to save
            original_file: Original paper file path
            
        Returns:
            Path to saved summary file
        """
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = original_file.stem
        output_filename = f"{base_name}_summary_{timestamp}.md"
        output_path = self.output_dir / output_filename
        
        # Format content
        content = self._format_summary_for_file(summary, original_file)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return output_path
    
    def _format_summary_for_file(self, summary: Summary, original_file: Path) -> str:
        """
        Format summary as markdown with metadata.
        
        Args:
            summary: Summary object
            original_file: Original paper file path
            
        Returns:
            Formatted markdown string
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        content = f"""# {summary.title}

---
**Original File:** `{original_file.name}`  
**Generated:** {timestamp}  
**Model:** {self.summarizer.model_name}  
**Word Count:** {summary.word_count}

---

{summary.full_summary}

---

## Metadata

- **Summary Word Count:** {summary.word_count}
- **Model Temperature:** {settings.temperature}
- **Generated by:** Scientific Paper Summarizing Agent
"""
        
        return content
    
    def get_summary_stats(self, summary: Summary) -> Dict:
        """
        Get statistics about a summary.
        
        Args:
            summary: Summary object
            
        Returns:
            Dictionary of statistics
        """
        return {
            "title": summary.title,
            "word_count": summary.word_count,
            "key_findings_count": len(summary.key_findings),
            "has_methodology": summary.methodology is not None,
            "has_results": summary.results is not None,
            "has_conclusions": summary.conclusions is not None
        }
