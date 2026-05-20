"""
latex/refs.py – Resolve LaTeX cross-references
===============================================

Responsibility
--------------
Replaces \\ref{}, \\pageref{}, \\fullref{} and removes remaining \\label{}
commands after convert_headings() has populated the label map.

  \\ref{name}      → <a href="#name">N</a>          (section number)
  \\pageref{name}  → <a href="#name">N</a>          (same; pages don't exist in HTML)
  \\fullref{name}  → <a href="#name">N Title</a>    (number + heading title)
  \\label{name}    → stripped (already consumed by convert_headings where
                     possible; any remaining ones are superfluous in HTML)

Unknown labels produce a warning and the literal text [?name].

Pipeline position
-----------------
  latex/headings.py  →  [latex/refs.py]  →  latex/footnotes.py
"""

import re
import logging

from config import PROGRAM_NAME
from latex.headings import get_label_map

_logger = logging.getLogger(f"{PROGRAM_NAME}.latex.refs")


def process_refs(text: str) -> str:
    """Resolve all cross-reference commands using the heading label map."""
    labels = get_label_map()

    def _ref_link(name: str) -> str:
        if name in labels:
            return f'<a href="#{name}">{labels[name]["num"]}</a>'
        _logger.warning("Unknown label in \\ref: %s", name)
        return f'[?{name}]'

    def _fullref_link(name: str) -> str:
        if name in labels:
            info = labels[name]
            title_span = f'<span class="fullref-title">{info["title"].replace(" ", "&nbsp;")}</span>'
            if info['num']:
                display = f'{info["num"]}&nbsp;{title_span}'
            else:
                display = title_span
            return f'<a class="fullref" href="#{name}">{display}</a>'
        _logger.warning("Unknown label in \\fullref: %s", name)
        return f'[?{name}]'

    # \ref*{} (starred variant used inside hyperref commands – same output)
    text = re.sub(r'\\ref\*?\{([^}]+)\}',     lambda m: _ref_link(m.group(1)),     text)
    text = re.sub(r'\\pageref\*?\{([^}]+)\}', lambda m: _ref_link(m.group(1)),     text)
    text = re.sub(r'\\fullref\{([^}]+)\}',    lambda m: _fullref_link(m.group(1)), text)

    # Remove any \label{} not already consumed by convert_headings
    text = re.sub(r'\\label\{[^}]+\}', '', text)

    return text
