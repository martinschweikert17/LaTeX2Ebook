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

    # \anchor{name}{title}: converter-native invisible anchor with a title.
    # The LaTeX definition \newcommand{\anchor}[2]{\phantomsection\label{#1}}
    # is multi-arg so expand_newcommands leaves the call sites intact.
    def _register_anchor(m: re.Match) -> str:
        name, title = m.group(1), m.group(2)
        labels[name] = {'num': '', 'title': title, 'tag': 'span'}
        return f'<span id="{name}"></span>'

    text = re.sub(r'\\anchor\{([^}]+)\}\{([^}]*)\}', _register_anchor, text)

    # Standalone \label{name} not consumed by convert_headings (e.g. after
    # \paragraph which apply_formatting already converted, or mid-paragraph
    # anchors): turn them into an invisible <span id> and register so that
    # \ref / \fullref can still resolve them.
    def _register_standalone(m: re.Match) -> str:
        name = m.group(1)
        if name not in labels:
            labels[name] = {'num': '', 'title': '', 'tag': 'span'}
        return f'<span id="{name}"></span>'

    text = re.sub(r'\\label\{([^}]+)\}', _register_standalone, text)

    def _ref_link(name: str) -> str:
        if name in labels:
            info = labels[name]
            href = info.get('href', f'#{name}')
            return f'<a href="{href}">{info["num"]}</a>'
        _logger.warning("Unknown label in \\ref: %s", name)
        return f'[?{name}]'

    def _fullref_link(name: str) -> str:
        if name in labels:
            info = labels[name]
            if not info['num'] and not info['title']:
                return f'<a class="fullref" href="#{name}">&#x2192;</a>'
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

    return text
