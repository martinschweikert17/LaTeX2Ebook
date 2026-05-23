"""
latex/headings.py – Convert LaTeX heading commands to HTML
==========================================================

Supported commands
------------------
  \\part, \\chapter, \\section, \\subsection, \\subsubsection
  Starred variants (\\chapter*) – numbered  output suppressed, counter not incremented
  Optional short title (\\chapter[short]{long}) – long title is used

Numbering
---------
  Counters are stateful across the document.
  A higher-level heading increments its counter and resets all lower-level counters.
  Style per level is configured via Config.heading_numbering:
    arabic      – 1, 2, 3 …
    roman_upper – I, II, III …
    roman_lower – i, ii, iii …
    alpha_upper – A, B, C …
    alpha_lower – a, b, c …
    none        – no number

Labels
------
  \\label{name} immediately following a heading is consumed here.
  The heading receives id="name" and the label is recorded in _label_map
  so latex/refs.py can resolve \\ref / \\fullref etc.

Pipeline position
-----------------
  latex/formatting.py  →  [latex/headings.py]  →  latex/refs.py
"""

import re

from config import Config, PROGRAM_NAME

import logging
_logger = logging.getLogger(f"{PROGRAM_NAME}.latex.headings")

_HEADING_LEVELS = ('part', 'chapter', 'section', 'subsection', 'subsubsection')

# Levels that form the dotted compound number (part and chapter remain standalone)
_COMPOUND_CHAIN = ('chapter', 'section', 'subsection', 'subsubsection')

_HTML_TAG = {
    'part':          'h1',
    'chapter':       'h2',
    'section':       'h3',
    'subsection':    'h4',
    'subsubsection': 'h5',
}

_ROMAN = [
    (1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
    (100,  'C'), (90,  'XC'), (50,  'L'), (40,  'XL'),
    (10,   'X'), (9,   'IX'), (5,   'V'), (4,   'IV'),
    (1,    'I'),
]


def _to_roman(n: int) -> str:
    result = []
    for value, numeral in _ROMAN:
        while n >= value:
            result.append(numeral)
            n -= value
    return ''.join(result)


_FORMATTERS = {
    'arabic':      lambda n: str(n),
    'roman_upper': lambda n: _to_roman(n),
    'roman_lower': lambda n: _to_roman(n).lower(),
    'alpha_upper': lambda n: chr(ord('A') + n - 1) if n <= 26 else str(n),
    'alpha_lower': lambda n: chr(ord('a') + n - 1) if n <= 26 else str(n),
    'none':        lambda n: '',
}

def _build_number(level: str, counters: dict, styles: dict) -> str:
    """
    Return the formatted number string for the given level.

    - part, chapter: standalone number (e.g. "I", "2")
    - section and below: compound dotted number built from _COMPOUND_CHAIN
      ancestors whose counter > 0 and style != 'none' (e.g. "2.3", "2.3.1")
    """
    if level not in _COMPOUND_CHAIN or level == 'chapter':
        style = styles.get(level, 'arabic')
        if style == 'none':
            return ''
        return _FORMATTERS.get(style, _FORMATTERS['arabic'])(counters[level])

    # section / subsection / subsubsection → dotted compound
    chain_up_to = _COMPOUND_CHAIN[:_COMPOUND_CHAIN.index(level) + 1]
    parts = []
    for ancestor in chain_up_to:
        style = styles.get(ancestor, 'arabic')
        if style == 'none' or counters[ancestor] == 0:
            continue
        parts.append(_FORMATTERS.get(style, _FORMATTERS['arabic'])(counters[ancestor]))
    return '.'.join(parts)


# \paragraph and \minisec are inline mini-headings: no counter, no TOC, but label support.
_MINISEC_LEVELS = frozenset({'paragraph', 'minisec'})

# Matches \appendix or heading commands (\part, \chapter* etc.)
_HEADING_CMD = re.compile(
    r'\\appendix\b'
    r'|'
    r'\\(?P<notoc>notoc)?(?P<level>part|chapter|section|subsection|subsubsection|paragraph|minisec)(?P<starred>\*)?'
    r'\s*(?:\[[^\]]*\])?\s*\{'
)

# \label{name} optionally following a heading (any whitespace between)
_LABEL_AFTER = re.compile(r'\s*\\label\{([^}]+)\}')

# label name → {'num': str, 'title': str, 'tag': str}
# Reset at the start of each convert_headings() call.
_label_map: dict[str, dict[str, str]] = {}

# Ordered list of all headings for TOC generation.
# Each entry: {'level': str, 'num': str, 'title': str, 'id': str}
_toc_entries: list[dict] = []


def get_label_map() -> dict[str, dict[str, str]]:
    """Return the label map built by the most recent convert_headings() call."""
    return _label_map


def get_toc_entries() -> list[dict]:
    """Return the ordered heading list built by the most recent convert_headings() call."""
    return _toc_entries


def convert_headings(text: str) -> str:
    """Replace LaTeX heading commands with numbered HTML headings.

    \\label{name} immediately following a heading is consumed: the heading
    receives id="name" and the label is recorded for cross-reference resolution.
    """
    global _label_map, _toc_entries
    _label_map  = {}
    _toc_entries = []

    cfg               = Config.get()
    styles            = cfg.heading_numbering
    appendices_style  = cfg.appendices_numbering
    counters          = {level: 0 for level in _HEADING_LEVELS}

    out     = []
    i       = 0
    n       = len(text)
    auto_id = 0

    while i < n:
        m = _HEADING_CMD.search(text, i)
        if m is None:
            out.append(text[i:])
            break

        out.append(text[i:m.start()])

        # ── \appendix: switch chapter numbering style and reset counter ──
        if m.group('level') is None:
            styles  = dict(styles)
            styles['chapter'] = appendices_style
            counters['chapter'] = 0
            for sub in _HEADING_LEVELS[_HEADING_LEVELS.index('chapter') + 1:]:
                counters[sub] = 0
            i = m.end()
            continue

        notoc   = m.group('notoc')   is not None
        level   = m.group('level')
        starred = m.group('starred') is not None

        # Brace-count to extract the title (handles nested {…} inside)
        j     = m.end()
        depth = 1
        while j < n and depth > 0:
            if   text[j] == '{': depth += 1
            elif text[j] == '}': depth -= 1
            j += 1
        title = text[m.end():j - 1]

        tag = _HTML_TAG.get(level, 'p')

        # Consume optional \label{name} immediately after the closing }
        lm         = _LABEL_AFTER.match(text, j)
        label_name = lm.group(1) if lm else None
        if lm:
            j = lm.end()

        if label_name:
            hid = label_name
        else:
            auto_id += 1
            hid = f'toc-{auto_id}'
        id_attr = f' id="{hid}"'

        if level in _MINISEC_LEVELS:
            # \paragraph / \minisec: styled paragraph, no counter, no TOC entry
            num = ''
            out.append(f'<p class="minisec"{id_attr}>{title}</p>')
        elif starred or notoc:
            num = ''
            out.append(f'<{tag}{id_attr}>{title}</{tag}>')
            if not notoc:
                _toc_entries.append({'level': level, 'num': '', 'title': title, 'id': hid})
        else:
            level_idx = _HEADING_LEVELS.index(level)
            counters[level] += 1
            for sub in _HEADING_LEVELS[level_idx + 1:]:
                counters[sub] = 0

            num = _build_number(level, counters, styles)

            if num:
                out.append(f'<{tag}{id_attr}>{num} {title}</{tag}>')
            else:
                out.append(f'<{tag}{id_attr}>{title}</{tag}>')

            _toc_entries.append({'level': level, 'num': num, 'title': title, 'id': hid})

        if label_name:
            _label_map[label_name] = {'num': num, 'title': title, 'tag': tag}

        i = j

    return ''.join(out)
