"""
Streamlit Web UI for Scientific Paper Summarizing Agent.

A beautiful, user-friendly web interface for summarizing scientific papers.
Upload PDFs, Word documents, or paste text directly to get AI-powered summaries.
"""

import streamlit as st
from pathlib import Path
import tempfile
import time
from datetime import datetime
from typing import Optional
import sys
import os
import re
import hashlib

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

try:
    from src.agent import SummarizingAgent
    from src.summarizers import Summary
    from src.processors import DocumentProcessorFactory
    from src.code_generator import CodeGenerator
    from src.utils.text_processor import (
        detect_sections,
        extract_section,
        list_detected_sections,
        detect_numbered_sections,
        extract_numbered_section,
        list_numbered_sections,
    )
    from config.settings import settings
except ImportError as e:
    st.error(f"Import error: {e}")
    st.error("Please install dependencies: pip install -r requirements.txt")
    st.stop()


# Page configuration
st.set_page_config(
    page_title="Scientific Paper Summarizer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    .summary-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


def compute_file_hash(file_content: bytes) -> str:
    """Compute SHA256 hash of file content for caching."""
    return hashlib.sha256(file_content).hexdigest()


@st.cache_resource(show_spinner=False)
def initialize_agent(model_name: Optional[str] = None) -> Optional[SummarizingAgent]:
    """
    Initialize the summarizing agent.
    Cached per model_name to avoid reinitializing unnecessarily.
    Cache is cleared when model_name changes.
    """
    try:
        if not settings.validate_api_key():
            return None
        agent = SummarizingAgent(model_name=model_name)
        return agent
    except Exception as e:
        st.error(f"Failed to initialize agent: {e}")
        return None


def display_summary(summary: Summary, code_generator: Optional[CodeGenerator] = None):
    """Display the generated summary in a beautiful format with code generation option."""
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Word Count", summary.word_count)
    with col2:
        st.metric("Key Findings", len(summary.key_findings))
    with col3:
        st.metric("Has Methodology", "✓" if summary.methodology else "✗")
    with col4:
        st.metric("Has Results", "✓" if summary.results else "✗")
    
    st.markdown("---")
    
    # Create tabs for different views (removed Code tab - now a standalone button)
    tab1, tab2, tab3 = st.tabs([
        "📋 Summary", 
        "🎯 Key Findings", 
        "📊 Sections"
    ])
    
    # Tab 1: Overview
    with tab1:
        st.markdown("### 📋 Overview")
        st.markdown(f'<div class="summary-box">{summary.overview}</div>', unsafe_allow_html=True)
        
        # Full summary download
        st.markdown("---")
        st.markdown("### 📥 Download Full Summary")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        download_content = f"""# {summary.title}

**Generated:** {timestamp}

---

{summary.full_summary}
"""
        
        st.download_button(
            label="Download as Markdown",
            data=download_content,
            file_name=f"{summary.title.replace(' ', '_')}_summary.md",
            mime="text/markdown"
        )
    
    # Tab 2: Key Findings
    with tab2:
        st.markdown("### 🎯 Key Findings")
        for i, finding in enumerate(summary.key_findings, 1):
            st.markdown(f"**{i}.** {finding}")
    
    # Tab 3: Sections
    with tab3:
        if summary.methodology:
            with st.expander("🔬 Methodology", expanded=False):
                st.write(summary.methodology)
        
        if summary.results:
            with st.expander("📊 Results", expanded=False):
                st.write(summary.results)
        
        if summary.conclusions:
            with st.expander("💡 Conclusions", expanded=False):
                st.write(summary.conclusions)


def display_section_summary(section_name: str, text: str):
    """Display a single-section summary."""
    word_count = len(text.split())
    st.markdown(f"### 🔍 Section Summary: {section_name.title()}")
    st.metric("Word Count", word_count)
    st.markdown(f'<div class="summary-box">{text}</div>', unsafe_allow_html=True)
    download_content = f"""# Section Summary: {section_name.title()}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## {section_name.title()}

{text}
"""
    st.download_button(
        label="Download Section Markdown",
        data=download_content,
        file_name=f"section_{section_name.lower().replace(' ','_')}_summary.md",
        mime="text/markdown"
    )


def process_section_from_text(raw_text: str, section_name: str, model_name: str) -> Optional[str]:
    """Extract and summarize a specific section from raw text."""
    if not raw_text.strip():
        return None
    if not section_name.strip():
        return None
    section_key = section_name.lower().strip()
    # Numeric-only (with dots) label -> numbered section mode
    numeric_mode = bool(re.match(r'^\d+(?:\.\d+)*$', section_key))
    # basic normalization
    aliases = {
        'methodology': 'methods',
        'conclusions': 'conclusion',
        'numerical results': 'results',
        'experimental results': 'results'
    }
    section_key = aliases.get(section_key, section_key)
    if numeric_mode:
        section_text = extract_numbered_section(raw_text, section_key)
        if not section_text:
            return None
        from src.summarizers import ScientificPaperSummarizer
        summarizer = ScientificPaperSummarizer(model_name=model_name)
        target_words = int(settings.summary_max_words * 0.6) if settings.summary_max_words else 300
        return summarizer._summarize_chunk(section_text, context=f"Section {section_key}", target_words=target_words)

    sections = detect_sections(raw_text)
    # direct match
    if section_key not in sections:
        # attempt fuzzy contains
        for s in sections.keys():
            if section_key in s or s in section_key:
                section_key = s
                break
    if section_key not in sections:
        return None
    section_text = extract_section(raw_text, section_key)
    if not section_text:
        return None
    # Use summarizer's chunk method for concise section summary
    from src.summarizers import ScientificPaperSummarizer
    summarizer = ScientificPaperSummarizer(model_name=model_name)
    target_words = int(settings.summary_max_words * 0.6) if settings.summary_max_words else 300
    summary_text = summarizer._summarize_chunk(section_text, context=section_key, target_words=target_words)  # noqa
    return summary_text


def process_uploaded_file(uploaded_file, agent: SummarizingAgent, title: Optional[str] = None, summary_max_words: Optional[int] = None):
    """Process an uploaded file and return summary with caching."""
    
    # Compute file hash for caching
    file_content = uploaded_file.getvalue()
    file_hash = compute_file_hash(file_content)
    
    # Create cache key based on file hash and parameters
    cache_key = f"{file_hash}_{title or uploaded_file.name}_{summary_max_words or settings.summary_max_words}"
    
    # Check if we have a cached summary
    if 'summary_cache' not in st.session_state:
        st.session_state['summary_cache'] = {}
    
    if cache_key in st.session_state['summary_cache']:
        st.info("📦 Using cached summary (no API call)")
        cached_data = st.session_state['summary_cache'][cache_key]
        # Store raw text for code generation
        st.session_state['last_paper_text'] = cached_data['raw_text']
        st.session_state['last_summary'] = cached_data['summary']
        return cached_data['summary'], None
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
        tmp_file.write(file_content)
        tmp_path = Path(tmp_file.name)
    
    try:
        # Show processing message
        with st.spinner(f"Processing {uploaded_file.name}..."):
            progress_bar = st.progress(0)
            
            # Step 1: Extract text
            progress_bar.progress(25)
            factory = DocumentProcessorFactory()
            raw_text = factory.extract_text(tmp_path)
            time.sleep(0.5)
            
            # Step 2: Analyze
            progress_bar.progress(50)
            time.sleep(0.5)
            
            # Step 3: Generate summary
            progress_bar.progress(75)
            summary = agent.process_paper(
                tmp_path,
                title=title or uploaded_file.name,
                save_output=False,  # Don't save in web UI
                summary_max_words=summary_max_words,
            )
            
            progress_bar.progress(100)
            time.sleep(0.3)
            progress_bar.empty()
        
        # Store in cache
        if summary:
            st.session_state['summary_cache'][cache_key] = {
                'summary': summary,
                'raw_text': raw_text,
                'timestamp': datetime.now()
            }
            st.session_state['last_paper_text'] = raw_text
            st.session_state['last_summary'] = summary
        
        return summary, None
    
    except Exception as e:
        return None, str(e)
    
    finally:
        # Clean up temporary file
        try:
            tmp_path.unlink()
        except:
            pass


def process_text_input(text: str, agent: SummarizingAgent, title: str = "Custom Text", summary_max_words: Optional[int] = None):
    """Process direct text input and return summary with caching."""
    
    # Compute text hash for caching
    text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
    cache_key = f"text_{text_hash}_{title}_{summary_max_words or settings.summary_max_words}"
    
    # Check cache
    if 'summary_cache' not in st.session_state:
        st.session_state['summary_cache'] = {}
    
    if cache_key in st.session_state['summary_cache']:
        st.info("📦 Using cached summary (no API call)")
        cached_data = st.session_state['summary_cache'][cache_key]
        st.session_state['last_paper_text'] = text
        st.session_state['last_summary'] = cached_data['summary']
        return cached_data['summary'], None
    
    try:
        with st.spinner("Generating summary..."):
            progress_bar = st.progress(0)
            
            from src.summarizers import ScientificPaperSummarizer
            
            progress_bar.progress(50)
            summarizer = ScientificPaperSummarizer()
            
            progress_bar.progress(75)
            summary = summarizer.summarize(text, title=title, summary_max_words=summary_max_words)
            
            progress_bar.progress(100)
            time.sleep(0.3)
            progress_bar.empty()
        
        # Store in cache
        if summary:
            st.session_state['summary_cache'][cache_key] = {
                'summary': summary,
                'raw_text': text,
                'timestamp': datetime.now()
            }
            st.session_state['last_paper_text'] = text
            st.session_state['last_summary'] = summary
        
        return summary, None
    
    except Exception as e:
        return None, str(e)


def main():
    """Main Streamlit application."""
    
    # Header
    st.markdown('<p class="main-header">📚 Scientific Paper Summarizer</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-powered summarization using Google Gemini</p>', unsafe_allow_html=True)
    
    # Sidebar configuration
    st.sidebar.title("⚙️ Configuration")
    
    # API Key configuration (allow input from UI)
    st.sidebar.markdown("### 🔑 API Key")
    # Initialize session state for API key (cleared on browser close)
    if 'api_key' not in st.session_state:
        st.session_state['api_key'] = ""
    
    api_key_input = st.sidebar.text_input(
        "Google API Key",
        type="password",
        value=st.session_state['api_key'],
        placeholder="Enter or paste key",
        help="🔒 Stored only in browser session - automatically cleared when you close the tab",
        key="api_key_input"
    )
    
    # Update session state when key changes (auto-apply)
    if api_key_input != st.session_state['api_key']:
        st.session_state['api_key'] = (api_key_input or "").strip()
        initialize_agent.clear()
    
    # Add clear button for convenience
    if st.sidebar.button("🗑️ Clear Key", help="Clear the API key", use_container_width=True):
        st.session_state['api_key'] = ""
        initialize_agent.clear()
        st.rerun()
    
    # Validate and show status (uses session state from settings.py)
    if settings.validate_api_key():
        st.sidebar.success("✅ API Key Configured")
        st.sidebar.info("🔒 Key cleared when tab closes")
    else:
        st.sidebar.error("⚠️ API Key Missing.")
        st.sidebar.info("Enter your Google API key above")
        st.sidebar.markdown(
        "💡 **Don't have an API key?**  \n"
        "Get one free at: [Google AI Studio](https://makersuite.google.com/app/apikey)"
        )
        st.stop()
    
    # Model selection
    model_options = [
        "gemini-2.5-flash",          # Fast and cost-effective
        "gemini-2.5-pro",            # Most capable
        "gemini-2.0-flash",          # Stable Gemini 2.0
        "gemini-flash-latest",       # Always latest flash
        "gemini-pro-latest",         # Always latest pro
    ]
    selected_model = st.sidebar.selectbox(
        "Select Model",
        model_options,
        index=0,
        help="Choose the Gemini model for summarization"
    )
    
    # Advanced settings
    with st.sidebar.expander("🔧 Advanced Settings"):
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.1,
            help="Lower = more factual, Higher = more creative"
        )
        
        max_words = st.number_input(
            "Max Summary Words",
            min_value=200,
            max_value=2000,
            value=500,
            step=50,
            help="Target word count for summary"
        )
    
    # Cache management
    with st.sidebar.expander("💾 Cache Management"):
        if 'summary_cache' in st.session_state and st.session_state['summary_cache']:
            cache_count = len(st.session_state['summary_cache'])
            st.write(f"**Cached summaries:** {cache_count}")
            if st.button("🗑️ Clear Cache", use_container_width=True):
                st.session_state['summary_cache'] = {}
                st.sidebar.success("Cache cleared!")
                st.rerun()
        else:
            st.write("No cached summaries yet")
    
    # Update settings
    settings.temperature = temperature
    settings.summary_max_words = max_words
    settings.model_name = selected_model  # Update global settings too
    
    # Initialize agent and code generator (cached per model)
    agent = initialize_agent(model_name=selected_model)
    if not agent:
        st.error("Failed to initialize agent. Please check your configuration.")
        st.stop()
    
    # Initialize code generator (create fresh each time to respect model changes)
    code_generator_key = f"code_gen_{selected_model}"
    if code_generator_key not in st.session_state or st.session_state.get('last_model') != selected_model:
        try:
            st.session_state[code_generator_key] = CodeGenerator(model_name=selected_model)
            st.session_state['last_model'] = selected_model
            code_generator = st.session_state[code_generator_key]
        except Exception as e:
            st.warning(f"Code generation disabled: {e}")
            code_generator = None
    else:
        code_generator = st.session_state.get(code_generator_key)
    
    # Main content area
    st.markdown("---")
    
    # Input method tabs
    tab1, tab2, tab3 = st.tabs(["📄 Upload File", "✏️ Paste Text", "ℹ️ About"])
    
    # Tab 1: File Upload
    with tab1:
        st.markdown("### Upload a Scientific Paper")
        st.markdown("Supported formats: PDF, TXT, MD, DOCX")
        
        col1, col2 = st.columns([2, 1])

        with col1:
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=["pdf", "txt", "md", "docx"],
                help="Upload your scientific paper"
            )
        with col2:
            section_name = st.text_input(
                "Section to summarize (optional)",
                placeholder="e.g. Introduction, Methods, Results"
            )
            full_title = st.text_input(
                "Custom Title (optional)",
                placeholder="Auto-detected from file"
            )
        
        if uploaded_file is not None:
            st.info(f"📁 File: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
            
            # Extract text immediately when file is uploaded (for code generation)
            if 'current_file' not in st.session_state or st.session_state.get('current_file') != uploaded_file.name:
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = Path(tmp_file.name)
                try:
                    factory = DocumentProcessorFactory()
                    raw_text = factory.extract_text(tmp_path)
                    st.session_state['last_paper_text'] = raw_text
                    st.session_state['current_file'] = uploaded_file.name
                except Exception as e:
                    st.warning(f"⚠️ Text extraction failed: {e}")
                finally:
                    try:
                        tmp_path.unlink()
                    except:
                        pass
            
            generate_col, section_col, code_col = st.columns(3)
            with generate_col:
                if st.button("🚀 Full Summary", type="primary", use_container_width=True):
                    summary, error = process_uploaded_file(
                        uploaded_file,
                        agent,
                        title=full_title if full_title else None,
                        summary_max_words=max_words,
                    )
                    if error:
                        # Check for rate limit errors
                        if "429" in str(error) or "rate limit" in str(error).lower() or "quota" in str(error).lower():
                            st.error("⏱️ **API Rate Limit Exceeded**")
                            st.warning(
                                "You've hit the free tier rate limit (5 requests/minute for gemini-2.5-flash). "
                                "Please wait ~60 seconds and try again, or:\n"
                                "- Switch to a slower model in the sidebar\n"
                                "- Use a smaller paper\n"
                                "- Reduce 'Max Summary Words' to minimize API calls\n\n"
                                "**Tip:** The free tier resets every minute. "
                                "[Learn more about rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)"
                            )
                        else:
                            st.error(f"❌ Error: {error}")
                    elif summary:
                        st.success("✅ Summary Generated Successfully!")
                        st.markdown("---")
                        display_summary(summary, code_generator=code_generator)
            with section_col:
                if st.button("🔍 Section Only", use_container_width=True):
                    raw_text = st.session_state.get('last_paper_text', '')
                    if not raw_text:
                        st.error("Please wait for text extraction to complete")
                    elif not section_name.strip():
                        st.warning("Provide a section name first")
                    else:
                        section_summary = process_section_from_text(raw_text, section_name, selected_model)
                        if section_summary:
                            st.success("Section summarized")
                            st.markdown("---")
                            display_section_summary(section_name, section_summary)
                        else:
                            detected = list_detected_sections(raw_text)
                            if detected:
                                st.warning(f"Section not found. Detected sections: {', '.join(detected)}")
                            else:
                                st.warning("No sections detected in document. Try full summary.")
            
            with code_col:
                if st.button("💻 Generate Code", use_container_width=True):
                    st.session_state['show_code_gen'] = True
            
            # Show code generation UI if button was clicked
            if st.session_state.get('show_code_gen', False):
                raw_text = st.session_state.get('last_paper_text', '')
                if not raw_text:
                    st.error("Please wait for text extraction to complete")
                    st.session_state['show_code_gen'] = False
                elif not code_generator:
                    st.error("Code generator not available")
                    st.session_state['show_code_gen'] = False
                else:
                    st.markdown("---")
                    st.markdown("### 💻 Code Generation")
                    
                    # Initialize temp summary if needed
                    if 'temp_summary' not in st.session_state:
                        from src.summarizers import Summary
                        st.session_state['temp_summary'] = Summary(
                            title=full_title if full_title else uploaded_file.name,
                            overview="",
                            key_findings=[],
                            methodology=None,
                            results=None,
                            conclusions=None,
                            full_summary="",
                            word_count=0
                        )
                    
                    temp_summary = st.session_state['temp_summary']
                    
                    # Mode selection: Auto-detect vs Manual selection
                    gen_mode = st.radio(
                        "Selection Mode:",
                        ["🔍 Auto-detect code-worthy sections", "✏️ Choose any section or custom text"],
                        horizontal=True
                    )
                    
                    if gen_mode.startswith("🔍"):
                        # Auto-detect mode (original behavior)
                        if 'code_sections_standalone' not in st.session_state:
                            with st.spinner("Detecting code-worthy sections..."):
                                st.session_state['code_sections_standalone'] = code_generator.get_code_worthy_sections(temp_summary, raw_text)
                        
                        code_sections = st.session_state.get('code_sections_standalone', [])
                        
                        if not code_sections:
                            st.warning("No implementable sections detected. Try manual mode.")
                            if st.button("← Back to Upload"):
                                st.session_state['show_code_gen'] = False
                                st.rerun()
                        else:
                            st.info(f"**Detected {len(code_sections)} sections:** {', '.join(code_sections)}")
                            
                            col_select, col_back = st.columns([4, 1])
                            with col_select:
                                selected_section = st.selectbox(
                                    "Choose section to implement:",
                                    options=code_sections,
                                    key="standalone_code_section"
                                )
                            with col_back:
                                st.write("")
                                st.write("")
                                if st.button("← Back"):
                                    st.session_state['show_code_gen'] = False
                                    st.session_state.pop('code_sections_standalone', None)
                                    st.session_state.pop('temp_summary', None)
                                    st.rerun()
                            
                            if st.button("🚀 Generate Implementation", type="primary"):
                                with st.spinner(f"Generating code for {selected_section}..."):
                                    code, explanation, error = code_generator.generate_for_section(
                                        section_name=selected_section,
                                        raw_text=raw_text,
                                        summary=temp_summary
                                    )
                                
                                if error:
                                    st.error(f"❌ {error}")
                                    if "Rate Limit" in error:
                                        st.warning("💡 Tip: Wait 60 seconds or switch to gemini-2.5-pro")
                                elif code:
                                    st.success("✅ Code Generated!")
                                    st.markdown(f"### 📝 {selected_section}")
                                    st.info(explanation)
                                    st.code(code, language="python")
                                    st.download_button(
                                        label="📥 Download Python File",
                                        data=code,
                                        file_name=f"{selected_section.lower().replace(' ', '_')}_implementation.py",
                                        mime="text/x-python"
                                    )
                    
                    else:
                        # Manual mode - list ALL detected sections + custom input
                        from src.utils.text_processor import detect_sections, list_detected_sections
                        all_sections = list_detected_sections(raw_text)
                        
                        st.info(f"**All detected sections:** {', '.join(all_sections) if all_sections else 'None - use custom text'}")
                        
                        col_select, col_back = st.columns([4, 1])
                        with col_select:
                            if all_sections:
                                # Add "Custom text" option
                                section_options = all_sections + ["📝 Custom Text (enter below)"]
                                selected_section = st.selectbox(
                                    "Choose ANY section or use custom text:",
                                    options=section_options,
                                    key="manual_code_section"
                                )
                            else:
                                selected_section = "📝 Custom Text (enter below)"
                                st.write("No sections detected - use custom text below")
                        with col_back:
                            st.write("")
                            st.write("")
                            if st.button("← Back"):
                                st.session_state['show_code_gen'] = False
                                st.session_state.pop('code_sections_standalone', None)
                                st.session_state.pop('temp_summary', None)
                                st.rerun()
                        
                        # Custom text input for manual mode
                        if selected_section == "📝 Custom Text (enter below)":
                            custom_text = st.text_area(
                                "Enter the text/methodology to implement:",
                                height=200,
                                placeholder="Paste algorithm description, methodology, or any text you want to convert to Python code..."
                            )
                            section_display = "Custom Implementation"
                            text_to_implement = custom_text
                        else:
                            section_display = selected_section
                            text_to_implement = None  # Will be extracted from raw_text
                        
                        if st.button("🚀 Generate Implementation", type="primary"):
                            if selected_section == "📝 Custom Text (enter below)" and not custom_text.strip():
                                st.error("Please enter text to implement")
                            else:
                                with st.spinner(f"Generating code for {section_display}..."):
                                    if text_to_implement:
                                        # Generate from custom text - create temporary summary
                                        custom_summary = Summary(
                                            title="Custom Implementation",
                                            overview=text_to_implement[:500],
                                            key_findings=[],
                                            methodology=text_to_implement,
                                            results=None,
                                            conclusions=None,
                                            full_summary=text_to_implement,
                                            word_count=len(text_to_implement.split())
                                        )
                                        code, explanation, error = code_generator.generate_for_section(
                                            section_name=section_display,
                                            raw_text=text_to_implement,
                                            summary=custom_summary
                                        )
                                    else:
                                        # Generate from detected section
                                        code, explanation, error = code_generator.generate_for_section(
                                            section_name=selected_section,
                                            raw_text=raw_text,
                                            summary=temp_summary
                                        )
                                
                                if error:
                                    st.error(f"❌ {error}")
                                    if "Rate Limit" in error:
                                        st.warning("💡 Tip: Wait 60 seconds or switch to gemini-2.5-pro")
                                elif code:
                                    st.success("✅ Code Generated!")
                                    st.markdown(f"### 📝 {section_display}")
                                    st.info(explanation)
                                    st.code(code, language="python")
                                    st.download_button(
                                        label="📥 Download Python File",
                                        data=code,
                                        file_name=f"{section_display.lower().replace(' ', '_')}_implementation.py",
                                        mime="text/x-python"
                                    )
    
    # Tab 2: Text Input
    with tab2:
        st.markdown("### Paste Paper Text")
        st.markdown("Copy and paste the content of your scientific paper")
        
        text_title = st.text_input(
            "Paper Title",
            placeholder="Enter paper title",
            key="text_title"
        )
        section_name_text = st.text_input(
            "Section to summarize (optional)",
            placeholder="e.g. Abstract, Discussion, Conclusion",
            key="section_name_text"
        )
        
        text_input = st.text_area(
            "Paper Content",
            height=300,
            placeholder="Paste the full text of your scientific paper here...",
            help="Include sections like Abstract, Introduction, Methods, Results, Conclusion"
        )
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🚀 Full Summary from Text", type="primary", use_container_width=True):
                if not text_input.strip():
                    st.warning("⚠️ Paste text first")
                elif not text_title.strip():
                    st.warning("⚠️ Enter a title")
                else:
                    summary, error = process_text_input(
                        text_input,
                        agent,
                        title=text_title,
                        summary_max_words=max_words,
                    )
                    if error:
                        # Check for rate limit errors
                        if "429" in str(error) or "rate limit" in str(error).lower() or "quota" in str(error).lower():
                            st.error("⏱️ **API Rate Limit Exceeded**")
                            st.warning(
                                "You've hit the free tier rate limit (5 requests/minute for gemini-2.5-flash). "
                                "Please wait ~60 seconds and try again, or:\n"
                                "- Switch to a slower model in the sidebar\n"
                                "- Use shorter text\n"
                                "- Reduce 'Max Summary Words' to minimize API calls\n\n"
                                "**Tip:** The free tier resets every minute. "
                                "[Learn more about rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)"
                            )
                        else:
                            st.error(f"❌ Error: {error}")
                    elif summary:
                        st.success("✅ Summary Generated Successfully!")
                        st.markdown("---")
                        display_summary(summary, code_generator=code_generator)
        with col_b:
            if st.button("🔍 Section Only from Text", use_container_width=True):
                if not text_input.strip():
                    st.warning("⚠️ Paste text first")
                elif not section_name_text.strip():
                    st.warning("⚠️ Enter a section name")
                else:
                    section_summary = process_section_from_text(text_input, section_name_text, selected_model)
                    if section_summary:
                        st.success("Section summarized")
                        st.markdown("---")
                        display_section_summary(section_name_text, section_summary)
                    else:
                        detected = list_detected_sections(text_input)
                        if detected:
                            st.warning(f"Section not found. Detected sections: {', '.join(detected)}")
                        else:
                            st.warning("No sections detected in text.")
    
    # Tab 3: About
    with tab3:
        st.markdown("### 📖 About This Application")
        
        st.markdown("""
        This application uses **Google's Generative AI (Gemini)** to automatically 
        summarize scientific papers and generate Python implementations. It provides:
        
        - **📋 Comprehensive Overview**: 200-300 word summary of the paper
        - **🎯 Key Findings**: 3-5 bullet points of main results
        - **🔬 Methodology**: Summary of research methods
        - **📊 Results**: Key experimental or analytical results
        - **💡 Conclusions**: Main takeaways and implications
        - **💻 Code Generation**: Auto-generate Python implementations from methodology sections
        
        #### How It Works
        
        1. **Extract**: Text is extracted from your document
        2. **Analyze**: The paper is analyzed for sections (Abstract, Methods, etc.)
        3. **Summarize**: Each section is summarized using AI
        4. **Synthesize**: A cohesive overview is generated
        5. **Generate Code**: Convert methodology into production-ready Python code
        6. **Present**: Results are displayed in an easy-to-read format
        
        #### Features
        
        - ✅ Multiple file formats (PDF, DOCX, TXT, MD)
        - ✅ Direct text input
        - ✅ Section-aware processing
        - ✅ **Smart code generation** with type hints and docstrings
        - ✅ **Auto-detect implementable sections** or choose any section manually
        - ✅ **Smart caching** - avoid redundant API calls
        - ✅ Customizable AI models (Gemini 2.5 Flash/Pro)
        - ✅ Adjustable summarization parameters
        - ✅ Download summaries as Markdown or code as Python files
        
        #### Code Generation
        
        The app can automatically generate Python implementations from research papers:
        
        - **Auto-Detection**: Identifies sections with algorithms/methods
        - **Manual Selection**: Choose any section or paste custom text
        - **Production-Ready**: Generates code with type hints, docstrings, and examples
        - **Syntax Validation**: Ensures generated code is syntactically correct
        - **Download**: Export as `.py` files ready to use
        
        #### Technology Stack
        
        - **AI Model**: Google Gemini 2.5 (Pro / Flash)
        - **Framework**: Streamlit
        - **Backend**: Python with clean architecture
        - **Processing**: pdfplumber, PyPDF2, python-docx
        - **Configuration**: Pydantic with environment-based settings
        
        #### Tips for Best Results
        
        - 📄 Use well-structured papers with clear sections
        - 🎯 Lower temperature (0.1-0.3) for factual summaries
        - 📊 Higher temperature (0.5-0.7) for creative interpretation
        - 📑 PDFs with good text quality work best
        - 💻 For code generation, papers with clear algorithm descriptions work best
        
        #### Privacy & Security
        
        - Files are processed temporarily and not stored
        - Temporary files are deleted after processing
        - Only text content is sent to Google's API
        - No data is saved or shared
        - API keys are stored securely in session state
        
        ---
        
        **Version**: 1.0.0  
        **Built with**: Streamlit + Google Gemini + Pydantic  
        **License**: MIT  
        **GitHub**: [Scientific-paper-summarizer](https://github.com/Retwika/Scientific-paper-summarizer)
        """)
        
        # Show current settings
        with st.expander("🔍 Current Configuration"):
            st.json({
                "Model": selected_model,
                "Temperature": temperature,
                "Max Summary Words": max_words,
                "API Key Status": "✅ Configured" if settings.validate_api_key() else "❌ Not Set"
            })
    
    # Footer
    st.markdown("---")
    st.markdown(
        '<div style="text-align: center; color: #666;">'
        '🚀 Powered by Google Gemini | Built with Streamlit | © 2026'
        '</div>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
