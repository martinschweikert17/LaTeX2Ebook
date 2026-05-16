"""
html/converter.py – Convert a deflated LaTeX string to an HTML file on disk
============================================================================

Responsibility
--------------
This module takes the deflated LaTeX source from the reader and produces
a well-formed HTML file. The HTML file is written to the output
directory and then passed on to the ebook builder as a file path.

HTML serves as the persistent intermediate format between the LaTeX
reader and the ebook builder. It is written to disk so that the
conversion result can be inspected, reused, or post-processed
independently.

Pipeline position
-----------------
  latex/reader.py  →  [html/converter.py]  →  ebook/builder.py

Expected inputs
---------------
  str                                 – deflated LaTeX source from LatexReader
  Config.get().output_directory       – where the .html file is written
  Config.get().language               – used for the <html lang="..."> attribute

Produced output
---------------
  Path                                – absolute path to the written .html file

Usage
-----
    from latex.reader import LatexReader
    from html.converter import HtmlConverter

    raw       = LatexReader().read()
    html_path = HtmlConverter().convert(raw)
"""

import logging
from pathlib import Path

from config import Config

_TEMPLATE = Path(__file__).parent.parent / "templates" / "html.template"


class HtmlConverter:
    """
    Converts a deflated LaTeX string into an HTML file written to disk.

    Usage
    -----
        html_path = HtmlConverter().convert(raw)
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{Config.get().programname}.html.converter")

    def convert(self, raw: str) -> Path:
        """
        Converts a deflated LaTeX string and writes the result as an .html file.

        Parameters
        ----------
        raw  – deflated LaTeX source from LatexReader

        Returns
        -------
        Path – absolute path to the written HTML file

        Raises
        ------
        OSError – if the output directory cannot be created
        """
        cfg      = Config.get()
        out_dir  = cfg.output_directory
        out_dir.mkdir(parents=True, exist_ok=True)

        stem     = cfg.tex_input.stem
        lang     = cfg.language
        suffix   = f"_{lang}" if lang else ""
        out_path = out_dir / f"{stem}{suffix}.html"

        self._logger.info("Converting to HTML: %s", out_path)

        html = self._build_page(raw, lang.lower())
        out_path.write_text(html, encoding="utf-8")

        self._logger.info("HTML written: %s", out_path)
        return out_path

    def _build_page(self, raw: str, lang: str) -> str:
        cfg  = Config.get()
        viewport_meta    = '<meta name="viewport" content="width=device-width, initial-scale=1.0" />' if cfg.htmlonly else ""
        meta_description = (f'<meta name="description" content="{cfg.description}" />'
                            if cfg.description else "")
        meta_keywords    = (f'<meta name="keywords" content="{cfg.keywords}" />'
                            if cfg.keywords else "")
        reset_css           = "* { box-sizing: border-box; margin: 0; padding: 0; }" if cfg.htmlonly else ""
        body_layout_css     = "max-width: 50em;\n      margin: 2em auto;"            if cfg.htmlonly else ""
        body_background_css = "background-color: #fafafa;"                           if cfg.htmlonly else ""
        th_background_css   = "background-color: #eee;"                              if cfg.htmlonly else ""
        a_hover_css         = "a:hover { color: #005faf; }"                          if cfg.htmlonly else ""
        img_boxshadow_css   = "box-shadow: 0 2px 6px rgba(0,0,0,.3);"               if cfg.htmlonly else ""
        dropcap_css         = ".drop-cap::first-letter { text-shadow: 1px 1px 2px #888; }" if cfg.htmlonly else ""
        ebook_title    = f'<p class="ebook-title">{cfg.title}</p>'       if cfg.htmlonly and cfg.title    else ""
        ebook_subtitle = f'<p class="ebook-subtitle">{cfg.subtitle}</p>' if cfg.htmlonly and cfg.subtitle else ""
        ebook_author   = f'<p class="ebook-author">{cfg.author}</p>'     if cfg.htmlonly and cfg.author   else ""
        copyright_text  = f"© {cfg.year} by {cfg.author}"
        copyright_block = (
            f'<hr class="ebook-copyright-rule" />\n'
            f'<p class="ebook-copyright">{copyright_text}</p>'
            if cfg.htmlonly else ""
        )
        longversionname_css = cfg.longversionname
        transliteration_css = cfg.transliteration
        verseemphasis_css   = cfg.verse_emphasis

        template = _TEMPLATE.read_text(encoding="utf-8")
        return (template
                .replace("{viewport_meta}",       viewport_meta)
                .replace("{meta_description}",    meta_description)
                .replace("{meta_keywords}",       meta_keywords)
                .replace("{reset_css}",           reset_css)
                .replace("{body_layout_css}",     body_layout_css)
                .replace("{body_background_css}", body_background_css)
                .replace("{th_background_css}",   th_background_css)
                .replace("{a_hover_css}",         a_hover_css)
                .replace("{img_boxshadow_css}",   img_boxshadow_css)
                .replace("{dropcap_css}",         dropcap_css)
                .replace("{programname}",         cfg.programname)
                .replace("{lang}",                lang)
                .replace("{title}",               cfg.title)
                .replace("{author}",              cfg.author)
                .replace("{ebook_title}",         ebook_title)
                .replace("{ebook_subtitle}",      ebook_subtitle)
                .replace("{ebook_author}",        ebook_author)
                .replace("{copyright_block}",     copyright_block)
                .replace("{longversionname_css}", longversionname_css)
                .replace("{transliteration_css}", transliteration_css)
                .replace("{verseemphasis_css}",   verseemphasis_css)
                .replace("{greekfontsize}",       cfg.greek_font_size)
                .replace("{hebrewfontsize}",      cfg.hebrew_font_size)
                .replace("{body}",                raw))

