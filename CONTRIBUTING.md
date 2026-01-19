# Contributing to Scientific Paper Summarizer

Thank you for considering contributing to this project! 🎉

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](../../issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Your environment (Python version, OS, etc.)

### Suggesting Features

1. Check [Issues](../../issues) for existing feature requests
2. Create a new issue with:
   - Clear use case description
   - Why this feature would be useful
   - Possible implementation approach (if you have ideas)

### Pull Requests

1. **Fork the repository**
2. **Create a new branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**:
   - Follow existing code style (PEP 8)
   - Add type hints where applicable
   - Update docstrings
   - Test your changes
4. **Commit with clear messages**:
   ```bash
   git commit -m "Add: feature description"
   ```
5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Create Pull Request** with:
   - Clear description of changes
   - Reference related issues
   - Screenshots/examples if applicable

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/scientific-paper-summarizer.git
cd scientific-paper-summarizer

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Add your GOOGLE_API_KEY to .env

# Run tests
python main.py --help
streamlit run streamlit_app.py
```

## Code Style

- **Python**: Follow PEP 8
- **Docstrings**: Google style
- **Type hints**: Use where applicable
- **Line length**: Max 120 characters
- **Imports**: Group by standard lib, third-party, local

Example:
```python
from typing import Optional, List
import logging

from pydantic import BaseModel

from src.utils.logger import setup_logger


def process_document(path: str, max_words: Optional[int] = None) -> List[str]:
    """
    Process a document and extract sections.
    
    Args:
        path: Path to document file.
        max_words: Optional maximum word limit.
    
    Returns:
        List of extracted sections.
    """
    pass
```

## Areas for Contribution

### High Priority
- [ ] Unit tests for core modules
- [ ] Support for more document formats (LaTeX, HTML)
- [ ] arXiv API integration
- [ ] Batch processing improvements
- [ ] Error handling enhancements

### Medium Priority
- [ ] Fine-tuning prompts for specific domains
- [ ] Custom summarization templates
- [ ] Export formats (JSON, LaTeX, etc.)
- [ ] UI/UX improvements
- [ ] Documentation improvements

### Low Priority
- [ ] OCR for scanned PDFs
- [ ] Multi-language support
- [ ] Database integration for caching
- [ ] CLI progress bars and better formatting

## Questions?

Feel free to open an issue with the `question` label or reach out via the project's contact information.

---

**Happy coding!** 🚀
