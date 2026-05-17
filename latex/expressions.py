"""
latex/expressions.py – Convert LaTeX expressions to plain text or HTML
=======================================================================

Responsibility
--------------
Replaces LaTeX inline expressions and commands within the deflated
source with their plain-text or HTML equivalents. This is the second
preprocessing step before HTML conversion.

Pipeline position
-----------------
  latex/deflate.py  →  [latex/expressions.py]  →  html/converter.py

Expected inputs
---------------
  str  – deflated LaTeX source from deflate()

Produced output
---------------
  str  – LaTeX source with expressions converted
"""

import logging
import re

from config import Config, PROGRAM_NAME
from latex.bible_names import load_bible_names
from latex.cjhebrew import convert_cjhebrew
from latex.formatting import _eliminate_cmd, _replace_cmd

_logger = logging.getLogger(f"{PROGRAM_NAME}.latex.expressions")
_BIBLE_NAMES: dict[str, str] | None = None


def _bible_names() -> dict[str, str]:
    global _BIBLE_NAMES
    if _BIBLE_NAMES is None:
        _BIBLE_NAMES = load_bible_names()
    return _BIBLE_NAMES


def convert_expressions(raw: str) -> str:
    """
    Converts LaTeX expressions in the deflated source.

    Parameters
    ----------
    raw  – deflated LaTeX source string

    Returns
    -------
    str  – source with expressions converted
    """
    cfg = Config.get()

    # Replacements - keep the order of these in mind, as some may interact (e.g. szquoted should be replaced before sz)
    replacements = {
        r'{\szquoted}': cfg.szquoted,
        r'{\sz}':       cfg.sz,
        '---':          '&mdash;',
        '--':           '&ndash;',
        r'\ldots':      '&hellip;',
        r'\,':          '&thinsp;',
        r'\thinspace':  '&thinsp;',
        r'\bigskip':    '<br/>',
        r'\medskip':    '<br/>',
        r'\-':          '',
        r'{\euml}':     'ë',
    }
    result = raw
    for old, new in replacements.items():
        result = result.replace(old, new)

    # Quotation marks
    result = _replace_enquote(result)

    # Hiding
    for cmd in (r'\hidefromltoe', r'\idx', r'\ltoetitle', r'\ltoesubtitle', r'\ltoeauthor', r'\ltoeyear'):
        result = _eliminate_cmd(result, cmd)
    result = _replace_cmd(result, r'\onlyforltoe', '', '')

    # cjhebrew: {\larger[n]\cjRL{...}} and \cjRL{...}
    result = convert_cjhebrew(result)

    # %%%L2E variables
    result = re.sub(r'%%%L2E_HEBREW[{]([^}]*)[}]', r'<span class="hebrew">\1</span>', result)
    result = re.sub(r'%%%L2E_GREEK[{]([^}]*)[}]',  r'<span class="greek">\1</span>',  result)

    # Bible translation names
    result = _replace_cmd(result, r'\biblename', '', '')
    result = re.sub(
        r'\\longbiblename[{]([^}]+)[}]',
        lambda m: f'<span class="longversionname">{_bible_names().get(m.group(1), f"UNKNOWN: {m.group(1)}")}</span>',
        result,
    )

    # Delete LaTeX expressions
    _DELETE = (
        r'\begin{document}',
        r'\end{document}',
    )
    for expr in _DELETE:
        result = result.replace(expr, '')

    result = re.sub(r'\\usepackage(?:\[[^\]]*\])?\{[^}]*\}', '', result)
    result = re.sub(r'\\input\{[^}]*\}', '', result)


    if cfg.debug:
        out = cfg.output_directory / "expressions.txt"
        out.write_text(result, encoding="utf-8")
        _logger.info("Expressions output written to: %s", out)

    return result


_BLANK_LINES = re.compile(r'\n[ \t]*\n+')


def build_paragraphs(text: str) -> str:
    """Wrap blank-line-separated blocks in <p>...</p> tags."""
    blocks = _BLANK_LINES.split(text)
    return '\n'.join(f'<p>{b.strip()}</p>' for b in blocks if b.strip())


# Outer quotes: „ ... "   Inner quotes: ‚ ... '
_QUOTES = [('&bdquo;', '&ldquo;'), ('&sbquo;', '&lsquo;')]

_ENQUOTE = r'\enquote{'


def _replace_enquote(text: str, depth: int = 0) -> str:
    """Replace \\enquote{...} with HTML quotation marks, alternating by nesting depth."""
    if _ENQUOTE not in text:
        return text

    open_q, close_q = _QUOTES[depth % 2]
    out = []
    i = 0
    while i < len(text):
        if text[i:i + len(_ENQUOTE)] == _ENQUOTE:
            j = i + len(_ENQUOTE)
            d = 1
            while j < len(text) and d > 0:
                if text[j] == '{':
                    d += 1
                elif text[j] == '}':
                    d -= 1
                j += 1
            inner = _replace_enquote(text[i + len(_ENQUOTE):j - 1], depth + 1)
            out.append(open_q + inner + close_q)
            i = j
        else:
            out.append(text[i])
            i += 1
    return ''.join(out)
