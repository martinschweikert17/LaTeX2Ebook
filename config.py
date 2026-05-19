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

  Exception – biblerefstyle / biblerefformat:
  1. Hard-coded default values
  2. LaTeX source  (\\biblerefstyle{} / \\biblerefformat{})
  3. INI file
  4. Command-line parameters       (highest – overrides source)

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

_BIBLEREF_STYLES: frozenset[str] = frozenset(
    {"lthk", "lutherbibel", "einheitsuebersetzung", "jerusalem"}
)

_NUMBERING_STYLES: frozenset[str] = frozenset(
    {"arabic", "roman_upper", "roman_lower", "alpha_upper", "alpha_lower", "none"}
)

_SZ_MAP: dict[str, tuple[str, str]] = {
    #                sz    szquoted
    "normal":     ("ß",  "ß"),
    "aggressive": ("ss", "ß"),
    "radical":    ("ss", "ss"),
}


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
        instance._load_lang_section(ini_path)
        instance._validate_paths()

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
            "programname": PROGRAM_NAME,

            # Variables
            "author":          "Martin Schweikert",
            "debug":           False,
            "description":     "",
            "keywords":        "",
            "subtitle":        "",
            "title":           "",
            "year":            str(date.today().year),
            "greekfontsize":   "1.05em",
            "hebrewfontsize":  "1.2em",
            "htmlonly":         False,
            "input_directory": "",
            "input_file":      "",
            "language":        "DE",
            "log_file":        "",       # empty = stdout only
            "log_level":       "INFO",
            "output_directory": "",      # empty = <input_directory>/L2E
            "target":          "epub",  # epub | html
            "szmode":          "normal",
            "longversionname":   "font-style: italic;",
            "transliteration":   "font-style: italic;",
            "verseemphasis":     "font-weight: bold;",
            "personnameformat":  "text-transform: uppercase; font-size: 85%;",
            "biblerefstyle":              "LThK",
            "biblerefformat":             "kurz",
            "translations":               "",
            "jhwh":                       "Jahwe",
            "numbering_part":             "roman_upper",
            "numbering_chapter":          "arabic",
            "numbering_section":          "arabic",
            "numbering_subsection":       "arabic",
            "numbering_subsubsection":    "arabic",
        }

    # ------------------------------------------------------------------
    # Layer 2 – INI file
    # ------------------------------------------------------------------

    def _load_ini(self, ini_path: Path) -> None:
        if not ini_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {ini_path}")

        parser = configparser.ConfigParser(interpolation=None)
        parser.read(ini_path, encoding="utf-8")

        mapping = {
            # (ini-section, ini-key) → (internal key, type)
            ("EBOOK", "SZMode"):         ("szmode",          str),
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
            ("PATHS", "OutputDirectory"):  ("output_directory", str),
            ("PATHS", "Translations"):     ("translations",     str),
            ("EBOOK", "YHWH"):             ("jhwh",             str),
            ("EBOOK", "PersonNameFormat"): ("personnameformat",  str),
            ("EBOOK", "BibleRefStyle"):             ("biblerefstyle",           str),
            ("EBOOK", "BibleRefFormat"):            ("biblerefformat",          str),
            ("EBOOK", "NumberingPart"):             ("numbering_part",          str),
            ("EBOOK", "NumberingChapter"):          ("numbering_chapter",       str),
            ("EBOOK", "NumberingSection"):          ("numbering_section",       str),
            ("EBOOK", "NumberingSubsection"):       ("numbering_subsection",    str),
            ("EBOOK", "NumberingSubsubsection"):    ("numbering_subsubsection", str),
        }

        self._ini_keys: set[str] = set()
        for (section, key), (internal_key, cast) in mapping.items():
            if parser.has_option(section, key):
                raw = parser.get(section, key)
                self._data[internal_key] = self._cast(raw, cast)
                self._ini_keys.add(internal_key)

    # ------------------------------------------------------------------
    # Layer 3 – Command-line parameters
    # ------------------------------------------------------------------

    def _load_cli(self, args: argparse.Namespace) -> None:
        cli_mapping = {
            # argparse attribute  → (internal key, type)
            "input_directory":  ("input_directory",  str),
            "input_file":       ("input_file",       str),
            "output_directory": ("output_directory", str),
            "language":         ("language",         str),
            "target":           ("target",           str),
            "log_level":        ("log_level",        str),
            "debug":            ("debug",            bool),
            "biblerefstyle":    ("biblerefstyle",    str),
            "biblerefformat":   ("biblerefformat",   str),
        }
        self._cli_keys: set[str] = set()
        for attr, (internal_key, cast) in cli_mapping.items():
            value = getattr(args, attr, None)
            if value is not None:
                self._data[internal_key] = self._cast(value, cast)
                self._cli_keys.add(internal_key)

    # ------------------------------------------------------------------
    # Layer 4 – Language-specific INI section (after CLI so language is final)
    # ------------------------------------------------------------------

    def _load_lang_section(self, ini_path: Path) -> None:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(ini_path, encoding="utf-8")
        lang_section = f"LANG_{self._data['language'].upper()}"
        if parser.has_section(lang_section):
            for key, internal_key in (
                ("Author",      "author"),
                ("Description", "description"),
                ("Keywords",    "keywords"),
                ("Subtitle",    "subtitle"),
                ("Title",       "title"),
                ("Year",        "year"),
            ):
                if parser.has_option(lang_section, key):
                    self._data[internal_key] = parser.get(lang_section, key)

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_paths(self) -> None:
        for key, label in (
            ("translations", "Translations"),
        ):
            raw = self._data[key]
            if not raw:
                raise FileNotFoundError(
                    f"[PATHS] {label} is not configured in the INI file."
                )
            path = Path(raw).expanduser()
            if not path.exists():
                raise FileNotFoundError(
                    f"[PATHS] {label}: file not found: {path}"
                )
        szmode = self._data["szmode"]
        if szmode not in _SZ_MAP:
            raise ValueError(
                f"[EBOOK] SZMode = {szmode!r} ist ungültig. "
                f"Erlaubte Werte: {list(_SZ_MAP)}"
            )
        biblerefstyle = self._data["biblerefstyle"]
        if biblerefstyle.lower() not in _BIBLEREF_STYLES:
            raise ValueError(
                f"[EBOOK] BibleRefStyle = {biblerefstyle!r} ist ungültig. "
                f"Erlaubte Werte: LThK, Lutherbibel, Einheitsuebersetzung, jerusalem"
            )
        biblerefformat = {"short": "kurz", "long": "lang"}.get(
            self._data["biblerefformat"].lower(), self._data["biblerefformat"].lower()
        )
        self._data["biblerefformat"] = biblerefformat
        if biblerefformat not in ("kurz", "lang"):
            raise ValueError(
                f"[EBOOK] BibleRefFormat = {biblerefformat!r} ist ungültig. "
                f"Erlaubte Werte: kurz / short, lang / long"
            )
        _numbering_keys = {
            "numbering_part":          "NumberingPart",
            "numbering_chapter":       "NumberingChapter",
            "numbering_section":       "NumberingSection",
            "numbering_subsection":    "NumberingSubsection",
            "numbering_subsubsection": "NumberingSubsubsection",
        }
        for key, ini_name in _numbering_keys.items():
            val = self._data[key]
            if val not in _NUMBERING_STYLES:
                raise ValueError(
                    f"[EBOOK] {ini_name} = {val!r} ist ungültig. "
                    f"Erlaubte Werte: {sorted(_NUMBERING_STYLES)}"
                )

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
        return Path(self._data["input_directory"]).expanduser()

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
    def description(self) -> str:
        return self._data["description"]

    @property
    def keywords(self) -> str:
        return self._data["keywords"]

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
    def title(self) -> str:
        return self._data["title"]

    @property
    def subtitle(self) -> str:
        return self._data["subtitle"]

    @property
    def author(self) -> str:
        return self._data["author"]

    @property
    def year(self) -> str:
        return self._data["year"]

    @property
    def szmode(self) -> str:
        return self._data["szmode"]

    @property
    def sz(self) -> str:
        return _SZ_MAP[self._data["szmode"]][0]

    @property
    def szquoted(self) -> str:
        return _SZ_MAP[self._data["szmode"]][1]

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

    @property
    def biblerefstyle(self) -> str:
        return self._data["biblerefstyle"]

    @property
    def biblerefformat(self) -> str:
        return self._data["biblerefformat"]

    def cli_has(self, key: str) -> bool:
        """True if the given internal key was explicitly set via CLI."""
        return key in getattr(self, "_cli_keys", set())

    def ini_has(self, key: str) -> bool:
        """True if the given internal key was explicitly set via INI."""
        return key in getattr(self, "_ini_keys", set())

    @property
    def jhwh(self) -> str:
        return self._data["jhwh"]

    @property
    def person_name_format(self) -> str:
        return self._data["personnameformat"]

    @property
    def heading_numbering(self) -> dict[str, str]:
        """Numbering style per heading level (part, chapter, section, subsection, subsubsection)."""
        return {
            "part":          self._data["numbering_part"],
            "chapter":       self._data["numbering_chapter"],
            "section":       self._data["numbering_section"],
            "subsection":    self._data["numbering_subsection"],
            "subsubsection": self._data["numbering_subsubsection"],
        }

    @property
    def translations(self) -> Path:
        raw = self._data["translations"]
        if raw:
            return Path(raw).expanduser()
        return Path(__file__).parent / "data" / "übersetzungen.tex"

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
            f"description={self.description!r}, "
            f"keywords={self.keywords!r}, "
            f"target={self.target!r}, "
            f"htmlonly={self.htmlonly}, "
            f"title={self.title!r}, "
            f"subtitle={self.subtitle!r}, "
            f"author={self.author!r}, "
            f"year={self.year!r}, "
            f"log_level={self.log_level!r}, "
            f"log_file={self.log_file!r}, "
            f"debug={self.debug}, "
            f"szmode={self.szmode!r}, "
            f"biblerefstyle={self.biblerefstyle!r}, "
            f"biblerefformat={self.biblerefformat!r}, "
            f"jhwh={self.jhwh!r})"
        )
