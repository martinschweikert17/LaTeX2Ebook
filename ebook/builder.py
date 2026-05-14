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
from pathlib import Path

from config import Config


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
    # Private methods – DUMMY implementations
    # Replace each method body with real conversion logic.
    # ------------------------------------------------------------------

    def _build_epub(self, html_path: Path, out_path: Path) -> None:
        """
        Packages the HTML file as an EPUB using ebooklib.
        Steps (to be implemented):
          1. Parse HTML into ebooklib EpubBook
          2. Set metadata (title, author, language) from Config
          3. Add stylesheet and cover image if present
          4. Write .epub file via epub.write_epub()
        DUMMY – writes a placeholder text file.
        """
        self._logger.debug("_build_epub: not yet implemented")
        out_path.write_text(
            f"[EPUB placeholder – source: {html_path.name}]", encoding="utf-8"
        )