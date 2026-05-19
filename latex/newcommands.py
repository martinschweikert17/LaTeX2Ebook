"""
latex/newcommands.py – Expand zero-argument \\newcommand definitions
====================================================================

Responsibility
--------------
Collects every zero-argument \\newcommand{\\cmd}{body} (and \\renewcommand)
using brace-counting so that nested braces in the body are handled correctly.
Then removes ALL \\newcommand / \\renewcommand / \\newcolumntype definitions
(also brace-counted) and substitutes every {\\cmd} occurrence with its body.

Only {\\cmd} syntax is expanded — bare \\cmd is left alone because it may
appear legally inside other LaTeX constructs that are handled later in the
pipeline.

Pipeline position
-----------------
  latex/decomment.py  →  [latex/newcommands.py]  →  latex/personal_settings.py
"""

import re
import logging

from config import PROGRAM_NAME

_logger = logging.getLogger(f"{PROGRAM_NAME}.latex.newcommands")

# Matches the opening of a zero-argument \newcommand / \renewcommand definition.
# The (?!\[) negative lookahead rejects definitions with an argument count [n].
_ZERO_ARG_OPEN = re.compile(
    r'\\(?:new|renew)command\*?\s*\{(\\[A-Za-z]+)\}\s*(?!\[)\{'
)

# Matches the opening of ANY \newcommand / \renewcommand / \newcolumntype
# (used for the removal pass — broader than _ZERO_ARG_OPEN).
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

    1. Collect all zero-arg definitions using brace-counting.
    2. Remove all \\newcommand / \\renewcommand / \\newcolumntype definitions
       using brace-counting (so nested braces never leave stray '}').
    3. Replace every {\\cmd} with the recorded body (longest name first).
    """
    # --- Pass 1: collect zero-arg definitions ---
    cmds: dict[str, str] = {}
    i = 0
    n = len(text)
    while i < n:
        m = _ZERO_ARG_OPEN.search(text, i)
        if m is None:
            break
        cmd_name = m.group(1)
        body_start = m.end()           # character after the opening '{'
        body_end   = _brace_body(text, body_start)
        body       = text[body_start : body_end - 1]
        if cmd_name in cmds:
            _logger.debug("Redefinition of %s – last wins", cmd_name)
        cmds[cmd_name] = body
        i = body_end

    if not cmds:
        return text

    # --- Pass 2: remove ALL newcommand-style definitions (brace-counted) ---
    out: list[str] = []
    i = 0
    while i < n:
        m = _ANY_CMD_OPEN.search(text, i)
        if m is None:
            out.append(text[i:])
            break
        out.append(text[i : m.start()])
        i = _brace_body(text, m.end())
    text = ''.join(out)

    # --- Pass 3: substitute {\\cmd} occurrences (longest name first) ---
    for cmd_name in sorted(cmds, key=len, reverse=True):
        replacement = cmds[cmd_name]
        key = '{' + cmd_name + '}'
        if key in text:
            text = text.replace(key, replacement)
            _logger.debug("Expanded %s → %r", cmd_name, replacement)

    return text
