"""
latex/decomment.py – Remove comments from LaTeX source
=======================================================

Responsibility
--------------
Strips LaTeX comments before further processing. Three classes are handled:

  Class 1 – Inline comments
             Code on a line followed by an unescaped '%': the '% …'
             portion is stripped, the code part is kept.
             '\\%' (escaped percent) is never treated as a comment start.

  Class 2 – Full-line comments
             Lines whose first non-whitespace character is '%' are removed
             entirely. Covers plain '%', '%%', '%%%', separator lines
             ('%%%%…'), and %%BLOCK / %%TEXTBLOCK markers (class 3).

  Class 3 – %%BLOCK / %%TEXTBLOCK markers
             Subsumed by class 2.

  Class 4 – %%%L2E_* structural markers
             Lines starting with '%%%L2E_' are never removed; they carry
             structural information consumed by later pipeline stages.
             %%%L2E_* markers that appear inline (mid-line) are also
             preserved; only the surrounding comment text is stripped.

Pipeline position
-----------------
  latex/deflate.py  →  [latex/decomment.py]  →  latex/expressions.py

Debug output
------------
  When Config.get().debug is True, the source is written to
  comments_pre.txt (before) and comments_post.txt (after) in
  Config.get().output_directory.
"""

import logging
import re

from config import Config, PROGRAM_NAME

_logger = logging.getLogger(f"{PROGRAM_NAME}.latex.decomment")

_L2E_MARKER    = re.compile(r'^\s*%%%L2E_')
_FULL_LINE     = re.compile(r'^\s*%')

# Alternation: keep %%%L2E_* inline markers; strip everything else from %
# The %%%L2E_ alternative must come first so it wins over the plain-% alternative.
_INLINE_OR_L2E = re.compile(r'(%%%L2E_[A-Z_]+(?:\{[^}]*\})?)|(?<!\\)%.*')


def decomment(text: str) -> str:
    """Remove LaTeX comments (classes 1–3); preserve %%%L2E_* markers."""
    cfg = Config.get()

    if cfg.debug:
        cfg.output_directory.mkdir(parents=True, exist_ok=True)
        pre = cfg.output_directory / "comments_pre.txt"
        pre.write_text(text, encoding="utf-8")
        _logger.info("Comments pre-replacement written to: %s", pre)

    result = _remove_comments(text)

    if cfg.debug:
        post = cfg.output_directory / "comments_post.txt"
        post.write_text(result, encoding="utf-8")
        _logger.info("Comments post-replacement written to: %s", post)

    return result


def _remove_comments(text: str) -> str:
    out = []
    for line in text.splitlines(keepends=True):
        # Class 4: structural markers — keep unchanged
        if _L2E_MARKER.match(line):
            out.append(line)
            continue

        content = line.rstrip('\n\r')
        eol     = line[len(content):]

        # Class 2 + 3: full-line comment — drop content, keep line ending
        if _FULL_LINE.match(content):
            out.append(eol)
            continue

        # Class 1: inline comment — strip from first unescaped %,
        # but preserve any %%%L2E_* markers that appear mid-line.
        content = _INLINE_OR_L2E.sub(lambda m: m.group(1) or '', content).rstrip()
        out.append(content + eol)

    return ''.join(out)