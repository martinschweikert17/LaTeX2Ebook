"""
latex/bible_names.py – Parse Bible translation names from übersetzungen.tex
===========================================================================

Reads \DeclareBibleName{ABBREV}{Full Name} entries and exposes them as a
plain dict so that \biblename and \longbiblename can be resolved at
conversion time.
"""

import re

from config import Config

_ENTRY = re.compile(r'^\\DeclareBibleName\{([^}]+)\}\{([^}]+)\}', re.MULTILINE)


def load_bible_names() -> dict[str, str]:
    """Return {abbreviation: full_name} from the configured übersetzungen.tex."""
    path = Config.get().translations
    text = path.read_text(encoding="utf-8")
    return {m.group(1): m.group(2) for m in _ENTRY.finditer(text)}
