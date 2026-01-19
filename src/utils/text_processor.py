"""Minimal text processing utilities for the summarizing agent.

Restored and improved section detection with multi-strategy approach:
1. Line classification (numbered headings, markdown, uppercase short lines)
2. Keyword + synonym matching (Numerical Results -> results, Algorithm -> methods)
3. Fallback regex scan if sparse.
"""

import re
from typing import Tuple, Dict, List
from .logger import logger  # safe relative import


def clean_text(text: str) -> str:
    """Clean and normalize text while preserving line boundaries for section detection."""
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Remove isolated page numbers (page number lines)
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    # Common OCR ligature fixes
    text = text.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
    # Collapse excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
    return text.strip()



def detect_sections(text: str, debug: bool = False) -> Dict[str, Tuple[int, int]]:
    """Detect sections; tolerant of numbered/composite headers (e.g., '2 Numerical Results')."""
    # Map canonical section names to regex fragments
    keyword_map = {
        'abstract': r'abstract',
        'introduction': r'introduction',
        'methods': r'(method(?:s|ology)?|algorithm|least[- ]squares algorithm)',
        'results': r'(result(?:s)?|numerical results|experimental results)',
        'discussion': r'discussion',
        'conclusion': r'conclusion(?:s)?',
        'references': r'reference(?:s)?'
    }

    lines = text.split('\n')
    sections: Dict[str, Tuple[int, int]] = {}

    # Precompute cumulative character offsets for each line start
    offsets: List[int] = []
    total = 0
    for line in lines:
        offsets.append(total)
        total += len(line) + 1  # +1 for newline

    for canonical, pattern in keyword_map.items():
        for idx, line in enumerate(lines):
            raw = line.strip()
            if not raw:
                continue
            lowered = raw.lower()
            # Heuristic: header lines are short (< 80 chars) and not ending with a period (except abbreviations)
            if len(raw) > 80:
                continue
            # Patterns: numbered, markdown, plain, composite (e.g., Numerical Results)
            header_patterns = [
                rf'^#+\s*{pattern}(?:\b|\s|[:\-–—])',
                rf'^\d+\.?\d*(?:\.\d+)*\s+{pattern}(?:\b|\s|[:\-–—])',
                rf'^{pattern}(?:\b|\s|[:\-–—])',
                rf'^.*\b{pattern}\b.*$'  # composite line containing keyword
            ]
            matched = any(re.search(p, lowered) for p in header_patterns)
            if matched and debug:
                logger.info(f"Section candidate matched [{canonical}]: '{raw}' (line {idx})")
            if matched:
                # Avoid capturing lines that look like full sentences (end with period and contain multiple verbs)
                if lowered.endswith('.') and len(lowered.split()) > 6:
                    continue
                start_pos = offsets[idx]
                if canonical not in sections:  # first occurrence
                    sections[canonical] = (start_pos, len(text))
                break  # move to next canonical after first match

    # Adjust end boundaries based on next section start
    ordered = sorted(sections.items(), key=lambda kv: kv[1][0])
    for i in range(len(ordered) - 1):
        name, (s, _) = ordered[i]
        next_s = ordered[i + 1][1][0]
        sections[name] = (s, next_s)

    # Fallback pass: if we found fewer than 2 sections, do a broader regex scan
    if len(sections) < 2:
        if debug:
            logger.info("Primary pass found <2 sections; entering fallback scan.")
        fallback_patterns = []
        for canonical, pattern in keyword_map.items():
            # Look for newline, optional numbering, keyword, then up to 120 chars and a newline
            fb = re.compile(rf'(?:^|\n)(?P<header>(?:\d+\.?\d*(?:\.\d+)*\s+)?{pattern}[A-Za-z0-9 \-–—:]{{0,40}})(?:\n|$)', re.IGNORECASE)
            fallback_patterns.append((canonical, fb))
        for canonical, rgx in fallback_patterns:
            if canonical in sections:
                continue
            m = rgx.search(text)
            if m:
                start = m.start('header')
                sections[canonical] = (start, len(text))
                if debug:
                    logger.info(f"Fallback captured section [{canonical}] at char {start}: '{m.group('header').strip()}'")
        # Recompute ordering after fallback additions
        ordered = sorted(sections.items(), key=lambda kv: kv[1][0])
        for i in range(len(ordered) - 1):
            name, (s, _) = ordered[i]
            next_s = ordered[i + 1][1][0]
            sections[name] = (s, next_s)
    return sections


def extract_section(text: str, section_name: str) -> str:
    """
    Extract a specific section from the paper.
    
    Args:
        text: Full paper text
        section_name: Name of section to extract
        
    Returns:
        Extracted section text, or empty string if not found
    """
    sections = detect_sections(text)
    if section_name.lower() in sections:
        start, end = sections[section_name.lower()]
        return text[start:end].strip()
    return ""


def list_detected_sections(text: str) -> List[str]:
    """Return list of detected section names (ordered)."""
    sections = detect_sections(text)
    return sorted(sections.keys(), key=lambda k: sections[k][0])


# ---------------- Numbered Section Support -----------------

_NUMBERED_HEADING_RE = re.compile(r'^(?P<label>\d+(?:\.\d+)*)[\s\.-]+(?P<title>\S.*)$')

def detect_numbered_sections(text: str) -> Dict[str, Tuple[int, int]]:
    """Detect hierarchical numbered sections (1., 1.1, 2.3.4) and compute spans.

    Returns mapping: numeric label -> (start_char, end_char)
    Rules:
      - Heading line matches leading number groups separated by dots followed by space/dot/dash and a title
      - Section span includes all descendant sub-sections until next sibling or ancestor of same or lower depth
    """
    lines = text.split('\n')
    offsets: List[int] = []
    total = 0
    for line in lines:
        offsets.append(total)
        total += len(line) + 1

    entries: List[Dict] = []
    for idx, line in enumerate(lines):
        m = _NUMBERED_HEADING_RE.match(line.strip())
        if not m:
            continue
        label = m.group('label')
        title = m.group('title').strip()
        depth = label.count('.') + 1
        start = offsets[idx]
        entries.append({
            'label': label,
            'title': title,
            'depth': depth,
            'start': start
        })

    # Sort by start (already sequential if iterated lines)
    sections: Dict[str, Tuple[int, int]] = {}
    for i, entry in enumerate(entries):
        start = entry['start']
        depth = entry['depth']
        label = entry['label']
        # Find end: next entry with depth <= current depth and not a descendant
        end = len(text)
        for j in range(i + 1, len(entries)):
            other = entries[j]
            other_label = other['label']
            other_depth = other['depth']
            # A descendant starts with label + '.'
            if other_label.startswith(label + '.'):
                # descendant does not terminate parent
                continue
            if other_depth <= depth:
                end = other['start']
                break
        sections[label] = (start, end)
    return sections


def list_numbered_sections(text: str) -> List[str]:
    """List numeric section labels in order."""
    secs = detect_numbered_sections(text)
    return sorted(secs.keys(), key=lambda k: secs[k][0])


def extract_numbered_section(text: str, label: str) -> str:
    """Extract a numbered section span by label (e.g., '1', '1.2')."""
    secs = detect_numbered_sections(text)
    if label in secs:
        start, end = secs[label]
        return text[start:end].strip()
    return ""


def count_words(text: str) -> int:
    """Count words in text."""
    return len(re.findall(r'\b\w+\b', text))


def truncate_to_words(text: str, max_words: int) -> str:
    """Truncate text to a maximum number of words."""
    words = re.findall(r'\S+', text)
    if len(words) <= max_words:
        return text
    return ' '.join(words[:max_words]) + '...'
