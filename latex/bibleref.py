"""
latex/bibleref.py – Convert bibleref package expressions to HTML
================================================================

Responsibility
--------------
Replaces LaTeX bibleref commands with plain-text equivalents.

Supported commands
------------------
  \\bibleverse{book}[(ch:vs)]     – book [+ chapter [+ verse]]
  \\ibibleverse{book}[(ch:vs)]    – same (i = also adds LaTeX index entry)
  \\biblechvs{book}[(ch:vs)]      – chapter[:verse] only, no book name
  \\ibiblechvs{book}[(ch:vs)]     – same
  \\biblevs{book}[(ch:vs)]        – verse(s) only
  \\ibiblevs{book}[(ch:vs)]       – same
  \\iibibleverse{book}[(ch:vs)]   – index only; eliminated without output

Book name sets
--------------
  Reihenfolge: CLI > INI > \\biblerefstyle{} im Quelltext > Default (LThK).
  Ebenso für \\biblerefformat{}: CLI > INI > Quelltext > Default (kurz).
  Available sets: LThK, Lutherbibel, Einheitsuebersetzung, jerusalem.

Chapter/verse separator
-----------------------
  DE → ","   EN → ":"

Pipeline position
-----------------
  latex/decomment.py  →  [latex/bibleref.py]  →  latex/expressions.py
"""

import csv
import logging
import re
from pathlib import Path

from config import Config, PROGRAM_NAME

_logger = logging.getLogger(f"{PROGRAM_NAME}.latex.bibleref")

_CSV_PATH = Path(__file__).parent.parent / "data" / "bibleref.csv"

_STYLE_CMD   = re.compile(r'\\biblerefstyle\{([^}]+)\}')
_FORMAT_CMD  = re.compile(r'\\biblerefformat\{([^}]*)\}')
_IIBIBLE     = re.compile(r'\\iibibleverse\{[^}]+\}(?:\([^)]*\))?')
_CMD       = re.compile(
    r'\\(i?)(bibleverse|biblechvs|biblevs)\{([^}]+)\}(?:\(([^)]*)\))?'
)


def _load_names() -> dict[tuple[str, str], tuple[str, str]]:
    """Return {(abbrev, set_lower): (short_name, long_name)} from bibleref.csv."""
    names: dict[tuple[str, str], tuple[str, str]] = {}
    with open(_CSV_PATH, encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if len(row) < 4:
                continue
            abbrev, set_name, short, long_ = (c.strip() for c in row[:4])
            names[(abbrev, set_name.lower())] = (short, long_)
    return names


def convert_bibleref(text: str) -> str:
    """Replace bibleref commands with their text equivalents."""
    cfg   = Config.get()
    names = _load_names()

    # Determine and remove \biblerefstyle{N}  (CLI > INI > source > default)
    styles = _STYLE_CMD.findall(text)
    if len(styles) > 1:
        raise ValueError(
            f"\\biblerefstyle appears {len(styles)} times – expected at most once"
        )
    if cfg.cli_has("biblerefstyle") or cfg.ini_has("biblerefstyle"):
        style = cfg.biblerefstyle          # CLI or INI wins
    else:
        style = styles[0] if styles else cfg.biblerefstyle   # source, then default
    text  = _STYLE_CMD.sub("", text)

    # Determine and remove \biblerefformat{FORMAT}  (CLI > INI > source > default)
    formats = _FORMAT_CMD.findall(text)
    if len(formats) > 1:
        raise ValueError(
            f"\\biblerefformat appears {len(formats)} times – expected at most once"
        )
    if cfg.cli_has("biblerefformat") or cfg.ini_has("biblerefformat"):
        fmt = cfg.biblerefformat.lower()   # CLI or INI wins
    else:
        fmt = formats[0].strip().lower() if formats else cfg.biblerefformat.lower()  # source, then default
    use_long_default = fmt in ("lang", "long")
    text = _FORMAT_CMD.sub("", text)

    # Eliminate \iibibleverse (index-only, no visible output)
    text = _IIBIBLE.sub("", text)

    sep = "," if cfg.language.upper() == "DE" else ":"

    def replace(m: re.Match) -> str:
        cmd      = m.group(2)           # bibleverse | biblechvs | biblevs
        abbrev   = m.group(3).strip()
        ref      = m.group(4)           # content inside (...), or None

        key = (abbrev, style.strip().lower())
        if key not in names:
            _logger.warning(
                "Unknown bibleref abbreviation '%s' (style '%s') in: %s",
                abbrev, style, m.group(0),
            )
            short, long_ = abbrev, abbrev
        else:
            short, long_ = names[key]

        book_name = long_ if use_long_default else short

        # Parse chapter and verse from ref
        if ref is None:
            chapter, verse = "", ""
        elif ":" in ref:
            chapter, verse = ref.split(":", 1)
        else:
            chapter, verse = ref, ""

        if cmd == "bibleverse":
            if not chapter and not verse:
                return book_name
            if not verse:
                return f"{book_name} {chapter}"
            return f"{book_name} {chapter}{sep}{verse}"

        if cmd == "biblechvs":
            if not chapter and not verse:
                return ""
            if not verse:
                return chapter
            return f"{chapter}{sep}{verse}"

        # biblevs – verse only
        return verse

    return _CMD.sub(replace, text)