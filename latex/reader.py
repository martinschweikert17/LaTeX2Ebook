"""
latex/reader.py – Read and deflate a LaTeX source file
=======================================================

Responsibility
--------------
This module reads the LaTeX source file configured via Config,
deflates it by removing irrelevant blocks, strips %%BLOCK comment
lines via decomment(), and returns the result as a plain string.
It is the first step in the conversion pipeline.

Pipeline
--------
  deflate  →  decomment  →  normalize_citations  →  expand_newcommands  →  apply_personal_commands
  →  convert_bibleref  →  convert_expressions  →  apply_formatting
  →  convert_headings  →  process_footnotes  →  process_toc  →  process_refs  →  process_literature
  →  build_paragraphs
  →  html/converter.py  →  ebook/builder.py

Expected inputs
---------------
  Config.get().tex_input  – full path to the .tex file

Produced output
---------------
  str  – deflated LaTeX source

Usage
-----
    from latex.reader import LatexReader

    raw = LatexReader().read()
"""

import logging
import re

from config import Config

_INPUT_FRONTMATTER = re.compile(r'\\input\{frontmatter\}')


def _inline_frontmatter(raw: str) -> str:
    """Replace \\input{frontmatter} with the content of frontmatter_<target>.tex.

    Runs before deflate() so that LANG blocks inside the frontmatter file
    are processed by the normal deflate pipeline.
    """
    if not _INPUT_FRONTMATTER.search(raw):
        return raw
    from config import Config
    cfg = Config.get()
    fm_path = cfg.input_directory / f"frontmatter_{cfg.target.lower()}.tex"
    if not fm_path.exists():
        raise FileNotFoundError(
            f"Frontmatter file not found: {fm_path}\n"
            f"Expected: frontmatter_{cfg.target.lower()}.tex in {cfg.input_directory}"
        )
    content = fm_path.read_text(encoding="utf-8")
    return _INPUT_FRONTMATTER.sub(lambda _: content, raw)
from latex.bib import normalize_citations
from latex.bibleref import convert_bibleref
from latex.decomment import decomment
from latex.deflate import deflate
from latex.expressions import build_paragraphs, convert_expressions
from latex.footnotes import process_footnotes
from latex.formatting import apply_formatting
from latex.headings import convert_headings
from latex.literature import process_literature
from latex.newcommands import expand_newcommands
from latex.refs import process_refs
from latex.toc import process_toc
from latex.personal_settings import apply_personal_commands, build_jhwh_commands


class LatexReader:
    """
    Reads and deflates a LaTeX source file.

    Usage
    -----
        raw = LatexReader().read()
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{Config.get().programname}.latex.reader")

    def read(self) -> str:
        """
        Reads and deflates the .tex file specified in Config.

        Returns
        -------
        str – deflated LaTeX source

        Raises
        ------
        FileNotFoundError – if the configured tex_input does not exist
        """
        cfg  = Config.get()
        path = cfg.tex_input

        self._logger.info("Reading LaTeX source: %s", path)

        if not path.exists():
            raise FileNotFoundError(f"LaTeX source file not found: {path}")

        raw = _inline_frontmatter(path.read_text(encoding="utf-8"))
        raw = deflate(raw)
        raw = decomment(raw)
        raw = normalize_citations(raw)     # biblatex \cite/\footcite → \citetitle
        raw = expand_newcommands(raw)
        raw = apply_personal_commands(raw, build_jhwh_commands())
        raw = convert_bibleref(raw)
        raw = convert_expressions(raw)
        raw = apply_formatting(raw)
        raw = convert_headings(raw)
        raw = process_footnotes(raw)
        raw = process_toc(raw)
        raw = process_refs(raw)
        raw = process_literature(raw)
        raw = build_paragraphs(raw)


        self._logger.info("Done – %d chars", len(raw))
        return raw
