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
from latex.newcommands import get_fm_value

_logger = logging.getLogger(f"{PROGRAM_NAME}.latex.expressions")
_BIBLE_NAMES: dict[str, str] | None = None

_FM_BARE = re.compile(r'\\(fm\w+)(?![A-Za-z])(?:\{\})?')

# Canonical "blank line" emitted for \bigskip/\medskip/\smallskip in both the
# \sffamily frontmatter block and normal body text. _VSPACE_BLOCK is wrapped in
# blank lines so build_paragraphs keeps it as its own block.
_VSPACE = '<p class="vspace">&#160;</p>'
_VSPACE_BLOCK = f'\n\n{_VSPACE}\n\n'

_SFFAM_SIZE  = r'(?:\\(?:tiny|scriptsize|footnotesize|small|normalsize|large|Large|LARGE|huge|Huge)\b\s*)*'
_SFFAM_STYLE = r'(?:\\(?:textbf|bfseries|textit|itshape)\b\s*)*'
# One frontmatter item: either a {<size>* <style>* \fmXXX} line (group 1 = key)
# or a vertical-space marker (group 2). \bigskip/\medskip/\smallskip are turned
# into the canonical _VSPACE paragraph by convert_expressions before this runs;
# literal commands and <br/> are matched too as harmless fallbacks.
_SFFAM_ITEM = re.compile(
    r'\{' + _SFFAM_SIZE + _SFFAM_STYLE + _SFFAM_SIZE + r'\\(fm\w+)\s*\}'
    r'(?:\\\\(?:\[[^\]]*\])?|\s*\\par\b)?'
    r'|(<p class="vspace">[^<]*</p>|<br\s*/?>|\\(?:big|med|small)skip\b)',
    re.DOTALL,
)
_SFFAM_FLUSHRIGHT = re.compile(
    r'\\begin\{flushright\}(.*?)\\end\{flushright\}',
    re.DOTALL,
)
_SFFAM_CENTER = re.compile(
    r'\\begin\{center\}(.*?)\\end\{center\}',
    re.DOTALL,
)


def _build_sffamily_html(block: str) -> str:
    """Convert \\sffamily...\\rmfamily block content to semantic HTML.

    Each {<size>* <style>* \\fmXXX} group becomes <p class="fmXXX">value</p>.
    A \\bigskip/\\medskip/\\smallskip becomes one blank line (<p class="vspace">).
    A \\begin{flushright}/\\begin{center} wrapper becomes <div class="flushright">/
    <div class="center">.
    Everything else (\\vfill, \\vspace, \\pagestyle, comments, …) is discarded.
    """
    def _fm_items(content: str) -> list[str]:
        content = re.sub(r'%[^\n]*', '', content)
        parts = []
        for m in _SFFAM_ITEM.finditer(content):
            if m.group(1):                       # \fmXXX line
                val = expand_fm_for_html(m.group(1))
                if val:
                    parts.append(f'<p class="{m.group(1)}">{val}</p>')
            else:                                # vertical-space marker → blank line
                parts.append(_VSPACE)
        return parts

    for env_re, css in ((_SFFAM_FLUSHRIGHT, 'flushright'), (_SFFAM_CENTER, 'center')):
        env = env_re.search(block)
        if env:
            rows = _fm_items(block[:env.start()])
            inner = _fm_items(env.group(1))
            rows_after = _fm_items(block[env.end():])
            if inner:
                rows.append(f'<div class="{css}">')
                rows.extend(inner)
                rows.append('</div>')
            rows.extend(rows_after)
            break
    else:
        rows = _fm_items(block)

    return ('\n'.join(rows) + '\n') if rows else ''



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


_FM_STANDALONE = re.compile(
    r'^\{?'
    r'(?:\\(?:tiny|scriptsize|footnotesize|small|normalsize|large|Large|LARGE|huge|Huge)\b\s*)*'
    r'\\(fm\w+)(?![A-Za-z])(?:\{\})?\}?$'
)


def _expand_standalone_fm(text: str) -> str:
    """Replace standalone \\fmXXX (or {\\fmXXX}) paragraphs with <p class="fmXXX">value</p>.

    A "standalone" paragraph is one whose entire content (after stripping
    whitespace) is a single \\fmXXX command, optionally wrapped in {}.
    Inline \\fmXXX commands mixed with other text are left for _FM_BARE.sub.
    """
    blocks = _BLANK_LINES.split(text)
    out = []
    for block in blocks:
        m = _FM_STANDALONE.fullmatch(block.strip())
        if m:
            val = expand_fm_for_html(m.group(1))
            if val:
                out.append(f'<p class="{m.group(1)}">{val}</p>')
            # empty value: drop the block entirely
        else:
            out.append(block)
    return '\n\n'.join(out)


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
        r'\bigskip':    _VSPACE_BLOCK,
        r'\medskip':    _VSPACE_BLOCK,
        r'\smallskip':  _VSPACE_BLOCK,
        r'\hrule':           '<hr/>',
        r'\newpage\newpage': '<div class="pagebreak"></div>',
        r'\newpage':         '<div class="pagebreak"></div>',
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

    # \sffamily...\rmfamily → semantic HTML before \fmXXX expansion so fm keys are still present
    result = re.sub(
        r'\\sffamily\b(.*?)\\rmfamily\b',
        lambda m: f'<div class="sffamily">\n{_build_sffamily_html(m.group(1))}</div>',
        result, flags=re.DOTALL,
    )
    result = result.replace(r'\sffamily', '').replace(r'\rmfamily', '')

    # Standalone \fmXXX paragraphs → <p class="fmXXX">value</p>  (preserves CSS class)
    result = _expand_standalone_fm(result)

    # Inline {\fmXXX} → plain text (class already applied by _expand_standalone_fm where applicable)
    result = _FM_BRACED.sub(lambda m: expand_fm_for_html(m.group(1)) or m.group(0), result)

    # Inline \fmXXX in body text — full expansion including nested refs and LaTeX subs
    result = _FM_BARE.sub(lambda m: expand_fm_for_html(m.group(1)) or m.group(0), result)

    # \the\year → current year (fallback if \fmyear was not used)
    result = re.sub(r'\\the\\year\b', cfg.copyright_year or cfg.year, result)

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
        r'\tableofcontents',
        r'~\vfill',
        r'\vfill',
        r'\phantomsection',
    )
    for expr in _DELETE:
        result = result.replace(expr, '')
    result = re.sub(r'\\par\b', '', result)

    result = re.sub(r'\\begin\{addmargin\}(?:\[[^\]]*\])?\{[^}]*\}', '', result)
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

    # \LaTeX logo
    result = re.sub(r'\\LaTeX(?:\{\})?', _LATEX_LOGO, result)

    # \url{U} – clickable link
    result = re.sub(r'\\url\{([^}]*)\}', r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>', result)


    if cfg.debug:
        out = cfg.output_directory / "expressions.txt"
        out.write_text(result, encoding="utf-8")
        _logger.info("Expressions output written to: %s", out)

    return result


_BLANK_LINES = re.compile(r'\n[ \t]*\n+')
_BLOCK_OPEN  = re.compile(r'^</?(?:table|div|ul|ol|dl|blockquote|pre|figure|h[1-6]|p|nav|footer|thead|tbody|tfoot|tr|hr)\b', re.IGNORECASE)

_FM_BRACED = re.compile(r'\{\\(fm\w+)\}')

_LATEX_LOGO = '<span class="latex">L<span>a</span>T<span>e</span>X</span>'

_FM_BASIC_SUBS = (
    (r'\copyright', '©'),
    (r'\LaTeX{}',   _LATEX_LOGO),
    (r'\LaTeX',     _LATEX_LOGO),
    ('---',         '—'),
    ('--',          '–'),
    (r'\ldots',     '…'),
    (r'\,',         ' '),
    (r'\thinspace', ' '),
    ('~',           ' '),
)


def _fm_resolver():
    """Return a resolver function that maps fm key → processed value."""
    from config import Config
    cfg = Config.get()

    def resolve(k: str) -> str:
        if k == 'fmyear':
            return cfg.copyright_year or cfg.year
        return get_fm_value(k)

    return resolve


def expand_fm_text(text: str) -> str:
    """Process arbitrary text for HTML: expand \\fmXXX refs and apply basic LaTeX substitutions."""
    if not text:
        return ''
    resolve = _fm_resolver()
    text = _FM_BRACED.sub(lambda m: resolve(m.group(1)) or m.group(0), text)
    # Iterate until stable: an expanded value may itself contain \fmXXX refs
    # (e.g. \fmcopyright expands to a body that contains \fmyear).
    for _ in range(10):
        expanded = _FM_BARE.sub(lambda m: resolve(m.group(1)) or m.group(0), text)
        if expanded == text:
            break
        text = expanded
    # LaTeX line break \\ → HTML line break (must precede \s+ collapse)
    text = re.sub(r'\\\\(?:\[[^\]]*\])?', '<br/>', text)
    # {\sz}/{\szquoted} → configured character (szquoted before sz to avoid partial match)
    cfg = Config.get()
    text = text.replace(r'{\szquoted}', cfg.szquoted)
    text = text.replace(r'{\sz}', cfg.sz)
    for old, new in _FM_BASIC_SUBS:
        text = text.replace(old, new)
    text = re.sub(r'\\[A-Za-z]+\{([^{}]*)\}', r'\1', text)
    text = re.sub(r'\\[A-Za-z]+', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def expand_fm_for_html(key: str) -> str:
    """Return a processed fm value ready for direct HTML insertion."""
    value = _fm_resolver()(key)
    return expand_fm_text(value)


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
