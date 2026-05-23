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

_NEWCMD_START = re.compile(
    r'\\(?:(?:new|renew)command\*?\s*\{(?:\\[A-Za-z]+)?\}|newcolumntype\s*\{[^}]*\})'
    r'\s*(?:\[[^\]]*\])?\s*\{'
)


def _eliminate_newcommand_defs(text: str) -> str:
    """Remove all \\newcommand definitions using brace-counting for the body."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        m = _NEWCMD_START.search(text, i)
        if m is None:
            out.append(text[i:])
            break
        out.append(text[i:m.start()])
        depth = 1
        j = m.end()
        while j < n and depth > 0:
            if text[j] == '{':
                depth += 1
            elif text[j] == '}':
                depth -= 1
            j += 1
        i = j
    return ''.join(out)


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

    # Eliminate \newcommand / \renewcommand definitions before any substitutions run
    # (substitutions would corrupt the command names inside the definitions)
    result = _eliminate_newcommand_defs(raw)

    # cjhebrew must run before the replacements dict so that '--' inside \cjRL{}
    # is decoded as maqqef (U+05BE) and not first mangled into '&ndash;'.
    result = convert_cjhebrew(result)

    # Strip ~ used as spacing glue between layout commands (before individual substitutions)
    result = re.sub(r'(\\(?:bigskip|medskip|newpage|vfill))\s*~\s*', r'\1', result)
    result = re.sub(r'~\s*(\\(?:bigskip|medskip|newpage|vfill))', r'\1', result)

    # Replacements - keep the order of these in mind, as some may interact (e.g. szquoted should be replaced before sz)
    replacements = {
        r'{\szquoted}': cfg.szquoted,
        r'{\sz}':       cfg.sz,
        '---':          '—',   # em dash  —
        '--':           '–',   # en dash  –
        r'\ldots':      '…',   # ellipsis …
        r'\,':          ' ',   # narrow no-break space
        r'\thinspace':  ' ',   # narrow no-break space
        r'\bigskip':    '<br/>',
        r'\medskip':    '<br/>',
        r'\-':          '',
        r'\S':          '§',
        r'{\euml}':     'ë',
        r'{\prozent}':  '%',
        '~':            ' ',   # non-breaking space
    }
    for old, new in replacements.items():
        result = result.replace(old, new)

    # Quotation marks
    result = _replace_enquote(result)

    # Hiding
    for cmd in (r'\hidefromltoe', r'\idx', r'\ltoetitle', r'\ltoesubtitle', r'\ltoeauthor', r'\ltoeyear'):
        result = _eliminate_cmd(result, cmd)
    result = _replace_cmd(result, r'\onlyforltoe', '', '')

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
        r'\backmatter',
        r'\end{addmargin}',
        r'\listoffigures',
        r'\listofsymbols',
        r'\listoftables',
        r'\printindex',
        r'\setdefaultparagraphmode',
        r'\setparagraphsseparated',
        r'\frontmatter',
        r'\mainmatter',
        r'\makecopyright',
        r'\makehalftitle',
        r'\maketitle',
        r'\newpage',
        r'\tableofcontents',
        r'~\vfill',
        r'\vfill',
        r'\begin{center}',
        r'\end{center}',
        r'\phantomsection',
    )
    for expr in _DELETE:
        result = result.replace(expr, '')

    result = re.sub(r'\\usepackage(?:\[[^\]]*\])?\{[^}]*\}', '', result)
    result = re.sub(r'\\input\{[^}]*\}', '', result)
    result = re.sub(r'\\addcontentsline\{[^}]*\}\{[^}]*\}\{[^}]*\}', '', result)
    result = re.sub(r'\\makeindex(?:\{[^}]*\})?', '', result)
    result = re.sub(r'\\setcounter\{[^}]*\}\{[^}]*\}', '', result)
    result = re.sub(r'\\vspace\*?\{[^}]*\}', '', result)
    result = re.sub(r'\\pagestyle\{[^}]*\}', '', result)
    result = re.sub(r'\\(?:widow|club|displaywidow)penalty\s*=\s*\d+', '', result)

    # \num{N} – HTML has no equivalent; output the number as-is
    result = _replace_cmd(result, r'\num', '', '')

    # \url{U} – clickable link
    result = re.sub(r'\\url\{([^}]*)\}', r'<a href="\1">\1</a>', result)


    if cfg.debug:
        out = cfg.output_directory / "expressions.txt"
        out.write_text(result, encoding="utf-8")
        _logger.info("Expressions output written to: %s", out)

    return result


_BLANK_LINES = re.compile(r'\n[ \t]*\n+')
_BLOCK_OPEN  = re.compile(r'^<(?:table|div|ul|ol|dl|blockquote|pre|figure|h[1-6]|p)\b', re.IGNORECASE)


def build_paragraphs(text: str) -> str:
    """Wrap blank-line-separated blocks in <p>...</p> tags (block-level HTML is left unwrapped)."""
    blocks = _BLANK_LINES.split(text)
    result = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        result.append(b if _BLOCK_OPEN.match(b) else f'<p>{b}</p>')
    return '\n'.join(result)


# Outer quotes: „ ... "   Inner quotes: ‚ ... '
_QUOTES = [("„", "“"), ("‚", "‘")]

_ENQUOTE = r'\enquote{'

# Footnote commands whose bodies must be processed at depth=0 (independent context).
# Longest trigger first so \pfootnote is never confused with \footnote.
_FN_TRIGGERS = (r'\pfootnote{', r'\footnote{')


def _replace_enquote(text: str, depth: int = 0) -> str:
    """Replace \\enquote{...} with HTML quotation marks, alternating by nesting depth.

    \\footnote and \\pfootnote bodies are always processed at depth=0 so that
    \\enquote inside a footnote starts fresh with outer quotation marks,
    regardless of the nesting level of the surrounding text.
    """
    if _ENQUOTE not in text:
        return text

    open_q, close_q = _QUOTES[depth % 2]
    out = []
    i = 0
    n = len(text)
    while i < n:
        # Footnote bodies: reset depth to 0 (independent quotation context)
        fn_trig = next((t for t in _FN_TRIGGERS if text[i:i + len(t)] == t), None)
        if fn_trig:
            j = i + len(fn_trig)
            d = 1
            while j < n and d > 0:
                if   text[j] == '{': d += 1
                elif text[j] == '}': d -= 1
                j += 1
            body = _replace_enquote(text[i + len(fn_trig):j - 1], 0)
            out.append(fn_trig + body + '}')
            i = j
        elif text[i:i + len(_ENQUOTE)] == _ENQUOTE:
            j = i + len(_ENQUOTE)
            d = 1
            while j < n and d > 0:
                if   text[j] == '{': d += 1
                elif text[j] == '}': d -= 1
                j += 1
            inner = _replace_enquote(text[i + len(_ENQUOTE):j - 1], depth + 1)
            out.append(open_q + inner + close_q)
            i = j
        else:
            out.append(text[i])
            i += 1
    return ''.join(out)
