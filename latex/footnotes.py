"""
latex/footnotes.py – Process \\footnote and \\pfootnote commands
================================================================

Responsibility
--------------
Replaces \\footnote{body} and \\pfootnote{body} commands and resolves the
%%%L2E_FOOTNOTES_SECTION_BEGIN / %%%L2E_FOOTNOTES_SECTION_END markers.

HTML mode (Config.htmlonly is True):
  - Each \\footnote / \\pfootnote becomes a superscript link [N].
  - The collected footnotes are inserted at %%%L2E_FOOTNOTES.
  - The %%%L2E_FOOTNOTES_SECTION_BEGIN/END marker lines are stripped.
  - If no footnotes exist, the whole section is eliminated.

Inline mode (epub):
  - Each \\footnote / \\pfootnote is inserted immediately after the word
    it is attached to as an indented paragraph (no numbering, no links).
  - The entire %%%L2E_FOOTNOTES_SECTION_BEGIN … _END block is eliminated.

\\pfootnote differs from \\footnote only in CSS:
  - No vertical gap between consecutive pfootnotes.
  - text-indent marks the start of each paragraph instead.

Pipeline position
-----------------
  latex/headings.py  →  [latex/footnotes.py]  →  latex/expressions.build_paragraphs
"""

import re
import logging

from config import Config, PROGRAM_NAME
from latex.formatting import convert_quotehebrew

_logger = logging.getLogger(f"{PROGRAM_NAME}.latex.footnotes")

_FN_SECTION = re.compile(
    r'^%%%L2E_FOOTNOTES_SECTION_BEGIN[^\n]*\n(.*?)^%%%L2E_FOOTNOTES_SECTION_END[^\n]*\n?',
    re.MULTILINE | re.DOTALL,
)
_FN_PLACEHOLDER = '%%%L2E_FOOTNOTES'

# Longest trigger first so \pfootnote is never confused with \footnote
_TRIGGERS = (
    (r'\pfootnote{', 'pfootnote'),
    (r'\footnote{',  'footnote'),
)


def _scan_footnotes(text: str, htmlonly: bool) -> tuple[str, list[tuple[str, str]]]:
    """
    Scan *text* for \\footnote{} and \\pfootnote{} and replace them in-place.

    HTML mode  → superscript link [N].
    Inline mode → indented <p> paragraph inserted immediately after the word.

    Returns (processed_text, footnotes) where footnotes is a list of
    (kind, body) pairs; kind is 'footnote' or 'pfootnote'.
    """
    footnotes: list[tuple[str, str]] = []
    out: list[str] = []
    i = 0
    n = len(text)

    while i < n:
        # Find earliest trigger
        best_pos = n
        best_trig: str | None = None
        best_kind: str | None = None
        for trig, kind in _TRIGGERS:
            pos = text.find(trig, i)
            if 0 <= pos < best_pos:
                best_pos = pos
                best_trig = trig
                best_kind = kind

        if best_trig is None:
            out.append(text[i:])
            break

        out.append(text[i:best_pos])

        # Brace-counted body extraction
        j = best_pos + len(best_trig)   # first char after opening '{'
        depth = 1
        while j < n and depth > 0:
            if   text[j] == '{': depth += 1
            elif text[j] == '}': depth -= 1
            j += 1
        body = text[best_pos + len(best_trig) : j - 1]
        body = convert_quotehebrew(body, 'hebrew-footnote')

        footnotes.append((best_kind, body))
        fn_num = len(footnotes)

        if htmlonly:
            out.append(
                f'<a id="fnref-{fn_num}" href="#fn-{fn_num}"'
                f' class="footnote-ref">[{fn_num}]</a>'
            )
        else:
            # Inline: end current paragraph, insert footnote, new paragraph continues
            out.append(f'\n\n<p class="{best_kind}-inline">{body}</p>\n\n')

        i = j

    return ''.join(out), footnotes


def _footnotes_html(footnotes: list[tuple[str, str]]) -> str:
    """Build HTML for the collected footnotes section."""
    parts = []
    for num, (kind, body) in enumerate(footnotes, 1):
        backref = f'<a href="#fnref-{num}" class="footnote-backref">&#11014;</a>'
        parts.append(f'<p class="{kind}" id="fn-{num}">[{num}] {body} {backref}</p>')
    return '\n'.join(parts)


def process_footnotes(text: str) -> str:
    """Replace footnote commands and resolve %%%L2E_FOOTNOTES_SECTION_* markers."""
    cfg = Config.get()
    text, footnotes = _scan_footnotes(text, cfg.htmlonly)
    text = convert_quotehebrew(text)   # main text: standard hebrew class
    _logger.debug("Found %d footnote(s)", len(footnotes))

    if cfg.htmlonly:
        if footnotes:
            fn_html = _footnotes_html(footnotes)
            text = _FN_SECTION.sub(
                lambda m: m.group(1).replace(_FN_PLACEHOLDER, fn_html),
                text,
            )
        else:
            text = _FN_SECTION.sub('', text)
    else:
        text = _FN_SECTION.sub('', text)

    return text
