"""
ebook/builder.py – Convert an HTML file to the target ebook format
===================================================================

Responsibility
--------------
This module takes the HTML file written by the HTML converter and
produces the final ebook in the format configured via Config
(Target = epub | html).

The HTML file path is read from disk, so this step can also be run
independently if an HTML file already exists from a previous run.

Pipeline position
-----------------
  latex/reader.py  →  html/converter.py  →  [ebook/builder.py]

Expected inputs
---------------
  html_path                          – Path to the .html file on disk
  Config.get().target                – "epub" or "html"
  Config.get().output_directory      – where the ebook file is written

Produced output
---------------
  Path                               – absolute path to the written ebook file

Format notes
------------
  epub  – requires: ebooklib  (pip install ebooklib)
  html  – no additional dependencies

Usage
-----
    from ebook.builder import EbookBuilder

    ebook_path = EbookBuilder().build(html_path)
"""

import logging
import re
import uuid
from pathlib import Path

from ebooklib import epub

from config import Config

_CSS_TEMPLATE = Path(__file__).parent.parent / "data" / "epub.css"

_BODY_RE    = re.compile(r'<body[^>]*>(.*?)</body>', re.DOTALL | re.IGNORECASE)
_LANG_RE    = re.compile(r'<html[^>]*\blang=["\']([^"\']+)["\']', re.IGNORECASE)
_HEADING_RE = re.compile(
    r'<(h[1-6])\b[^>]*\bid=["\']([^"\']+)["\'][^>]*>(.*?)</\1>',
    re.DOTALL | re.IGNORECASE,
)
_STRIP_TAGS = re.compile(r'<[^>]+>')


def _epub_css(cfg: Config) -> str:
    from latex.newcommands import get_fm_value
    fmtitlecss         = get_fm_value('fmtitlecss')         or "font-family: sans-serif; font-size: 1.8em; font-weight: bold; margin-top: 1em; margin-bottom: 0.3em;"
    fmsubtitlecss      = get_fm_value('fmsubtitlecss')      or "font-family: sans-serif; font-size: 1.3em; font-style: italic; margin-top: 0; margin-bottom: 0.8em;"
    fmauthorcss        = get_fm_value('fmauthorcss')        or "font-family: sans-serif; font-size: 1.1em; margin-bottom: 0.3em;"
    fmyearcss          = get_fm_value('fmyearcss')          or "font-family: sans-serif; font-size: 1.0em; color: #555; margin-bottom: 2em;"
    fmcopyrightrulecss  = get_fm_value('fmcopyrightrulecss')  or "border: none; border-top: 1px solid #aaa; margin-top: 2em; margin-bottom: 0.5em;"
    fmcopyrightcss      = get_fm_value('fmcopyrightcss')      or "font-size: 0.85em; color: #555; margin-top: 0;"
    fmtableofcontentcss = get_fm_value('fmtableofcontentcss') or "font-family: sans-serif; font-size: 1.4em; font-weight: bold; line-height: 1.2; margin-top: 1.5em; margin-bottom: 0.5em;"
    return (
        _CSS_TEMPLATE.read_text(encoding="utf-8")
        .replace("{fmtitlecss}",          fmtitlecss)
        .replace("{fmsubtitlecss}",       fmsubtitlecss)
        .replace("{fmauthorcss}",         fmauthorcss)
        .replace("{fmyearcss}",           fmyearcss)
        .replace("{fmcopyrightrulecss}",  fmcopyrightrulecss)
        .replace("{fmcopyrightcss}",        fmcopyrightcss)
        .replace("{fmtableofcontentcss}",  fmtableofcontentcss)
        .replace("{fullreftitle_css}",     cfg.fullref_title)
        .replace("{longversionname_css}", cfg.longversionname)
        .replace("{transliteration_css}", cfg.transliteration)
        .replace("{verseemphasis_css}",   cfg.verse_emphasis)
        .replace("{personname_css}",      cfg.person_name_format)
        .replace("{smallcaps_css}",       cfg.small_caps_format)
        .replace("{greekfontsize}",       cfg.greek_font_size)
        .replace("{hebrewfontsize}",      cfg.hebrew_font_size)
    )


def _parse_html(html_path: Path) -> tuple[str, str]:
    """Return (body_content, lang) extracted from the HTML file."""
    text   = html_path.read_text(encoding="utf-8")
    lang_m = _LANG_RE.search(text)
    lang   = lang_m.group(1) if lang_m else "de"
    body_m = _BODY_RE.search(text)
    body   = body_m.group(1).strip() if body_m else text
    return body, lang


def _build_toc(body: str) -> list:
    """Return a flat list of epub.Link items from headings that carry id attributes."""
    items = []
    for m in _HEADING_RE.finditer(body):
        id_   = m.group(2)
        title = _STRIP_TAGS.sub('', m.group(3)).strip()
        items.append(epub.Link(f"content.xhtml#{id_}", title, id_))
    return items


class EbookBuilder:
    """
    Converts an HTML file into the configured ebook format.

    The target format is read from Config.get().target.

    Usage
    -----
        builder    = EbookBuilder()
        ebook_path = builder.build(html_path)
    """

    # Supported target formats and their file extensions
    FORMATS: dict[str, str] = {
        "epub": ".epub",
        "html": ".html",
    }

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{Config.get().programname}.ebook.builder")

    def build(self, html_path: Path) -> Path:
        """
        Reads the HTML file and writes the ebook to the output directory.

        Parameters
        ----------
        html_path – Path to the .html file produced by HtmlConverter

        Returns
        -------
        Path – absolute path to the written ebook file

        Raises
        ------
        FileNotFoundError – if html_path does not exist
        ValueError        – if the configured target format is unknown
        """
        cfg    = Config.get()
        target = cfg.target.lower()

        if target not in self.FORMATS:
            raise ValueError(
                f"Unknown target format: '{target}'. "
                f"Supported: {list(self.FORMATS)}"
            )

        if not html_path.exists():
            raise FileNotFoundError(f"HTML input file not found: {html_path}")

        # The language suffix (e.g. "_DE") is already part of html_path.stem,
        # so replacing only the extension preserves it:
        #   Ps22.17_DE.html  →  Ps22.17_DE.epub  (or .html)
        suffix   = self.FORMATS[target]
        out_path = cfg.output_directory / html_path.with_suffix(suffix).name

        self._logger.info(
            "Building %s from %s → %s", target.upper(), html_path.name, out_path
        )

        if target == "epub":
            self._build_epub(html_path, out_path)

        self._logger.info("Ebook written: %s", out_path)
        return out_path

    # ------------------------------------------------------------------

    def _build_epub(self, html_path: Path, out_path: Path) -> None:
        from latex.newcommands import get_fm_value, get_meta_value
        from latex.expressions import expand_fm_text

        cfg = Config.get()

        body, lang = _parse_html(html_path)
        # EPUB metadata title is plain text: expand {\sz} etc. and turn \\ into a space
        title     = re.sub(r'\s+', ' ', expand_fm_text(get_fm_value('fmtitle') or cfg.title).replace('<br/>', ' ')).strip()
        author    = get_fm_value('fmauthor')    or cfg.author
        keywords  = get_fm_value('fmkeywords')  or get_meta_value('metakeywords') or cfg.keywords
        publisher = get_fm_value('fmpublisher') or get_fm_value('fmeditor') or 'Selbstverlag'

        # --- Book metadata ---
        book = epub.EpubBook()
        book.set_identifier(str(uuid.uuid4()))
        book.set_title(title)
        book.set_language(lang)
        book.add_author(author)
        book.add_metadata('DC', 'publisher', publisher)
        if cfg.description:
            book.add_metadata('DC', 'description', cfg.description)
        if keywords:
            book.add_metadata('DC', 'subject', keywords)
        cy = cfg.copyright_year or cfg.year
        if cy:
            book.add_metadata('DC', 'date', cy)

        # --- CSS ---
        style = epub.EpubItem(
            uid="epub_css",
            file_name="style/epub.css",
            media_type="text/css",
            content=_epub_css(cfg).encode("utf-8"),
        )
        book.add_item(style)

        # --- Content chapter ---
        chapter = epub.EpubHtml(
            uid="content",
            title=title,
            file_name="content.xhtml",
            lang=lang,
            content=f"<html><body>{body}</body></html>",
        )
        chapter.add_link(href="style/epub.css", rel="stylesheet", type="text/css")
        book.add_item(chapter)

        # --- TOC ---
        toc_links = _build_toc(body)
        book.toc = toc_links or [epub.Link("content.xhtml", title, "main")]

        # --- Navigation documents ---
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # --- Spine ---
        # "nav" is intentionally excluded: including it causes readers to start
        # on the machine-readable TOC page instead of the title page.
        # The NAV document remains in the manifest for EPUB3 compliance.
        book.spine = [chapter]

        epub.write_epub(str(out_path), book)
        self._logger.debug("EPUB written: %s (%d TOC entries)", out_path, len(book.toc))
