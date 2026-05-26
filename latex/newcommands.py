"""
latex/newcommands.py – Expand zero-argument \\newcommand definitions
====================================================================

Responsibility
--------------
Collects every zero-argument \\newcommand{\\cmd}{body} (and \\renewcommand)
using brace-counting so that nested braces in the body are handled correctly.
Then removes ALL \\newcommand / \\renewcommand / \\newcolumntype definitions
(also brace-counted) and substitutes every {\\cmd} occurrence with its body.

For \\fm* and \\meta* variables two additional syntax variants are supported:
  \\newcommand{fmtitle}{...}   – without backslash before the command name
  \\fmtitle                    – bare command (expanded in addition to {\\fmtitle})

This makes it possible to define LTOE-only frontmatter variables that are not
valid LaTeX macros (and would be skipped by the LaTeX compiler).

Only {\\cmd} syntax is expanded for regular commands — bare \\cmd is left alone
because it may appear legally inside other LaTeX constructs that are handled
later in the pipeline.

Pipeline position
-----------------
  latex/decomment.py  →  [latex/newcommands.py]  →  latex/personal_settings.py
"""

import re
import logging

from config import PROGRAM_NAME

_logger = logging.getLogger(f"{PROGRAM_NAME}.latex.newcommands")

# ── Cached values (populated during expand_newcommands) ───────────────────────

_FM_VALUES:   dict[str, str] = {}
_META_VALUES: dict[str, str] = {}


def get_fm_value(key: str) -> str:
    """Return value of \\fm<key> extracted from the LaTeX source."""
    return _FM_VALUES.get(key, '')


def get_meta_value(key: str) -> str:
    """Return value of \\meta<key> extracted from the LaTeX source."""
    return _META_VALUES.get(key, '')


# ── Regexes ───────────────────────────────────────────────────────────────────

# Standard form: \newcommand{\cmd}{body}  – backslash required before name
_ZERO_ARG_OPEN = re.compile(
    r'\\(?:new|renew)command\*?\s*\{(\\[A-Za-z]+)\}\s*(?!\[)\{'
)

# fm/meta form: \newcommand{\fmXXX}{body}  OR  \newcommand{fmXXX}{body}
# The backslash before the name is optional here.
_FM_META_OPEN = re.compile(
    r'\\(?:new|renew)command\*?\s*\{\\?((?:fm|meta)[A-Za-z]*)\}\s*(?!\[)\{'
)

# Broad removal: catches \newcommand{\cmd}{} and \newcommand{}{} (empty name)
_ANY_CMD_OPEN = re.compile(
    r'\\(?:(?:new|renew)command\*?\s*\{(?:\\[A-Za-z]+)?\}|newcolumntype\s*\{[^}]*\})'
    r'\s*(?:\[[^\]]*\])?\s*\{'
)


def _brace_body(text: str, start: int) -> int:
    """Return the index just past the closing '}' of a brace group.

    *start* must point to the character AFTER the opening '{'.
    """
    depth = 1
    j = start
    n = len(text)
    while j < n and depth > 0:
        if text[j] == '{':
            depth += 1
        elif text[j] == '}':
            depth -= 1
        j += 1
    return j


def expand_newcommands(text: str) -> str:
    """
    Expand zero-argument \\newcommand definitions found in *text*.

    1. Collect standard definitions {\\cmd} and fm/meta definitions (both syntaxes).
    2. Remove all definition forms from the source.
    3. Replace every {\\cmd} with its body (longest name first).
    4. Replace bare \\fmXXX and \\metaXXX with their bodies.
    """
    n = len(text)
    cmds: dict[str, str] = {}

    # --- Pass 1a: collect standard zero-arg definitions \newcommand{\cmd}{body} ---
    i = 0
    while i < n:
        m = _ZERO_ARG_OPEN.search(text, i)
        if m is None:
            break
        cmd_name   = m.group(1)          # e.g. '\fmtitle' or '\emphtext'
        body_start = m.end()
        body_end   = _brace_body(text, body_start)
        body       = text[body_start:body_end - 1]
        if cmd_name in cmds:
            _logger.debug("Redefinition of %s – last wins", cmd_name)
        cmds[cmd_name] = body
        i = body_end

    # --- Pass 1b: collect fm/meta definitions (also without-backslash form) ---
    i = 0
    while i < n:
        m = _FM_META_OPEN.search(text, i)
        if m is None:
            break
        cmd_name   = '\\' + m.group(1)  # normalise to \fmtitle form
        body_start = m.end()
        body_end   = _brace_body(text, body_start)
        body       = text[body_start:body_end - 1]
        if cmd_name not in cmds:         # standard form (Pass 1a) wins
            cmds[cmd_name] = body
        i = body_end

    # Populate module-level caches
    _FM_VALUES.clear()
    _META_VALUES.clear()
    for cmd_name, body in cmds.items():
        short = cmd_name[1:]             # strip leading backslash
        if short.startswith('fm'):
            _FM_VALUES[short]   = body
        elif short.startswith('meta'):
            _META_VALUES[short] = body

    if not cmds:
        return text

    # --- Pass 2a: remove standard \newcommand definitions ---
    out: list[str] = []
    i = 0
    while i < n:
        m = _ANY_CMD_OPEN.search(text, i)
        if m is None:
            out.append(text[i:])
            break
        out.append(text[i:m.start()])
        i = _brace_body(text, m.end())
    text = ''.join(out)

    # --- Pass 2b: remove fm/meta without-backslash definitions (not caught above) ---
    n = len(text)
    out = []
    i = 0
    while i < n:
        m = _FM_META_OPEN.search(text, i)
        if m is None:
            out.append(text[i:])
            break
        out.append(text[i:m.start()])
        i = _brace_body(text, m.end())
    text = ''.join(out)

    # --- Pass 3: substitute {\\cmd} occurrences (longest name first) ---
    # fm* and meta* are intentionally skipped: they carry CSS class information
    # and are expanded later by convert_expressions with class-preserving logic.
    for cmd_name in sorted(cmds, key=len, reverse=True):
        short = cmd_name[1:]  # strip leading backslash
        if short.startswith(('fm', 'meta')):
            continue
        key = '{' + cmd_name + '}'
        if key in text:
            text = text.replace(key, cmds[cmd_name])
            _logger.debug("Expanded %s → %r", cmd_name, cmds[cmd_name])

    return text
