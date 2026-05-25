"""
latex/literature.py – Process \\citetitle commands and build literature list
============================================================================

Responsibility
--------------
Scans the processed text for \\citetitle{key} commands, replaces each with
a clickable link to its entry in the literature section, and builds the
bibliography HTML from the configured .bib file.

  \\citetitle{KEY}  →  <a class="citetitle" href="#lit-KEY">Title</a>

If citations were found, the %%%L2E_LITERATURE placeholder in the
%%%L2E_LITERATURE_SECTION_BEGIN … %%%L2E_LITERATURE_SECTION_END block is
replaced with the formatted bibliography.  If no citations were found, the
entire section is eliminated.

Pipeline position
-----------------
  latex/refs.py  →  [latex/literature.py]  →  latex/expressions.build_paragraphs
"""

import re
import logging

from config import Config, PROGRAM_NAME
from latex.bib import (
    CITETITLE_RE as _CITETITLE,
    _latex_to_text,
    _load_bib,
    _short_title,
    get_bib,
)

_logger = logging.getLogger(f"{PROGRAM_NAME}.latex.literature")

# ── Section / placeholder markers ─────────────────────────────────────────────

_LIT_SECTION = re.compile(
    r'^%%%L2E_LITERATURE_SECTION_BEGIN[^\n]*\n(.*?)^%%%L2E_LITERATURE_SECTION_END[^\n]*\n?',
    re.MULTILINE | re.DOTALL,
)
_LIT_PLACEHOLDER = '%%%L2E_LITERATURE'


# ── Name handling ──────────────────────────────────────────────────────────────

def _split_persons(field: str) -> list[str]:
    """Split a BibTeX author/editor string on ' and ' / ' und '."""
    et_al = ''
    cleaned = field.rstrip()
    if re.search(r'\bet\s+al\.?\s*$', cleaned, re.IGNORECASE):
        cleaned = re.sub(r'\s*\bet\s+al\.?\s*$', '', cleaned, flags=re.IGNORECASE)
        et_al   = 'et al.'
    parts  = re.split(r'\s+(?:and|und)\s+', cleaned, flags=re.IGNORECASE)
    result = [_latex_to_text(p.strip()) for p in parts if p.strip()]
    if et_al:
        result.append(et_al)
    return result


def _normalize_name(name: str) -> str:
    """Ensure 'Firstname Lastname' → 'Lastname, Firstname'; leave 'Last, First' unchanged."""
    if not name or name == 'et al.' or ',' in name:
        return name
    # Reverse word order: last word becomes last name
    idx = name.rfind(' ')
    if idx > 0:
        return f'{name[idx + 1:]}, {name[:idx]}'
    return name


def _format_authors_editors(entry: dict) -> str:
    """Build the bold author/editor string for display."""
    author = entry.get('author', '')
    editor = entry.get('editor', '')

    if author:
        persons    = _split_persons(author)
        author_str = '/'.join(_normalize_name(p) for p in persons)
    else:
        author_str = ''

    if editor:
        persons    = _split_persons(editor)
        editor_str = '/'.join(_normalize_name(p) for p in persons) + ' (Hrsg.)'
    else:
        editor_str = ''

    if author_str and editor_str:
        return f'{author_str}; {editor_str}'
    return author_str or editor_str or entry.get('_key', '?')


def _sort_key(entry: dict) -> str:
    """First author/editor last name, lower-cased, for alphabetical sorting."""
    field = entry.get('author', '') or entry.get('editor', '') or entry.get('title', '')
    if not field:
        return 'zzz'
    first = re.split(r'\s+(?:and|und)\s+', field, flags=re.IGNORECASE, maxsplit=1)[0].strip()
    first = _latex_to_text(first)
    first = _normalize_name(first)
    if ',' in first:
        return first.split(',', 1)[0].strip().lower()
    return first.lower()


# ── Edition normalisation ──────────────────────────────────────────────────────

def _first_author_lastname(entry: dict) -> str:
    """Return the last name of the first author or editor."""
    field = entry.get('author', '') or entry.get('editor', '')
    if not field:
        return ''
    first = re.split(r'\s+(?:and|und)\s+', field, flags=re.IGNORECASE, maxsplit=1)[0].strip()
    first = _latex_to_text(first)
    name  = _normalize_name(first)
    if ',' in name:
        return name.split(',', 1)[0].strip()
    return name


def _format_edition(raw: str) -> str:
    return _latex_to_text(raw).strip()


# ── Entry formatters ───────────────────────────────────────────────────────────

def _append_url(content: str, url: str, urldate: str) -> str:
    """Append URL (and optional access date) to content string."""
    url = url.replace(r'\&', '&').replace(r'\-', '').strip()
    if not url:
        return content
    href    = url.replace('&', '&amp;')
    display = url.replace('&', '&amp;')
    link    = f'<a href="{href}" target="_blank" rel="noopener noreferrer">{display}</a>'
    sep     = ' ' if re.search(r'[\d.!?)]$', content) else '. '
    result  = content + sep + link
    if urldate:
        result += f' – Zugriff am {urldate}'
    return result


def _format_book(key: str, entry: dict) -> str:
    author_block = _format_authors_editors(entry)
    title        = _latex_to_text(entry.get('title',     ''))
    volume_raw   = _latex_to_text(entry.get('volume',    ''))
    series       = _latex_to_text(entry.get('series',    ''))
    address      = _latex_to_text(entry.get('address',   ''))
    publisher    = _latex_to_text(entry.get('publisher', ''))
    year         = _latex_to_text(entry.get('year',      ''))
    isbn         = _latex_to_text(entry.get('isbn',      ''))
    note         = _latex_to_text(entry.get('note',      ''))
    edition_str  = _format_edition(entry.get('edition', ''))
    url          = entry.get('url',     '').strip()
    urldate      = entry.get('urldate', '').strip()

    # ISBN: replace hyphens with en-dashes
    if isbn:
        isbn = isbn.replace('-', '–')

    segments: list[str] = []

    if title:
        segments.append(title)

    # Volume / series block
    merge_vol_with_loc = False
    vol_for_merge      = ''

    if volume_raw or series:
        vol_block = f'Band {volume_raw}' if volume_raw else ''
        combined  = f'{vol_block}, {series}' if (vol_block and series) else (vol_block or series)

        if edition_str:
            if series:
                # Edition as its own sentence after the series block
                segments.append(combined)
                segments.append(edition_str)
                edition_str = ''
            else:
                # No series → edition appended to volume with comma
                segments.append(f'{combined}, {edition_str}')
                edition_str = ''
        else:
            if series:
                segments.append(combined)
            else:
                # Volume without series and without edition: merge with loc block
                merge_vol_with_loc = True
                vol_for_merge      = combined

    if edition_str:
        segments.append(edition_str)

    # Location block
    loc_parts: list[str] = []
    if address and publisher and year:
        loc_parts.append(f'{address}: {publisher}, {year}')
    elif publisher and year:
        loc_parts.append(f'{publisher}, {year}')
    elif year:
        loc_parts.append(year)
    elif address and publisher:
        loc_parts.append(f'{address}: {publisher}')

    if isbn:
        if loc_parts:
            loc_parts[-1] += f', ISBN {isbn}'
        else:
            loc_parts.append(f'ISBN {isbn}')
    if note:
        if loc_parts:
            loc_parts[-1] += f', {note}'
        else:
            loc_parts.append(note)

    if loc_parts:
        loc = loc_parts[0]
        if merge_vol_with_loc:
            segments.append(f'{vol_for_merge}, {loc}')
        else:
            segments.append(loc)
    elif merge_vol_with_loc:
        segments.append(vol_for_merge)

    content = '. '.join(segments)
    content = _append_url(content, url, urldate)

    return f'<p class="literature-entry" id="lit-{key}"><strong>{author_block}</strong>: {content}</p>'


def _format_article(key: str, entry: dict) -> str:
    author_block = _format_authors_editors(entry)
    title        = _latex_to_text(entry.get('title',   ''))
    journal      = _latex_to_text(entry.get('journal', ''))
    year         = _latex_to_text(entry.get('year',    ''))
    volume       = _latex_to_text(str(entry.get('volume', '')))
    number       = _latex_to_text(entry.get('number', ''))
    pages        = _latex_to_text(entry.get('pages',  '')).replace('-', '–')
    url          = entry.get('url',     '').strip()
    urldate      = entry.get('urldate', '').strip()

    j_parts: list[str] = []
    if journal:
        j_parts.append(journal)
    if volume:
        j_parts.append(f'{volume} {year}' if year else volume)
    elif year:
        j_parts.append(year)
    if number:
        j_parts.append(f'Nr. {number}')
    if pages:
        j_parts.append(pages)

    journal_part = ', '.join(j_parts)

    # No extra period after title ending in '?' or '!'
    if title and (title.endswith('?') or title.endswith('!')):
        content = f'{title} {journal_part}' if journal_part else title
    else:
        content = f'{title}. {journal_part}' if journal_part else title

    content = _append_url(content, url, urldate)

    return f'<p class="literature-entry" id="lit-{key}"><strong>{author_block}</strong>: {content}</p>'


def _format_entry(key: str, entry: dict) -> str:
    if entry.get('_type') == 'article':
        return _format_article(key, entry)
    return _format_book(key, entry)


# ── Public API ────────────────────────────────────────────────────────────────

def process_literature(text: str) -> str:
    """Replace \\citetitle{} commands and build the literature section."""
    cfg = Config.get()
    bib = get_bib()

    if not bib and cfg.bib_file:
        _logger.warning("No bib entries loaded from: %s", cfg.bib_file)

    cited_keys: list[str] = []
    seen:       set[str]  = set()

    def _replace_cite(m: re.Match) -> str:
        locator = m.group(1)   # None when no [...]
        key     = m.group(2)
        if key not in seen:
            seen.add(key)
            cited_keys.append(key)
        if key not in bib:
            _logger.warning("Unknown bib key in \\citetitle{%s}", key)
            if locator:
                return f'[?{key}, {_latex_to_text(locator)}]'
            return f'[?{key}]'
        entry = bib[key]
        if locator:
            lastname = _first_author_lastname(entry)
            short    = _short_title(entry)
            ref      = f'{lastname}: {short}' if lastname else short
            loc      = _latex_to_text(locator).strip()
            link     = f'<a class="citetitle" href="#lit-{key}">{ref}</a>'
            return f'{link}, {loc}'
        else:
            title = _short_title(entry) or key
            return f'<a class="citetitle" href="#lit-{key}">{title}</a>'

    text = _CITETITLE.sub(_replace_cite, text)

    if cited_keys:
        entries = [(k, bib[k]) for k in cited_keys if k in bib]
        entries.sort(key=lambda x: _sort_key(x[1]))
        lit_html = '\n'.join(_format_entry(k, e) for k, e in entries)
        text = _LIT_SECTION.sub(
            lambda m: m.group(1).replace(_LIT_PLACEHOLDER, lit_html),
            text,
        )
    else:
        text = _LIT_SECTION.sub('', text)

    return text
