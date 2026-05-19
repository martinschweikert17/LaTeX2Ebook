"""
main.py – Entry point for tex2ebook
=====================================
Converts a LaTeX file into an ebook (EPUB or HTML).

Pipeline
--------
  .tex file  →  LatexReader  →  HtmlConverter  →  EbookBuilder  →  ebook file
                                    (writes .html to disk)

Usage
-----
  python main.py --config ps22_17.ini
  python main.py --config ps22_17.ini --target epub
  python main.py --config ps22_17.ini --log-level DEBUG --debug
  python main.py --config ps22_17.ini --output-directory /tmp/out
"""

import argparse
import configparser
import logging
import sys
from pathlib import Path

from config import Config
from latex.reader import LatexReader
from html.converter import HtmlConverter
from ebook.builder import EbookBuilder


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    """Configures logging from Config. Called after Config.initialize()."""
    cfg      = Config.get()
    level    = logging.DEBUG if cfg.debug else getattr(logging, cfg.log_level, logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if cfg.log_file:
        Path(cfg.log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(cfg.log_file, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)-8s] %(name)s – %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )
    return logging.getLogger(cfg.programname)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a LaTeX file to an ebook.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Required
    parser.add_argument(
        "--config",
        required=True,
        metavar="INI_FILE",
        help="Path to the INI configuration file",
    )

    # Optional – override INI values
    parser.add_argument(
        "--input-directory",
        metavar="DIR",
        dest="input_directory",
        help="Directory containing the LaTeX source file",
    )
    parser.add_argument(
        "--input-file",
        metavar="FILE",
        dest="input_file",
        help="LaTeX source filename (relative to input-directory)",
    )
    parser.add_argument(
        "--output-directory",
        metavar="DIR",
        dest="output_directory",
        help="Output directory (default: <input-directory>/L2E)",
    )
    parser.add_argument(
        "--target",
        choices=["epub", "html"],
        help="Target format: epub, html",
    )
    parser.add_argument(
        "--language",
        metavar="LANG",
        help="Document language, e.g. DE or EN",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=None,
        help="Enable debug mode",
    )
    parser.add_argument(
        "--biblerefstyle",
        metavar="STYLE",
        dest="biblerefstyle",
        help="Bible reference style: LThK, Lutherbibel, Einheitsuebersetzung, jerusalem (case-insensitive)",
    )
    parser.add_argument(
        "--biblerefformat",
        metavar="FORMAT",
        dest="biblerefformat",
        help="Bible reference format: kurz/short (short name) or lang/long (full name) (case-insensitive)",
    )

    return parser


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

class Application:
    """
    Orchestrates the conversion pipeline:
      LatexReader → HtmlConverter → EbookBuilder
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(Config.get().programname)

    def run(self) -> int:
        cfg = Config.get()
        self._logger.info("=== %s starting ===", cfg.programname)

        self._logger.debug("Active configuration: %s", cfg)

        # Step 1 – Read and deflate LaTeX source
        raw = LatexReader().read()

        # Step 2 – Convert to HTML → write .html file to output_directory
        html_path = HtmlConverter().convert(raw)

        if cfg.htmlonly:
            self._logger.info("Done. Output: %s", html_path)
            return 0

        # Step 3 – Build ebook from .html file → write ebook to output_directory
        ebook_path = EbookBuilder().build(html_path)

        self._logger.info("Done. Output: %s", ebook_path)
        return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = build_parser()
    args   = parser.parse_args()

    try:
        Config.initialize(args, Path(args.config))
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except (ValueError, configparser.Error) as exc:
        print(f"ERROR reading configuration: {exc}", file=sys.stderr)
        return 1

    logger = setup_logging()

    try:
        return Application().run()
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1
    except ValueError as exc:
        logger.error("%s", exc)
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        return 0
    except Exception:
        logger.exception("Unexpected error:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
