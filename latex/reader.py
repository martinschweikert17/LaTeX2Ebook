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
  deflate  →  decomment  →  expand_newcommands  →  apply_personal_commands
  →  convert_bibleref  →  convert_expressions  →  apply_formatting
  →  convert_headings  →  process_footnotes  →  process_refs  →  build_paragraphs
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

from config import Config
from latex.bibleref import convert_bibleref
from latex.decomment import decomment
from latex.deflate import deflate
from latex.expressions import build_paragraphs, convert_expressions
from latex.footnotes import process_footnotes
from latex.formatting import apply_formatting
from latex.headings import convert_headings
from latex.newcommands import expand_newcommands
from latex.refs import process_refs
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

        raw = deflate(path.read_text(encoding="utf-8"))
        raw = decomment(raw)
        raw = expand_newcommands(raw)
        raw = apply_personal_commands(raw, build_jhwh_commands())
        raw = convert_bibleref(raw)
        raw = convert_expressions(raw)
        raw = apply_formatting(raw)
        raw = convert_headings(raw)
        raw = process_footnotes(raw)
        raw = process_refs(raw)
        raw = build_paragraphs(raw)


        self._logger.info("Done – %d chars", len(raw))
        return raw
