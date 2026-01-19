"""
Code generation module for scientific papers.

Generates Python implementations from paper sections using AI models.
Includes validation, error handling, and comprehensive prompts.
"""

import ast
from typing import Optional, Dict, List, Tuple
import google.generativeai as genai

from .utils.text_processor import detect_sections, extract_section, truncate_to_words
from .utils.logger import logger
from .summarizers.scientific_summarizer import Summary
from config.settings import settings


class CodeGenerator:
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the code generator.
        
        Args:
            model_name: Google Gemini model name (uses settings default if None)
        """
        self.model_name = model_name or settings.model_name
        self.temperature = 0.3  # Lower temperature for more deterministic code
        self.max_tokens = settings.max_tokens
        
        # Configure Google AI
        if not settings.validate_api_key():
            raise ValueError("Google API key not set. Cannot generate code.")
        
        configure_fn = getattr(genai, "configure", None)
        if callable(configure_fn):
            try:
                configure_fn(api_key=settings.google_api_key)
            except Exception:
                logger.warning("GenAI configure failed; relying on environment auth.")
        
        # Instantiate model
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
                logger.warning(f"Model instantiation failed: {e}")
                self._model = None
        else:
            self._model = None
        
        logger.info(f"Initialized CodeGenerator with model: {self.model_name}")
    
    def get_code_worthy_sections(self, summary: Summary, raw_text: str) -> List[str]:
        """
        Auto-detect sections suitable for code generation.
        
        Args:
            summary: Generated paper summary
            raw_text: Full paper text
            
        Returns:
            List of section names that likely contain implementable content
        """
        code_sections = []
        
        # Priority sections from summary
        if summary.methodology:
            code_sections.append("Methods/Methodology")
        
        # Detect code-worthy sections from raw text
        sections = detect_sections(raw_text)
        
        code_keywords = [
            'algorithm', 'implementation', 'procedure', 'method',
            'preprocessing', 'data processing', 'model', 'computation',
            'experimental setup', 'analysis', 'statistical', 'approach',
            'technique', 'framework', 'architecture'
        ]
        
        for section_name in sections.keys():
            section_lower = section_name.lower()
            if any(keyword in section_lower for keyword in code_keywords):
                formatted_name = section_name.replace('_', ' ').title()
                if formatted_name not in code_sections:
                    code_sections.append(formatted_name)
        
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for section in code_sections:
            section_lower = section.lower()
            if section_lower not in seen:
                seen.add(section_lower)
                result.append(section)
        
        # Fallback if no sections detected
        if not result:
            result = ["Methods/Methodology", "Algorithm", "Implementation"]
        
        logger.info(f"Detected {len(result)} code-worthy sections: {result}")
        return result
    
    def generate_for_section(
        self,
        section_name: str,
        raw_text: str,
        summary: Summary,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Generate Python code for a specific paper section.
        
        Args:
            section_name: Name of section to implement (e.g., "Methods")
            raw_text: Full paper text for context
            summary: Pre-generated summary object
            
        Returns:
            Tuple of (code, explanation, error_message)
            - code: Generated Python implementation
            - explanation: High-level explanation of the code
            - error_message: Error if generation failed, None otherwise
        """
        logger.info(f"Generating code for section: {section_name}")
        
        try:
            # Extract section content
            section_text, section_summary = self._extract_section_content(
                section_name, raw_text, summary
            )
            
            if not section_text:
                error_msg = f"Section '{section_name}' not found in paper. Try another section."
                logger.warning(error_msg)
                return None, None, error_msg
            
            # Generate code with comprehensive prompt
            code = self._generate_code_implementation(
                section_name=section_name,
                section_text=section_text,
                section_summary=section_summary,
                paper_title=summary.title,
                paper_overview=summary.overview,
                full_text=raw_text
            )
            
            if not code:
                return None, None, "Code generation failed. No output from model."
            
            # Validate syntax
            is_valid, validation_error = self._validate_python_syntax(code)
            if not is_valid:
                logger.warning(f"Generated code has syntax errors: {validation_error}")
                # Still return the code but with warning in explanation
                explanation = self._generate_code_explanation(code, section_name)
                explanation = f"⚠️ Note: Generated code may have syntax issues.\n\n{explanation}"
                return code, explanation, None
            
            # Generate explanation
            explanation = self._generate_code_explanation(code, section_name)
            
            logger.info(f"Successfully generated {len(code)} characters of valid Python code")
            return code, explanation, None
            
        except Exception as e:
            error_msg = f"Error generating code: {str(e)}"
            logger.error(error_msg)
            
            # Check for rate limits
            if "429" in str(e) or "quota" in str(e).lower():
                error_msg = "⏱️ API Rate Limit Exceeded. Wait 60 seconds and try again."
            
            return None, None, error_msg
    
    def generate_all_sections(
        self,
        raw_text: str,
        summary: Summary,
    ) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
        """
        Generate code for all code-worthy sections in the paper.
        
        Args:
            raw_text: Full paper text
            summary: Pre-generated summary
            
        Returns:
            Dictionary mapping section names to (code, explanation) tuples
        """
        logger.info("Generating code for all sections")
        
        sections = self.get_code_worthy_sections(summary, raw_text)
        results = {}
        
        for section_name in sections:
            code, explanation, error = self.generate_for_section(
                section_name, raw_text, summary
            )
            
            if error:
                logger.warning(f"Failed to generate code for {section_name}: {error}")
                results[section_name] = (None, error)
            else:
                results[section_name] = (code, explanation)
        
        logger.info(f"Completed batch generation for {len(results)} sections")
        return results
    
    def _extract_section_content(
        self,
        section_name: str,
        raw_text: str,
        summary: Summary
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract section text and its summary.
        
        Returns:
            (section_text, section_summary)
        """
        # Normalize section name
        section_key = section_name.lower().replace('/', ' ').strip()
        
        # Common aliases
        aliases = {
            'methodology': 'methods',
            'conclusions': 'conclusion',
            'techniques': 'methods',
            'approach': 'methods',
        }
        section_key = aliases.get(section_key, section_key)
        
        # Detect sections
        sections = detect_sections(raw_text)
        
        # Find matching section
        section_text = None
        for s in sections.keys():
            if section_key in s or s in section_key:
                section_text = extract_section(raw_text, s)
                break
        
        # Get section summary from Summary object
        section_summary = None
        if 'method' in section_key:
            section_summary = summary.methodology
        elif 'result' in section_key:
            section_summary = summary.results
        elif 'conclusion' in section_key:
            section_summary = summary.conclusions
        
        # Fallback: use summary methodology or abstract
        if not section_text and summary.methodology:
            section_text = summary.methodology
            section_summary = summary.methodology
        
        return section_text, section_summary
    
    def _generate_code_implementation(
        self,
        section_name: str,
        section_text: str,
        section_summary: Optional[str],
        paper_title: str,
        paper_overview: str,
        full_text: str
    ) -> Optional[str]:
        """
        Generate Python code using comprehensive prompt.
        
        Returns:
            Generated Python code string or None on failure
        """
        # Truncate texts to fit context window (reduced for faster generation)
        section_text_truncated = truncate_to_words(section_text, 1500)
        
        # Build focused, concise prompt
        prompt = f"""Generate a complete, runnable Python implementation of the methodology described below.

# PAPER: {paper_title}

# SECTION TO IMPLEMENT: {section_name}

# METHODOLOGY:
{section_summary or section_text_truncated}

# DETAILED CONTENT:
{section_text_truncated[:2000]}

# REQUIREMENTS:
Generate complete, working Python code with:
- Proper imports (numpy, scipy, pandas as needed)
- Type hints on functions  
- Brief docstrings
- A working example in if __name__ == "__main__": block
- NO placeholders or TODO comments

Output ONLY Python code. Start with imports, end with working example.
No markdown blocks, no explanations outside code comments.

Begin implementation:
"""
        
        logger.info(f"Prompt length: {len(prompt)} characters")
        
        try:
            # Call Gemini API
            if self._model is not None:
                gen_fn = getattr(self._model, "generate_content", None)
                if callable(gen_fn):
                    response = gen_fn(prompt)
                    code_response = (getattr(response, "text", "") or "").strip()
                else:
                    return None
            else:
                gen_content_fn = getattr(genai, "generate_content", None)
                if callable(gen_content_fn):
                    response = gen_content_fn(model=self.model_name, prompt=prompt)
                    code_response = (getattr(response, "text", "") or "").strip()
                else:
                    raise RuntimeError("Gemini SDK provides no usable generation method.")
            
            # Log response details for debugging
            logger.info(f"Received API response: {len(code_response)} characters")
            
            # Check if response was likely truncated (ends abruptly)
            if code_response and not any(code_response.endswith(marker) for marker in ['"', ')', '}', '\n', '```']):
                logger.warning(f"Response may be truncated - ends with: ...{code_response[-50:]}")
            
            # Check for finish reason if available
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    logger.info(f"Finish reason: {candidate.finish_reason}")
                    if candidate.finish_reason not in [1, 'STOP']:  # 1 = STOP
                        logger.warning(f"Response finished with reason: {candidate.finish_reason}")
            
            # Extract code from response (handle markdown blocks)
            code = self._extract_code_from_response(code_response)
            
            return code
            
        except Exception as e:
            logger.error(f"Code generation API call failed: {e}")
            if "429" in str(e) or "quota" in str(e).lower():
                raise RuntimeError(f"API Rate Limit Exceeded: {e}") from e
            raise
    
    def _extract_code_from_response(self, response: str) -> str:
        """
        Extract Python code from model response, handling markdown formatting.
        """
        # Remove markdown code blocks if present
        if "```python" in response:
            start = response.find("```python") + 9
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        # Return as-is if no markdown blocks
        return response.strip()
    
    def _validate_python_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that generated code is syntactically correct Python.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            ast.parse(code)
            logger.info("✓ Generated code is syntactically valid")
            return True, None
        except SyntaxError as e:
            error_msg = f"Line {e.lineno}: {e.msg}"
            logger.warning(f"Syntax validation failed: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Validation error: {error_msg}")
            return False, error_msg
    
    def _generate_code_explanation(
        self,
        code: str,
        section_name: str
    ) -> str:
        """
        Generate a high-level explanation of what the code does.
        
        Returns:
            Human-readable explanation string
        """
        # Truncate code for prompt
        code_preview = code[:1500] if len(code) > 1500 else code
        
        prompt = f"""Provide a brief, high-level explanation (3-4 sentences) of what this Python code does and how it implements the methodology from the "{section_name}" section of the paper.

Code:
{code_preview}

Write the explanation for a researcher who wants to understand the implementation at a glance. Focus on:
1. What algorithm/method it implements
2. Key steps in the implementation
3. What inputs it expects and outputs it produces

Explanation:"""
        
        try:
            if self._model is not None:
                gen_fn = getattr(self._model, "generate_content", None)
                if callable(gen_fn):
                    response = gen_fn(prompt)
                    explanation = (getattr(response, "text", "") or "").strip()
                    return explanation
            else:
                gen_content_fn = getattr(genai, "generate_content", None)
                if callable(gen_content_fn):
                    response = gen_content_fn(model=self.model_name, prompt=prompt)
                    explanation = (getattr(response, "text", "") or "").strip()
                    return explanation
            
            # Fallback
            return f"Python implementation of the {section_name} methodology described in the paper."
            
        except Exception as e:
            logger.warning(f"Failed to generate explanation: {e}")
            return f"Python implementation of the {section_name} methodology described in the paper."
