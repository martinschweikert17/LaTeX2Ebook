"""
latex/toc.py – Replace %%%L2E_TABLE_OF_CONTENT with a generated HTML TOC
=========================================================================

Reads the heading list built by convert_headings() and produces a
hierarchically indented, clickable table of contents.

Pipeline position
-----------------
  latex/headings.py  →  [latex/toc.py]  →  latex/footnotes.py
"""

import re
import logging

from config import PROGRAM_NAME
from latex.headings import get_toc_entries

_logger = logging.getLogger(f"{PROGRAM_NAME}.latex.toc")

_TOC_PLACEHOLDER = re.compile(r'^%%%L2E_TABLE_OF_CONTENT[^\n]*$', re.MULTILINE)

_LEVEL_CSS = {
    'part':          'toc-part',
    'chapter':       'toc-chapter',
    'section':       'toc-section',
    'subsection':    'toc-subsection',
    'subsubsection': 'toc-subsubsection',
}


def process_toc(text: str) -> str:
    """Replace %%%L2E_TABLE_OF_CONTENT with a generated HTML table of contents."""
    if not _TOC_PLACEHOLDER.search(text):
        return text

    entries = get_toc_entries()
    if not entries:
        _logger.warning("TOC placeholder found but no headings recorded")
        return _TOC_PLACEHOLDER.sub('', text)

    lines = []
    for e in entries:
        if f'id="{e["id"]}"' not in text:
            continue
        css     = _LEVEL_CSS.get(e['level'], 'toc-chapter')
        display = f"{e['num']} {e['title']}" if e['num'] else e['title']
        lines.append(f'<p class="toc-entry {css}"><a href="#{e["id"]}">{display}</a></p>')

    toc_html = '<nav class="toc">\n' + '\n'.join(lines) + '\n</nav>'
    return _TOC_PLACEHOLDER.sub(lambda _: toc_html, text)
