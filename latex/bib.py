"""
latex/bib.py – BibTeX loading and plain-text conversion utilities
=================================================================

Shared by latex/literature.py (full bibliography processing) and
latex/footnotes.py (tooltip text generation).  Neither module depends
on the other; both import what they need from here.

Public API
----------
  get_bib()        – lazy-loaded, cached {key: fields_dict}
  _load_bib(path)  – parse a BibTeX file; internal but usable for testing
  _latex_to_text() – convert LaTeX markup to plain text
  _short_title()   – shorttitle or title field, cleaned
  CITETITLE_RE     – compiled regex for \\citetitle[...]{key}
"""

import re
import logging
from pathlib import Path

from config import Config, PROGRAM_NAME

_logger = logging.getLogger(f"{PROGRAM_NAME}.latex.bib")

# ── \\citetitle regex (shared with literature.py and footnotes.py) ─────────────

CITETITLE_RE = re.compile(r'\\citetitle(?:\[([^\]]*)\])?\{([^}]+)\}')

# ── BibTeX parser ──────────────────────────────────────────────────────────────

_ENTRY_RE = re.compile(r'@(\w+)\{(\w+)\s*,', re.IGNORECASE)


def _load_bib(bib_path: str | Path) -> dict[str, dict]:
    """Parse a BibTeX file; return {key: fields_dict}."""
    path = Path(bib_path).expanduser()
    if not path.exists():
        _logger.warning("Bib file not found: %s", path)
        return {}

    text = path.read_text(encoding='utf-8', errors='replace')
    entries: dict[str, dict] = {}
    i = 0
    n = len(text)

    while i < n:
        m = _ENTRY_RE.search(text, i)
        if not m:
            break

        entry_type = m.group(1).lower()
        key        = m.group(2)
        j          = m.end()          # depth=1: we consumed the opening '{'

        depth = 1
        while j < n and depth > 0:
            c = text[j]
            if   c == '{': depth += 1
            elif c == '}': depth -= 1
            j += 1

        body            = text[m.end():j - 1]
        fields          = _parse_fields(body)
        fields['_type'] = entry_type
        fields['_key']  = key
        entries[key]    = fields
        i = j

    return entries


def _parse_fields(body: str) -> dict[str, str]:
    """Parse BibTeX field assignments from an entry body."""
    fields: dict[str, str] = {}
    i = 0
    n = len(body)

    while i < n:
        # Skip whitespace and commas between fields
        while i < n and body[i] in ' \t\n\r,':
            i += 1
        if i >= n:
            break

        eq = body.find('=', i)
        if eq < 0:
            break

        name = body[i:eq].strip().lower()
        if not re.match(r'^[a-zA-Z_]\w*$', name):
            i = eq + 1
            continue

        i = eq + 1
        while i < n and body[i] in ' \t\n\r':
            i += 1
        if i >= n:
            break

        if body[i] == '{':
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if   body[j] == '{': depth += 1
                elif body[j] == '}': depth -= 1
                j += 1
            fields[name] = body[i + 1:j - 1]
            i = j
        elif body[i] == '"':
            j = i + 1
            while j < n and body[j] != '"':
                if body[j] == '\\':
                    j += 1
                j += 1
            fields[name] = body[i + 1:j]
            i = j + 1
        else:
            j = i
            while j < n and body[j] not in ',}':
                j += 1
            fields[name] = body[i:j].strip()
            i = j

    return fields


# ── LaTeX → plain text ────────────────────────────────────────────────────────

_LATEX_CHARS = [
    (r'\"a', 'ä'), (r'\"o', 'ö'), (r'\"u', 'ü'),
    (r'\"A', 'Ä'), (r'\"O', 'Ö'), (r'\"U', 'Ü'),
    (r'\"e', 'ë'), (r'\"E', 'Ë'),
    (r"\'e", 'é'), (r"\'a", 'á'), (r"\'o", 'ó'), (r"\'u", 'ú'), (r"\'i", 'í'),
    (r'\`e', 'è'), (r'\`a', 'à'), (r'\`o', 'ò'),
    (r'\^a', 'â'), (r'\^e', 'ê'), (r'\^o', 'ô'), (r'\^u', 'û'),
    (r'\~n', 'ñ'), (r'\~a', 'ã'), (r'\~o', 'õ'),
    (r'{\ss}', 'ß'), (r'\ss', 'ß'),
    (r'{\ae}', 'æ'), (r'\ae', 'æ'),
    (r'{\AA}', 'Å'), (r'\AA', 'Å'),
    (r'{[}', '['),  (r'{]}', ']'),
    (r'\&', '&'),
    (r'\-', ''),
    ('~', ' '),
]


def _latex_to_text(s: str) -> str:
    if not s:
        return ''
    s = re.sub(r'\\enquote\{([^{}]*)\}', r'"\1"', s)
    for latex, uni in _LATEX_CHARS:
        s = s.replace(latex, uni)
    # Strip {…} braces iteratively (handles nesting)
    for _ in range(5):
        s2 = re.sub(r'\{([^{}]*)\}', r'\1', s)
        if s2 == s:
            break
        s = s2
    # Remove remaining backslash commands
    s = re.sub(r'\\[a-zA-Z]+\s*', '', s)
    return s.strip()


# ── Title helper ──────────────────────────────────────────────────────────────

def _short_title(entry: dict) -> str:
    """Return shorttitle if present, otherwise title, as plain text."""
    return _latex_to_text(entry.get('shorttitle', '') or entry.get('title', ''))


# ── Lazy-loaded bib cache ──────────────────────────────────────────────────────

_BIB: dict[str, dict] | None = None


def get_bib() -> dict[str, dict]:
    """Return the cached bib dict, loading it from Config.bib_file on first call."""
    global _BIB
    if _BIB is None:
        cfg  = Config.get()
        _BIB = _load_bib(cfg.bib_file) if cfg.bib_file else {}
    return _BIB
