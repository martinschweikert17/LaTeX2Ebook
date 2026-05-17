"""
latex/deflate.py – Remove irrelevant blocks from a LaTeX source string
=======================================================================

Responsibility
--------------
Strips two categories of blocks from the raw LaTeX source before
any further processing:

  1. Skip blocks – content between ``%%%L2E_SKIP_BEGIN`` and
     ``%%%L2E_SKIP_END`` markers (must appear at the start of a line).

  2. Language blocks – ``\\ifbool{LANG_<CODE>}{...}%LANG_<CODE>``
     constructs. The content is kept when <CODE> matches the configured
     language; otherwise the entire block is removed.

Pipeline position
-----------------
  latex/reader.py calls deflate()  →  [latex/deflate.py]

Expected inputs
---------------
  str                      – raw LaTeX source
  Config.get().language    – two-letter language code (e.g. "DE")

Produced output
---------------
  str  – deflated LaTeX source

Debug output
------------
  When Config.get().debug is True, the deflated source is written to
  ``deflated.txt`` in Config.get().output_directory for inspection.
"""

import logging
import re
from pathlib import Path

from config import Config, PROGRAM_NAME

_logger = logging.getLogger(f"{PROGRAM_NAME}.latex.deflate")

# Remove irrelevant blocks. These include
# 1. Areas surrounded by %%%L2E_SKIP_BEGIN and %%%L2E_SKIP_END (both at the beginning of a line)
# 2. Language-specific blocks. These are surrounded by "\ifbool{LANG_<CODE>}{" and "}%LANG_<CODE>",
#    where <CODE> is a 2-letter language code (e.g. DE,EN).

_SKIP_BLOCK = re.compile(
    r"^%%%L2E_SKIP_BEGIN[^\n]*\n.*?^%%%L2E_SKIP_END[^\n]*\n?",
    re.MULTILINE | re.DOTALL,
)

_LANG_OPEN = re.compile(r'\\ifbool\{LANG_([A-Z]{2})\}\s*\{')
# Optional closing comment on the same line: }%LANG_XX  or  }%LANG_XX BLOCK 57  etc.
_LANG_CLOSE = re.compile(r'[^\S\n]*%LANG_[A-Z]{2}[^\n]*')


def _deflate_lang(text: str, lang: str) -> str:
    """
    Brace-counting replacement for \\ifbool{LANG_XX}{...}%LANG_XX blocks.

    The block always ends at the brace-counted depth-0 closing '}'.
    The trailing %LANG_XX comment (with any extra text on that line) is
    optional — if present it is consumed; if absent the '}' alone closes
    the block.  Nesting is handled correctly because inner closing braces
    increment/decrement the depth counter and are never mistaken for the
    outer closing brace.
    """
    out = []
    i = 0
    n = len(text)
    while i < n:
        m = _LANG_OPEN.search(text, i)
        if m is None:
            out.append(text[i:])
            break

        # Copy everything before this match verbatim
        out.append(text[i:m.start()])
        block_lang = m.group(1)

        # Count braces to find the matching closing '}'
        depth = 1
        j = m.end()  # first char inside the block
        content_start = j

        while j < n and depth > 0:
            ch = text[j]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
            j += 1
        # j now points one past the closing '}'

        content = text[content_start:j - 1]

        # Consume optional same-line closing comment: %LANG_XX[rest of line]
        close_m = _LANG_CLOSE.match(text, j)
        end = close_m.end() if close_m else j

        if block_lang == lang:
            out.append(_deflate_lang(content, lang))

        i = end

    return ''.join(out)


def deflate(raw: str) -> str:
    """
    Removes skip blocks and non-matching language blocks from raw LaTeX source.

    Parameters
    ----------
    raw  – raw LaTeX source string

    Returns
    -------
    str  – deflated LaTeX source
    """
    cfg  = Config.get()
    lang = cfg.language.upper()

    # 1. Remove blocks marked for skipping

    result = _SKIP_BLOCK.sub("", raw)

    # 2. Remove language-specific blocks that do not match the configured language

    result = _deflate_lang(result, lang)

    # Kosmetik: Mehrere aufeinanderfolgende Zeilenumbrüche auf einen reduzieren

    if cfg.debug:
        out = cfg.output_directory / "deflated.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result, encoding="utf-8")
        _logger.info("Deflated source written to: %s", out)
    return result