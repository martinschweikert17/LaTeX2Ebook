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
  latex/refs.py  →  [latex/footnotes.py]  →  latex/expressions.build_paragraphs

  Note: footnotes.py runs BEFORE refs.py so that \\label{} commands inside
  footnote bodies are registered in the label map before \\ref{} is resolved.
"""

import re
import logging

from config import Config, PROGRAM_NAME
from latex.bib import CITETITLE_RE as _CITETITLE_RE, _short_title, get_bib
from latex.formatting import convert_quotehebrew
from latex.headings import get_label_map

_logger = logging.getLogger(f"{PROGRAM_NAME}.latex.footnotes")

_FN_SECTION = re.compile(
    r'^%%%L2E_FOOTNOTES_SECTION_BEGIN[^\n]*\n(.*?)^%%%L2E_FOOTNOTES_SECTION_END[^\n]*\n?',
    re.MULTILINE | re.DOTALL,
)
_FN_PLACEHOLDER = '%%%L2E_FOOTNOTES'

_LABEL_IN_FN = re.compile(r'\\label\{([^}]+)\}')

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

        fn_labels = _LABEL_IN_FN.findall(body)
        body = _LABEL_IN_FN.sub('', body)

        footnotes.append((best_kind, body))
        fn_num = len(footnotes)

        label_map = get_label_map()
        for lbl in fn_labels:
            label_map[lbl] = {'num': str(fn_num), 'title': '', 'tag': 'fn',
                              'href': f'#fn-{fn_num}'}

        if htmlonly:
            tip = _tooltip_text(body)
            out.append(
                f'<a id="fnref-{fn_num}" href="#fn-{fn_num}"'
                f' class="footnote-ref" data-fn="{tip}">[{fn_num}]</a>'
            )
        else:
            # Inline: split body on blank lines so build_paragraphs cannot
            # tear the block apart and strip the CSS class from continuations.
            paras = [p.strip() for p in _PARA_SPLIT.split(body) if p.strip()]
            elems = []
            last = len(paras) - 1
            for i, p in enumerate(paras):
                if best_kind == 'pfootnote':
                    css = 'pfootnote-inline' if i == 0 else 'pfootnote-inline-continuation'
                else:
                    css = 'footnote-inline'
                if i == last:
                    css += ' fn-inline-end'
                id_attr = f' id="fn-{fn_num}"' if i == 0 else ''
                elems.append(f'<p class="{css}"{id_attr}>{p}</p>')
            out.append('\n\n' + '\n'.join(elems) + '\n\n')

        i = j

    return ''.join(out), footnotes


_PARA_SPLIT = re.compile(r'\n[ \t]*\n+')

_LATEX_CMD_ARG = re.compile(r'\\[A-Za-z]+\{([^{}]*)\}')
_LATEX_CMD     = re.compile(r'\\[A-Za-z@]+')
_LATEX_SPECIAL = re.compile(r'\\[^A-Za-z\s]')
_HTML_TAG      = re.compile(r'<[^>]+>')


def _tooltip_text(body: str) -> str:
    """Strip LaTeX/HTML markup from a footnote body for use in data-fn attribute."""
    text = _HTML_TAG.sub('', body)
    # Resolve \citetitle{key} → short title before generic LaTeX stripping
    bib = get_bib()
    text = _CITETITLE_RE.sub(
        lambda m: _short_title(bib[m.group(2)]) if m.group(2) in bib else m.group(2),
        text,
    )
    prev = None
    while prev != text:
        prev = text
        text = _LATEX_CMD_ARG.sub(r'\1', text)
    text = _LATEX_CMD.sub('', text)
    text = _LATEX_SPECIAL.sub('', text)
    text = ' '.join(text.split())
    return text.replace('&', '&amp;').replace('"', '&quot;')


def _footnotes_html(footnotes: list[tuple[str, str]]) -> str:
    """Build HTML for the collected footnotes section.

    Multi-paragraph bodies (blank-line separated) are split into separate
    <p> elements so that build_paragraphs cannot tear them apart later.

    pfootnote:  first paragraph → p.pfootnote (no indent)
                subsequent     → p.pfootnote-continuation (text-indent)
    footnote:   all paragraphs → p.footnote (standard paragraph spacing)
    """
    parts = []
    for num, (kind, body) in enumerate(footnotes, 1):
        backref = f'<a href="#fnref-{num}" class="footnote-backref">&#11014;</a>'
        paras = [p.strip() for p in _PARA_SPLIT.split(body) if p.strip()]
        if not paras:
            continue

        for idx, para in enumerate(paras):
            is_first = idx == 0
            is_last  = idx == len(paras) - 1
            suffix   = f' {backref}' if is_last else ''

            if kind == 'pfootnote':
                css = 'pfootnote' if is_first else 'pfootnote-continuation'
            else:
                css = 'footnote'

            id_attr = f' id="fn-{num}"' if is_first else ''
            prefix  = f'[{num}] '       if is_first else ''
            parts.append(f'<p class="{css}"{id_attr}>{prefix}{para}{suffix}</p>')

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
