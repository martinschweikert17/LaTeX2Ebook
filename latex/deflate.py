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

_LANG_BLOCK = re.compile(
    r"\\ifbool\{LANG_([A-Z]{2})\}\{(.*?)\}%LANG_\1",
    re.DOTALL,
)


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

    def _replace_lang(m: re.Match) -> str:
        return m.group(2) if m.group(1) == lang else ""

    result = _LANG_BLOCK.sub(_replace_lang, result)

    # Kosmetik: Mehrere aufeinanderfolgende Zeilenumbrüche auf einen reduzieren

    if cfg.debug:
        out = cfg.output_directory / "deflated.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result, encoding="utf-8")
        _logger.info("Deflated source written to: %s", out)
    return result