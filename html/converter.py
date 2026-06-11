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
import re
from pathlib import Path

from config import Config
from latex.expressions import expand_fm_for_html, expand_fm_text
from latex.newcommands import get_fm_value, get_meta_value

# Tags whose opening tag alone (without closing tag on same line) widens the indent.
_PRETTY_OPEN  = re.compile(
    r'^<(?:html|head|body|style|nav|div|table|thead|tbody|tfoot|tr|ul|ol|dl)\b[^>]*/?>$',
    re.IGNORECASE,
)
_PRETTY_CLOSE = re.compile(
    r'^</(?:html|head|body|style|nav|div|table|thead|tbody|tfoot|tr|ul|ol|dl)>$',
    re.IGNORECASE,
)


def _pretty_print(html: str) -> str:
    """Indent HTML for readability.

    Works on already-structured HTML where each element is on its own line,
    which is what our pipeline produces.  Does not attempt to re-wrap content.
    """
    lines = html.replace('\r\n', '\n').split('\n')
    out   = []
    depth = 0
    pad   = '  '
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if _PRETTY_CLOSE.match(s):
            depth = max(0, depth - 1)
            out.append(pad * depth + s)
        elif _PRETTY_OPEN.match(s):
            out.append(pad * depth + s)
            depth += 1
        else:
            if s.startswith('<p') and out:
                out.append('')
            out.append(pad * depth + s)
    return '\n'.join(out) + '\n'

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

        html = _pretty_print(self._build_page(raw, lang.lower()))
        out_path.write_text(html, encoding="utf-8")

        self._logger.info("HTML written: %s", out_path)
        return out_path

    def _build_page(self, raw: str, lang: str) -> str:
        cfg  = Config.get()
        viewport_meta    = '<meta name="viewport" content="width=device-width, initial-scale=1.0" />' if cfg.htmlonly else ""
        _desc            = get_meta_value('metadescription') or cfg.description
        _kw              = get_meta_value('metakeywords')    or get_fm_value('fmkeywords') or cfg.keywords
        meta_description = f'<meta name="description" content="{_desc}" />' if _desc else ""
        meta_keywords    = f'<meta name="keywords" content="{_kw}" />'      if _kw   else ""
        reset_css           = "* { box-sizing: border-box; margin: 0; padding: 0; }" if cfg.htmlonly else ""
        body_layout_css     = "max-width: 50em;\n      margin: 2em auto;"            if cfg.htmlonly else ""
        body_background_css = "background-color: #fafafa;"                           if cfg.htmlonly else ""
        th_background_css   = "background-color: #eee;"                              if cfg.htmlonly else ""
        a_hover_css         = "a:hover { color: #005faf; }"                          if cfg.htmlonly else ""
        img_boxshadow_css   = "box-shadow: 0 2px 6px rgba(0,0,0,.3);"               if cfg.htmlonly else ""
        dropcap_css         = ".drop-cap::first-letter { text-shadow: 1px 1px 2px #888; }" if cfg.htmlonly else ""
        tooltip_css         = (
            "a.footnote-ref { position: relative; }\n"
            "    a.footnote-ref::after {\n"
            "      content: attr(data-fn);\n"
            "      position: absolute;\n"
            "      bottom: 1.4rem;\n"
            "      left: 0;\n"
            "      background: #333;\n"
            "      color: #fff;\n"
            "      padding: 0.5rem 0.7rem;\n"
            "      border-radius: 4px;\n"
            "      white-space: normal;\n"
            "      width: 320px;\n"
            "      display: none;\n"
            "      font-size: 0.85rem;\n"
            "      font-weight: normal;\n"
            "      line-height: 1.4;\n"
            "      vertical-align: baseline;\n"
            "      z-index: 100;\n"
            "    }\n"
            "    a.footnote-ref:hover::after { display: block; }"
        ) if cfg.htmlonly else ""
        fmtitlecss         = get_fm_value('fmtitlecss')         or "font-family: sans-serif; font-size: 1.8em; font-weight: bold; margin-top: 1em; margin-bottom: 0.3em;"
        fmsubtitlecss      = get_fm_value('fmsubtitlecss')      or "font-family: sans-serif; font-size: 1.3em; font-style: italic; margin-top: 0; margin-bottom: 0.8em;"
        fmauthorcss        = get_fm_value('fmauthorcss')        or "font-family: sans-serif; font-size: 1.1em; margin-bottom: 0.3em;"
        fmyearcss          = get_fm_value('fmyearcss')          or "font-family: sans-serif; font-size: 1.0em; color: #555; margin-bottom: 2em;"
        fmcopyrightrulecss    = get_fm_value('fmcopyrightrulecss')    or "border: none; border-top: 1px solid #aaa; margin-top: 2em; margin-bottom: 0.5em;"
        fmcopyrightcss        = get_fm_value('fmcopyrightcss')        or "font-size: 0.85em; color: #555; margin-top: 0;"
        fmtableofcontentcss   = get_fm_value('fmtableofcontentcss')   or "font-family: sans-serif; font-size: 1.4em; font-weight: bold; line-height: 1.2; margin-top: 1.5em; margin-bottom: 0.5em;"
        fullreftitle_css    = cfg.fullref_title
        longversionname_css = cfg.longversionname
        transliteration_css = cfg.transliteration
        verseemphasis_css   = cfg.verse_emphasis
        personname_css      = cfg.person_name_format
        smallcaps_css       = cfg.small_caps_format

        fmfooter_raw = get_fm_value('fmfooter') if cfg.htmlonly else ''
        if fmfooter_raw:
            footer_parts = ['<footer>', '<hr class="footer-rule"/>']
            for item in fmfooter_raw.split('\\\\'):
                item = item.strip()
                if not item:
                    continue
                m = re.fullmatch(r'\\(fm\w+)', item)
                val = expand_fm_for_html(m.group(1)) if m else expand_fm_text(item)
                if val:
                    footer_parts.append(f'<p class="footer-text">{val}</p>')
            footer_parts.append('</footer>')
            footer = '\n'.join(footer_parts)
        else:
            footer = ''

        # <title> is plain text: expand {\sz} etc. and turn the \\ line break into a space
        title_text = re.sub(r'\s+', ' ', expand_fm_text(get_fm_value('fmtitle') or cfg.title).replace('<br/>', ' ')).strip()

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
                .replace("{title}",               title_text)
                .replace("{author}",              get_fm_value('fmauthor') or cfg.author)
                .replace("{fmtitlecss}",          fmtitlecss)
                .replace("{fmsubtitlecss}",       fmsubtitlecss)
                .replace("{fmauthorcss}",         fmauthorcss)
                .replace("{fmyearcss}",           fmyearcss)
                .replace("{fmcopyrightrulecss}",  fmcopyrightrulecss)
                .replace("{fmcopyrightcss}",        fmcopyrightcss)
                .replace("{fmtableofcontentcss}",  fmtableofcontentcss)
                .replace("{fullreftitle_css}",     fullreftitle_css)
                .replace("{longversionname_css}", longversionname_css)
                .replace("{transliteration_css}", transliteration_css)
                .replace("{verseemphasis_css}",   verseemphasis_css)
                .replace("{personname_css}",      personname_css)
                .replace("{smallcaps_css}",       smallcaps_css)
                .replace("{greekfontsize}",       cfg.greek_font_size)
                .replace("{hebrewfontsize}",      cfg.hebrew_font_size)
                .replace("{tooltip_css}",         tooltip_css)
                .replace("{body}",                raw)
                .replace("{footer}",             footer))

