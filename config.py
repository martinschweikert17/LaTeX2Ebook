"""
config.py – Singleton configuration class
==========================================

CONCEPT
-------
Config is a singleton: exactly one instance exists at runtime.
It is created once in main() and is then directly accessible throughout
the program – without being passed as a parameter.

LIFECYCLE
---------
1. Initialization (once, in main.py):

       Config.initialize(args, Path(args.config))

2. Access (anywhere in the program):

       from config import Config
       path = Config.get().tex_input

3. Protection against double initialization:

       Config.initialize(...)   # second call → RuntimeError

4. Protection against access before initialization:

       Config.get()             # before initialize() → RuntimeError

CONFIGURATION PRIORITY (low → high)
-------------------------------------
  1. Hard-coded default values     (_set_defaults)
  2. INI file                      (--config <file>)
  3. Command-line parameters       (all flags except --config)

USAGE IN OTHER CLASSES
----------------------
    from config import Config

    class LatexReader:
        def read(self):
            cfg = Config.get()
            print(cfg.tex_input)

TESTS
-----
    Config._reset()
    Config.initialize(mock_args, mock_ini)
"""

import argparse
import configparser
from datetime import date
from pathlib import Path

PROGRAM_NAME = "latex2ebook"


class Config:
    """
    Singleton configuration class for latex2ebook.

    Public class methods
    --------------------
    Config.initialize(args, ini_path)  – creates the single instance
    Config.get()                       – returns the instance

    All configuration values are accessible via @property getters.
    There are no setters – the instance is immutable after initialize().
    """

    # ------------------------------------------------------------------
    # Singleton mechanism
    # ------------------------------------------------------------------

    _instance: "Config | None" = None

    def __init__(self) -> None:
        self._data: dict = {}

    @classmethod
    def initialize(cls, args: argparse.Namespace, ini_path: Path) -> "Config":
        """
        Creates the singleton instance and loads all configuration layers.
        May only be called ONCE during the entire program run.

        Exceptions
        ----------
        RuntimeError      – on double initialization
        FileNotFoundError – if ini_path does not exist
        ValueError        – on invalid values in the INI file
        """
        if cls._instance is not None:
            raise RuntimeError(
                "Config.initialize() has already been called. "
                "Re-initialization is not allowed. "
                "(In tests: call Config._reset() before initialize().)"
            )

        instance = cls.__new__(cls)
        instance._data = {}
        instance._set_defaults()
        instance._load_ini(ini_path)
        instance._load_cli(args)
        if instance._data["target"] == "html":
            instance._data["htmlonly"] = True

        cls._instance = instance
        return instance

    @classmethod
    def get(cls) -> "Config":
        """
        Returns the singleton instance.

        Exceptions
        ----------
        RuntimeError – if initialize() has not been called yet
        """
        if cls._instance is None:
            raise RuntimeError(
                "Config.get() was called before Config.initialize(). "
                "Call initialize() first in main()."
            )
        return cls._instance

    @classmethod
    def _reset(cls) -> None:
        """FOR TESTS ONLY – resets the singleton instance."""
        cls._instance = None

    # ------------------------------------------------------------------
    # Layer 1 – Hard-coded default values
    # ------------------------------------------------------------------

    def _set_defaults(self) -> None:
        self._data = {

            # "Constants"
            "ebookauthor": "Martin Schweikert",
            "programname": PROGRAM_NAME,

            # Variables
            "debug":           False,
            "ebooksubtitle":    "",
            "ebooktitle":       "",
            "ebookyear":        str(date.today().year),
            "greekfontsize":   "1.05em",
            "hebrewfontsize":  "1.2em",
            "htmlonly":         False,
            "input_directory": "",
            "input_file":      "",
            "language":        "",
            "log_file":        "",       # empty = stdout only
            "log_level":       "INFO",
            "output_directory": "",      # empty = <input_directory>/L2E
            "target":          "epub",  # epub | html
            "sz":              "ß",
            "szquoted":        "ß",
            "longversionname": "font-style: italic;",
            "transliteration": "font-style: italic;",
            "verseemphasis":   "font-weight: bold;",
        }

    # ------------------------------------------------------------------
    # Layer 2 – INI file
    # ------------------------------------------------------------------

    def _load_ini(self, ini_path: Path) -> None:
        if not ini_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {ini_path}")

        parser = configparser.ConfigParser()
        parser.read(ini_path, encoding="utf-8")

        mapping = {
            # (ini-section, ini-key) → (internal key, type)
            ("EBOOK", "EbookAuthor"): ("ebookauthor", str),
            ("EBOOK", "EbookSubtitle"): ("ebooksubtitle", str),
            ("EBOOK", "EbookTitle"): ("ebooktitle", str),
            ("EBOOK", "EbookYear"): ("ebookyear", str),
            ("EBOOK", "sz"): ("sz", str),
            ("EBOOK", "szquoted"): ("szquoted", str),
            ("EBOOK", "LongVersionName"): ("longversionname", str),
            ("EBOOK", "Transliteration"): ("transliteration", str),
            ("EBOOK", "VerseEmphasis"): ("verseemphasis", str),
            ("EBOOK", "GreekFontSize"):  ("greekfontsize",  str),
            ("EBOOK", "HebrewFontSize"): ("hebrewfontsize", str),
            ("GENERAL", "Debug"): ("debug", bool),
            ("GENERAL", "HtmlOnly"): ("htmlonly", bool),
            ("GENERAL", "Language"): ("language", str),
            ("GENERAL", "Target"): ("target", str),
            ("LOGGING", "LogFile"): ("log_file", str),
            ("LOGGING", "LogLevel"): ("log_level", str),
            ("PATHS", "InputDirectory"): ("input_directory", str),
            ("PATHS", "InputFile"): ("input_file", str),
            ("PATHS", "OutputDirectory"): ("output_directory", str),
        }

        for (section, key), (internal_key, cast) in mapping.items():
            if parser.has_option(section, key):
                raw = parser.get(section, key)
                self._data[internal_key] = self._cast(raw, cast)

    # ------------------------------------------------------------------
    # Layer 3 – Command-line parameters
    # ------------------------------------------------------------------

    def _load_cli(self, args: argparse.Namespace) -> None:
        cli_mapping = {
            # argparse attribute  → (internal key, type)
            "ebook_year":       ("ebookyear",        str),
            "input_directory":  ("input_directory",  str),
            "input_file":       ("input_file",       str),
            "output_directory": ("output_directory", str),
            "language":         ("language",         str),
            "target":           ("target",           str),
            "log_level":        ("log_level",        str),
            "debug":            ("debug",            bool),
        }
        for attr, (internal_key, cast) in cli_mapping.items():
            value = getattr(args, attr, None)
            if value is not None:
                self._data[internal_key] = self._cast(value, cast)

    # ------------------------------------------------------------------
    # Helper – type conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _cast(value, cast: type):
        if cast is bool:
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("1", "true", "yes", "on")
        if cast is str:
            s = str(value)
            if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
                return s[1:-1]
            return s
        return cast(value)

    # ------------------------------------------------------------------
    # Getters
    # ------------------------------------------------------------------

    @property
    def input_directory(self) -> Path:
        return Path(self._data["input_directory"])

    @property
    def input_file(self) -> str:
        return self._data["input_file"]

    @property
    def tex_input(self) -> Path:
        """Full path to the LaTeX source file: input_directory / input_file."""
        return self.input_directory / self.input_file

    @property
    def output_directory(self) -> Path:
        """
        Output directory for all generated files.
        Defaults to <input_directory>/L2E if not set in INI or CLI.
        """
        raw = self._data["output_directory"]
        if raw:
            return Path(raw)
        return self.input_directory / "L2E"

    @property
    def language(self) -> str:
        return self._data["language"]

    @property
    def target(self) -> str:
        return self._data["target"]

    @property
    def htmlonly(self) -> bool:
        return self._data["htmlonly"]

    @property
    def log_level(self) -> str:
        return self._data["log_level"].upper()

    @property
    def log_file(self) -> str:
        name = self._data["log_file"] or f'{self._data["programname"]}.log'
        return str(self.output_directory / name)

    @property
    def debug(self) -> bool:
        return self._data["debug"]

    @property
    def ebook_title(self) -> str:
        return self._data["ebooktitle"]

    @property
    def ebook_author(self) -> str:
        return self._data["ebookauthor"]

    @property
    def ebook_subtitle(self) -> str:
        return self._data["ebooksubtitle"]

    @property
    def ebook_year(self) -> str:
        return self._data["ebookyear"]

    @property
    def sz(self) -> str:
        return self._data["sz"]

    @property
    def szquoted(self) -> str:
        return self._data["szquoted"]

    @property
    def programname(self) -> str:
        return self._data["programname"]

    @property
    def longversionname(self) -> str:
        return self._data["longversionname"]

    @property
    def greek_font_size(self) -> str:
        return self._data["greekfontsize"]

    @property
    def hebrew_font_size(self) -> str:
        return self._data["hebrewfontsize"]

    @property
    def transliteration(self) -> str:
        return self._data["transliteration"]

    @property
    def verse_emphasis(self) -> str:
        return self._data["verseemphasis"]

    def __repr__(self) -> str:
        return (
            f"Config("
            f"programname={self.programname!r}, "
            f"greek_font_size={self.greek_font_size!r}, "
            f"hebrew_font_size={self.hebrew_font_size!r}, "
            f"transliteration={self.transliteration!r}, "
            f"verse_emphasis={self.verse_emphasis!r}, "
            f"tex_input={self.tex_input}, "
            f"output_directory={self.output_directory}, "
            f"language={self.language!r}, "
            f"target={self.target!r}, "
            f"htmlonly={self.htmlonly}, "
            f"ebook_title={self.ebook_title!r}, "
            f"ebook_author={self.ebook_author!r}, "
            f"ebook_subtitle={self.ebook_subtitle!r}, "
            f"ebook_year={self.ebook_year!r}, "
            f"log_level={self.log_level!r}, "
            f"log_file={self.log_file!r}, "
            f"debug={self.debug}, "
            f"sz={self.sz!r}, "
            f"szquoted={self.szquoted!r})"
        )
