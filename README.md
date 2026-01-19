# 📚 Scientific Paper Summarizing Agent

AI-powered tool to automatically summarize scientific papers using Google Gemini.

## ✨ Features

- 📄 **Multi-format support**: PDF, DOCX, TXT, Markdown
- 🧠 **Smart analysis**: Detects sections (Abstract, Methods, Results, etc.)
- 🎯 **Structured output**: Overview + Key Findings + Detailed sections
- 💻 **Code Generation**: Auto-generate Python implementations from methodology sections
- 🌐 **Two interfaces**: Web UI (Streamlit) + CLI
- 📦 **Smart Caching**: Avoid redundant API calls for same document
- ⚙️ **Configurable**: Model, temperature, word limits

## 🚀 Quick Start

> Python 3.10+ (3.11 recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "GOOGLE_API_KEY=your_key" > .env
streamlit run streamlit_app.py
```

**Get API Key (FREE):** https://makersuite.google.com/app/apikey

---

## 📦 Usage

### 🌐 Web Interface (Recommended)

```bash
streamlit run streamlit_app.py
```

**Features:**
- 📄 Drag & drop PDF/DOCX/TXT/Markdown files or paste text
- 🎯 View structured summary (Overview, Key Findings, Sections)
- 💻 **Generate Python code from methodology sections**
  - Auto-detect implementable sections
  - Manual selection for any section
  - Custom text input for code generation
- 📦 Smart caching - no redundant API calls
- 🎨 Adjust model, temperature, summary length
- 📥 Download summary as Markdown or code as Python file

### 💻 Command Line

```bash
# Single paper
python main.py --file paper.pdf

# Batch processing (recursive)
python main.py --directory papers/ --recursive

# Custom settings
python main.py --file paper.pdf --model gemini-2.5-flash --temperature 0.3 --summary-max-words 600 --verbose
```

### 🔧 Programmatic Usage

```python
from src.agent import SummarizingAgent

agent = SummarizingAgent()
summary = agent.process_paper("paper.pdf")

print(summary.overview)
print(summary.key_findings)
```

### 💻 Code Generation

Generate Python implementations from research papers:

```python
from src.code_generator import CodeGenerator
from src.processors import DocumentProcessorFactory

# Extract text from paper
factory = DocumentProcessorFactory()
raw_text = factory.extract_text("paper.pdf")

# Initialize code generator
code_gen = CodeGenerator(model_name="gemini-2.5-flash")

# Auto-detect implementable sections
code_sections = code_gen.get_code_worthy_sections(summary, raw_text)
print(f"Found sections: {code_sections}")  # e.g., ['Methods', 'Algorithm']

# Generate code for a specific section
code, explanation, error = code_gen.generate_for_section(
    section_name="Methods",
    raw_text=raw_text,
    summary=summary
)

if code:
    print(explanation)
    print(code)
    
    # Save to file
    with open("implementation.py", "w") as f:
        f.write(code)
```

**What gets generated:**
- ✅ Complete, runnable Python code
- ✅ Type hints and docstrings
- ✅ Working example with sample data
- ✅ Proper imports (NumPy, SciPy, etc.)
- ✅ Error handling and validation
---

## 🏗️ Architecture & Flow

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERFACE LAYER                          │
├─────────────────────────┬───────────────────────────────────┤
│   Streamlit UI          │         CLI (Click)               │
│   (streamlit_app.py)    │         (main.py)                 │
└──────────┬──────────────┴────────────────┬──────────────────┘
           │                                │
           ▼                                ▼
┌─────────────────────────────────────────────────────────────┐
│              ORCHESTRATION LAYER                            │
│                SummarizingAgent                             │
│          (src/agent/summarizing_agent.py)                   │
│  • Coordinates pipeline                                     │
│  • Manages document processing                              │
│  • Invokes summarization                                    │
│  • Handles output generation                                │
└──────────┬──────────────────────────────┬──────────────────┘
           │                                │
           ▼                                ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│   PROCESSING LAYER       │    │   SUMMARIZATION LAYER    │
│   DocumentProcessor      │    │  ScientificSummarizer    │
│  (src/processors/)       │    │  (src/summarizers/)      │
├──────────────────────────┤    ├──────────────────────────┤
│ • PDFProcessor           │    │ • Section detection      │
│ • DOCXProcessor          │    │ • Chunk summarization    │
│ • TXTProcessor           │    │ • Overview generation    │
│ • MarkdownProcessor      │    │ • Key findings extract   │
└──────────────────────────┘    │ • Full summary compile   │
                                 └──────────┬───────────────┘
                                            │
                                            ▼
                                 ┌──────────────────────────┐
                                 │   AI MODEL (Google)      │
                                 │   Gemini API             │
                                 │ • gemini-2.5-flash       │
                                 │ • gemini-2.5-pro         │
                                 └──────────────────────────┘
```

### Data Flow (User Request → Summary)

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Input Acquisition                                   │
└─────────────────────────────────────────────────────────────┘
    User uploads file (PDF/DOCX/TXT/MD) OR pastes text
    UI collects: file, title, model, temperature, max_words
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Configuration Load                                  │
└─────────────────────────────────────────────────────────────┘
    Settings loaded from .env + UI overrides
    effective_max_words = UI_value OR settings.summary_max_words
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Document Processing                                 │
└─────────────────────────────────────────────────────────────┘
    DocumentProcessorFactory.extract_text(file)
         │
         ├─→ PDF: pdfplumber + PyPDF2 fallback
         ├─→ DOCX: python-docx
         ├─→ TXT/MD: direct read with encoding detection
         │
    Returns: raw_text (string)
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Text Preprocessing                                  │
└─────────────────────────────────────────────────────────────┘
    clean_text(raw_text)
         │
         ├─→ Remove excessive whitespace
         ├─→ Normalize line breaks
         ├─→ Fix encoding issues
         │
    detect_sections(cleaned_text)
         │
         ├─→ Regex-based header detection
         ├─→ Returns: {section_name: (start_pos, end_pos)}
         │
    Returns: sections_dict
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Section Summarization                               │
└─────────────────────────────────────────────────────────────┘
    _summarize_sections(text, sections, effective_max_words)
         │
         ├─→ Calculate word budget per section
         │   total_budget = effective_max_words
         │   section_pool = 60% of total
         │   per_section = section_pool / num_sections
         │
         ├─→ For each priority section:
         │   │  (abstract, intro, methods, results, etc.)
         │   ├─→ Extract section text
         │   ├─→ Truncate to 4x target for compression
         │   └─→ Call Gemini API with prompt
         │
    Returns: {section_name: summary_text}
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Overview Generation                                 │
└─────────────────────────────────────────────────────────────┘
    _generate_overview(text, section_summaries, effective_max)
         │
         ├─→ If sections exist:
         │   │  Combine section summaries
         │   │  Target = 40% of effective_max_words
         │   └─→ Prompt: "synthesize integrated overview"
         │
         └─→ If NO sections (fallback):
             │  Use first 2000 chars of raw text
             │  Target = 60% of effective_max_words
             └─→ Prompt: "comprehensive overview from excerpt"
         │
    Returns: overview_text
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 7: Key Findings Extraction                             │
└─────────────────────────────────────────────────────────────┘
    _extract_key_findings(text, section_summaries)
         │
         ├─→ Focus on: results, discussion, conclusion sections
         ├─→ Fallback: use all section summaries OR raw text
         ├─→ Prompt: "extract 3-5 key findings as numbered list"
         │
    Returns: ["Finding 1", "Finding 2", ...]
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 8: Full Summary Compilation                            │
└─────────────────────────────────────────────────────────────┘
    _compile_full_summary(overview, sections, findings, ...)
         │
         ├─→ Assemble markdown structure:
         │   │  # SCIENTIFIC PAPER SUMMARY
         │   │  ## Overview
         │   │  ## Key Findings
         │   │  ## Methodology (if present)
         │   │  ## Results (if present)
         │   │  ## Conclusion (if present)
         │
         ├─→ Check word count vs target:
         │   │  If < 85% of target:
         │   └─→ _expand_summary() with source text
         │
         └─→ Enforce final cap:
             truncate_to_words(full, effective_max_words)
         │
    Returns: formatted_markdown_summary
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 9: Summary Object Creation                             │
└─────────────────────────────────────────────────────────────┘
    Summary(
        title, overview, key_findings,
        methodology, results, conclusions,
        full_summary, word_count
    )
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 10: Output & Display                                   │
└─────────────────────────────────────────────────────────────┘
    UI: Display formatted summary + metrics + download button
    CLI: Save to outputs/ directory as .md file
```

### Parameter Flow (UI Slider → Word Count Control)

```
User adjusts "Max Summary Words" slider (200-2000)
                 │
                 ▼
        max_words = st.number_input(...)
                 │
                 ▼
  process_uploaded_file(summary_max_words=max_words)
                 │
                 ▼
    agent.process_paper(summary_max_words=max_words)
                 │
                 ▼
   summarizer.summarize(summary_max_words=max_words)
                 │
                 ▼
  effective_max = summary_max_words OR settings.summary_max_words
                 │
                 ├─→ _summarize_sections(effective_max)
                 │       └─→ per_section_budget
                 │
                 ├─→ _generate_overview(effective_max)
                 │       └─→ overview_target_words
                 │
                 └─→ _compile_full_summary(effective_max)
                         └─→ final truncate_to_words(effective_max)
```

---

## 📂 Project Structure

```
.
├── streamlit_app.py       # Web UI
├── main.py                # CLI interface
├── config/settings.py     # Configuration
├── src/
│   ├── agent/            # Main orchestrator
│   ├── processors/       # Document extraction (PDF, DOCX, TXT)
│   ├── summarizers/      # AI summarization engine
│   └── utils/            # Helper functions
├── data/                 # Input papers
└── outputs/              # Generated summaries
```
---

## ⚙️ Configuration

Create/edit `.env` file:

```bash
# Required
GOOGLE_API_KEY=your_api_key_here

# Optional (defaults shown)
MODEL_NAME=gemini-2.5-flash
TEMPERATURE=0.3
SUMMARY_MAX_WORDS=500
```

Or edit `config/settings.py` for advanced options.
---

## 📚 Documentation

This repository has been cleaned for minimal distribution. All extended guides were removed.
Core usage is covered in this README.

---

## 🎯 Example Output

```
📋 Overview:
This paper presents a novel approach to climate prediction using 
machine learning, achieving 23% improvement in accuracy...

🎯 Key Findings:
1. Hybrid model combining LSTM and CNNs improves predictions by 23%
2. Polar regions showed highest improvement (28%)
3. Model maintains 0.42°C MAE across 5-year horizons

🔬 Methodology: [...detailed summary...]
📊 Results: [...detailed summary...]
💡 Conclusions: [...detailed summary...]
```

---

## 🚀 Deploy to Cloud (FREE)

Tip: In Streamlit Cloud, add GOOGLE_API_KEY under Settings > Secrets before first run.

---

## 🛠 Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| KeyError: 'GOOGLE_API_KEY' | Missing env var | Create `.env` with GOOGLE_API_KEY=... or set Streamlit secret |
| 404 model not found | Invalid MODEL_NAME | Use one of: gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash |
| Empty section summaries | Headings not detected | Ensure paper uses clear section headers (e.g. `## Methods`) |
| Very short overview | No sections parsed | Fallback kicks in; verify document formatting |
| Slow PDF processing | Large/scanned PDF | Prefer text-based PDFs; OCR not yet integrated |

If problems persist, run: `python main.py --file data/sample_paper.txt --verbose` to see pipeline logs.

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repository
4. Add API key as secret
5. Deploy!

(*Full deployment guide removed during repo cleanup; the above steps are sufficient.*)

---

## 🤝 Contributing

Contributions welcome! The code follows clean architecture principles.

---

## 📄 License

MIT License - Feel free to use for any purpose.

---

## 🙏 Acknowledgments

- Powered by **Google Gemini** AI
- Built with **Streamlit**, **Pydantic**, **Click**
- PDF processing by **pdfplumber** and **PyPDF2**
