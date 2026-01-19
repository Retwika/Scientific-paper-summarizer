"""
Summarization strategies for scientific papers.

Implements various approaches to generate high-quality summaries
using Google's Generative AI models.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import google.generativeai as genai

from ..utils.text_processor import (
    detect_sections,
    extract_section,
    count_words,
    clean_text,
    truncate_to_words,
)
from ..utils.logger import logger
from config.settings import settings


@dataclass
class Summary:
    """Structured summary of a scientific paper."""
    title: str
    overview: str
    key_findings: List[str]
    methodology: Optional[str] = None
    results: Optional[str] = None
    conclusions: Optional[str] = None
    full_summary: Optional[str] = None
    word_count: int = 0


class ScientificPaperSummarizer:
    """
    Advanced summarizer specifically designed for scientific papers.
    
    Uses section-aware processing and iterative refinement to produce
    high-quality, structured summaries.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the summarizer.
        
        Args:
            model_name: Google Gemini model name (uses settings default if None)
        """
        self.model_name = model_name or settings.model_name
        self.temperature = settings.temperature
        self.max_tokens = settings.max_tokens
        
        # Configure Google AI
        if not settings.validate_api_key():
            raise ValueError("Google API key not set. Please set GOOGLE_API_KEY environment variable.")
        
        # Dynamic API setup (avoid static attribute access for compatibility with different SDK versions)
        configure_fn = getattr(genai, "configure", None)
        if callable(configure_fn):
            try:
                configure_fn(api_key=settings.google_api_key)
            except Exception:
                logger.warning("GenAI configure failed; relying on environment auth.")

        # Instantiate model dynamically if available; else fallback to name-only usage.
        model_cls = getattr(genai, "GenerativeModel", None)
        if callable(model_cls):
            try:
                self._model = model_cls(
                    model_name=self.model_name,
                    generation_config={
                        "temperature": self.temperature,
                        "max_output_tokens": self.max_tokens,
                    }
                )
            except Exception as e:
                logger.warning(f"Model instantiation failed; will use direct generate calls. Error: {e}")
                self._model = None
        else:
            self._model = None
        self._model_name = self.model_name
        
        logger.info(f"Initialized summarizer with model: {self.model_name}")
    
    def summarize(
        self,
        text: str,
        title: str = "Scientific Paper",
        summary_max_words: Optional[int] = None,
    ) -> Summary:
        """
        Generate a comprehensive summary of a scientific paper.
        
        This method:
        1. Detects paper sections
        2. Extracts key information from each section
        3. Generates a cohesive summary
        4. Identifies key findings
        
        Args:
            text: Full text of the paper
            title: Paper title (if known)
            
        Returns:
            Summary object with structured information
        """
        effective_max = summary_max_words or settings.summary_max_words
        logger.info(f"Starting summarization of: {title} (target words={effective_max})")

        # Clean the text
        text = clean_text(text)
        logger.info(f"Processing {count_words(text)} words")

        # Detect sections
        sections = detect_sections(text)
        logger.info(f"Detected sections: {list(sections.keys())}")

        # Extract and summarize key sections
        section_summaries = self._summarize_sections(text, sections, effective_max)

        # Generate overview
        overview = self._generate_overview(text, section_summaries, effective_max)

        # Extract key findings
        key_findings = self._extract_key_findings(text, section_summaries)

        # Compile full summary and expand if too short
        full_summary = self._compile_full_summary(
            overview,
            section_summaries,
            key_findings,
            source_text=text,
            effective_max=effective_max,
        )

        summary = Summary(
            title=title,
            overview=overview,
            key_findings=key_findings,
            methodology=section_summaries.get("methods") or section_summaries.get("methodology"),
            results=section_summaries.get("results"),
            conclusions=section_summaries.get("conclusion"),
            full_summary=full_summary,
            word_count=count_words(full_summary),
        )

        logger.info(f"Summary generated: {summary.word_count} words (cap={effective_max})")
        return summary
    
    def _summarize_sections(self, text: str, sections: Dict[str, tuple], effective_max: int) -> Dict[str, str]:
        """
        Summarize individual sections of the paper.
        
        Args:
            text: Full paper text
            sections: Dictionary of section names to (start, end) positions
            
        Returns:
            Dictionary mapping section names to their summaries
        """
        section_summaries: Dict[str, str] = {}

        # Only focus on essential sections to reduce API calls
        priority_sections = [
            "methods",
            "methodology",
            "results",
        ]

        # Allocate a rough per-section word budget from settings
        present = [s for s in priority_sections if s in sections]
        total_budget = max(200, effective_max)
        section_budget_pool = max(100, int(total_budget * 0.6))
        per_section_words = max(80, int(section_budget_pool / max(1, len(present) or 1)))

        for section_name in priority_sections:
            if section_name in sections:
                section_text = extract_section(text, section_name)
                if section_text and len(section_text) > 100:
                    logger.info(f"Summarizing section: {section_name}")
                    summary = self._summarize_chunk(
                        section_text,
                        section_name,
                        target_words=per_section_words,
                    )
                    section_summaries[section_name] = summary

        return section_summaries
    
    def _summarize_chunk(self, text: str, context: str = "", target_words: int = 150) -> str:
        """
        Summarize a chunk of text using the AI model.
        
        Args:
            text: Text to summarize
            context: Context about what this text represents
            
        Returns:
            Generated summary
        """
        prompt = f"""You are an expert at summarizing scientific papers.

Context: This is the {context} section of a scientific paper.

Text to summarize:
{text}

Please provide a clear, concise summary that captures the essential information. 
Focus on the key points, methods, findings, or conclusions as appropriate for this section.
Use technical language where necessary but ensure clarity. Limit to about {target_words} words.

Summary:"""

        try:
            # Prefer instantiated model if available
            if self._model is not None:
                gen_fn = getattr(self._model, "generate_content", None)
                if callable(gen_fn):
                    response = gen_fn(prompt)
                    return (getattr(response, "text", "") or "").strip() or "Summary generation failed."
            # Fallback: module-level generation helpers (dynamic)
            gen_content_fn = getattr(genai, "generate_content", None)
            if callable(gen_content_fn):
                response = gen_content_fn(model=self._model_name, prompt=prompt)
                return (getattr(response, "text", "") or "").strip() or "Summary generation failed."
            gen_fn_alt = getattr(genai, "generate", None)
            if callable(gen_fn_alt):
                response = gen_fn_alt(model=self._model_name, prompt=prompt)
                return (getattr(response, "text", "") or "").strip() or "Summary generation failed."
            raise RuntimeError("Gemini SDK provides no usable generation method.")
        except Exception as e:
            logger.error(f"Error summarizing chunk: {e}")
            # Check if it's a rate limit error
            if "429" in str(e) or "quota" in str(e).lower():
                raise RuntimeError(f"API Rate Limit Exceeded: {e}") from e
            raise RuntimeError(f"Section summarization failed: {e}") from e
    
    def _generate_overview(self, text: str, section_summaries: Dict[str, str], effective_max: int) -> str:
        """
        Generate a high-level overview of the paper.
        
        Args:
            text: Full paper text
            section_summaries: Summaries of individual sections
            
        Returns:
            Overview text
        """
        logger.info("Generating overview")
        
        # If no section summaries, use the raw text (first ~2000 chars)
        if not section_summaries:
            logger.warning("No section summaries available, using raw text for overview")
            context = text[:2000] + "..." if len(text) > 2000 else text
            
            # If sections are missing, dedicate more budget to overview (comprehensive fallback)
            overview_target = max(400, int(effective_max * 0.8))
            prompt = f"""You are an expert at summarizing scientific papers.

Read this excerpt from a scientific paper and provide a comprehensive overview (~{overview_target} words) that captures the paper's main contribution, approach, and significance.

Paper Excerpt:
{context}

Generate a cohesive overview that:
1. States the research question or problem
2. Describes the methodology in brief
3. Highlights main findings
4. Indicates significance or implications

Overview:"""
        else:
            # Combine section summaries for context
            context = "\n\n".join([
                f"{section.upper()}:\n{summary}" 
                for section, summary in section_summaries.items()
            ])
            
            overview_target = max(200, int(effective_max * 0.4))
            prompt = f"""You are an expert at summarizing scientific papers.

Based on these section summaries from a scientific paper, provide a comprehensive overview (~{overview_target} words) that captures the paper's main contribution, approach, and significance.

Section Summaries:
{context}

Generate a cohesive overview that:
1. States the research question or problem
2. Describes the methodology in brief
3. Highlights main findings
4. Indicates significance or implications

Overview:"""

        try:
            if self._model is not None:
                gen_fn = getattr(self._model, "generate_content", None)
                if callable(gen_fn):
                    response = gen_fn(prompt)
                    return (getattr(response, "text", "") or "").strip() or "Overview generation failed."
            gen_content_fn = getattr(genai, "generate_content", None)
            if callable(gen_content_fn):
                response = gen_content_fn(model=self._model_name, prompt=prompt)
                return (getattr(response, "text", "") or "").strip() or "Overview generation failed."
            gen_fn_alt = getattr(genai, "generate", None)
            if callable(gen_fn_alt):
                response = gen_fn_alt(model=self._model_name, prompt=prompt)
                return (getattr(response, "text", "") or "").strip() or "Overview generation failed."
            raise RuntimeError("Gemini SDK provides no usable generation method.")
        except Exception as e:
            logger.error(f"Error generating overview: {e}")
            # Check if it's a rate limit error
            if "429" in str(e) or "quota" in str(e).lower():
                raise RuntimeError(f"API Rate Limit Exceeded: {e}") from e
            raise RuntimeError(f"Overview generation failed: {e}") from e
    
    def _extract_key_findings(self, text: str, section_summaries: Dict[str, str]) -> List[str]:
        """
        Extract key findings as bullet points.
        
        Args:
            text: Full paper text
            section_summaries: Summaries of sections
            
        Returns:
            List of key findings
        """
        logger.info("Extracting key findings")
        
        # Focus on results and conclusion sections
        relevant_text = ""
        for section in ['results', 'discussion', 'conclusion']:
            if section in section_summaries:
                relevant_text += f"\n\n{section_summaries[section]}"
        
        if not relevant_text and section_summaries:
            relevant_text = "\n\n".join(section_summaries.values())
        
        # If still no section summaries, use raw text
        if not relevant_text:
            logger.warning("No section summaries available for key findings, using raw text")
            relevant_text = text[:3000] + "..." if len(text) > 3000 else text
        
        prompt = f"""You are an expert at analyzing scientific papers.

Based on this text from a scientific paper, extract 3-5 key findings or contributions.

Text:
{relevant_text}

Provide the key findings as a numbered list. Each finding should be:

Key Findings:"""

        try:
            if self._model is not None:
                gen_fn = getattr(self._model, "generate_content", None)
                if callable(gen_fn):
                    response = gen_fn(prompt)
                    findings_text = (getattr(response, "text", "") or "").strip()
                else:
                    findings_text = ""
            else:
                gen_content_fn = getattr(genai, "generate_content", None)
                if callable(gen_content_fn):
                    response = gen_content_fn(model=self._model_name, prompt=prompt)
                    findings_text = (getattr(response, "text", "") or "").strip()
                else:
                    gen_fn_alt = getattr(genai, "generate", None)
                    if callable(gen_fn_alt):
                        response = gen_fn_alt(model=self._model_name, prompt=prompt)
                        findings_text = (getattr(response, "text", "") or "").strip()
                    else:
                        raise RuntimeError("Gemini SDK provides no usable generation method.")
            
            # Parse into list
            findings = []
            for line in findings_text.split('\n'):
                line = line.strip()
                # Remove numbering like "1.", "1)", etc.
                line = line.lstrip('0123456789.)-• ')
                if line:
                    findings.append(line)
            
            return findings[:5]  # Limit to 5 findings
        except Exception as e:
            logger.error(f"Error extracting key findings: {e}")
            # Check if it's a rate limit error
            if "429" in str(e) or "quota" in str(e).lower():
                raise RuntimeError(f"API Rate Limit Exceeded: {e}") from e
            raise RuntimeError(f"Key findings extraction failed: {e}") from e
    
    def _compile_full_summary(
        self, 
        overview: str, 
        section_summaries: Dict[str, str],
        key_findings: List[str],
        source_text: str,
        effective_max: int,
    ) -> str:
        """
        Compile all parts into a full summary document.
        
        Args:
            overview: Paper overview
            section_summaries: Section-by-section summaries
            key_findings: List of key findings
            
        Returns:
            Complete formatted summary
        """
        parts = [
            "# SCIENTIFIC PAPER SUMMARY\n",
            "## Overview",
            overview,
            "\n## Key Findings"
        ]
        
        for i, finding in enumerate(key_findings, 1):
            parts.append(f"{i}. {finding}")
        
        if 'methodology' in section_summaries or 'methods' in section_summaries:
            parts.append("\n## Methodology")
            methodology_text = section_summaries.get('methodology') or section_summaries.get('methods') or ""
            parts.append(methodology_text)
        
        if 'results' in section_summaries:
            parts.append("\n## Results")
            parts.append(section_summaries['results'])
        
        if 'conclusion' in section_summaries:
            parts.append("\n## Conclusions")
            parts.append(section_summaries['conclusion'])
        
        full = "\n\n".join(parts)

        # If we're significantly below target, try an expansion pass
        target = max(200, effective_max)
        if count_words(full) < int(target * 0.85):
            expanded = self._expand_summary(source_text, full, target_words=target)
            if expanded:
                full = expanded

        # Enforce global word cap
        if effective_max:
            full = truncate_to_words(full, effective_max)
        return full

    def _expand_summary(self, source_text: str, current_summary: str, target_words: int) -> str:
        """Expand a concise summary into a comprehensive one using the source text.

        Tries to reach approximately target_words while preserving structure and avoiding repetition.
        """
        prompt = f"""You are an expert technical writer.

Expand the following scientific paper summary to approximately {target_words} words.
Use the SOURCE TEXT to add missing details (problem statement, assumptions, methodology highlights, key results, limitations, and implications).
Preserve the markdown structure and keep it factual and non-repetitive.

SOURCE TEXT (use for details):
{truncate_to_words(source_text, 2500)}

CURRENT SUMMARY (to expand):
{current_summary}

Write the expanded summary now, maintaining the same headings:
"""
        try:
            if self._model is not None:
                gen_fn = getattr(self._model, "generate_content", None)
                if callable(gen_fn):
                    response = gen_fn(prompt)
                    return (getattr(response, "text", "") or "").strip() or current_summary
            gen_content_fn = getattr(genai, "generate_content", None)
            if callable(gen_content_fn):
                response = gen_content_fn(model=self._model_name, prompt=prompt)
                return (getattr(response, "text", "") or "").strip() or current_summary
            gen_fn_alt = getattr(genai, "generate", None)
            if callable(gen_fn_alt):
                response = gen_fn_alt(model=self._model_name, prompt=prompt)
                return (getattr(response, "text", "") or "").strip() or current_summary
        except Exception as e:
            logger.error(f"Expansion failed: {e}")
        return current_summary
