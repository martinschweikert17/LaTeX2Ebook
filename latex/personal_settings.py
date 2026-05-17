"""
latex/personal_settings.py – JHWH command mappings driven by [EBOOK] JHWH
==========================================================================

Translates the INI setting JHWH ∈ {Jahwe, JHWH, HERR, hebrew} into a
dict {command_name: replacement_text} that is applied to the LaTeX source
before the rest of the conversion pipeline runs.
"""

import re
import logging

from config import Config, PROGRAM_NAME

_logger = logging.getLogger(f"{PROGRAM_NAME}.latex.personal_settings")

_HEB = r'{\larger[1]\cjRL{yhwh}}'

_JHWH_COMMANDS: dict[str, dict[str, str]] = {
    'Jahwe': {
        'jhwh':    'Jahwe',
        'jhwhNU':  'Jahwe',
        'jhwhNL':  'Jahwe',
        'jhwhGU':  'Jahwes',
        'jhwhGL':  'Jahwes',
        'jhwhDU':  'Jahwe',
        'jhwhDL':  'Jahwe',
        'jhwhDUA': 'Dem Jahwe',
        'jhwhDLA': 'dem Jahwe',
        'jhwhAU':  'Jahwe',
        'jhwhAL':  'Jahwe',
    },
    'JHWH': {
        'jhwh':    'JHWH',
        'jhwhNU':  'JHWH',
        'jhwhNL':  'JHWH',
        'jhwhGU':  'JHWHs',
        'jhwhGL':  'JHWHs',
        'jhwhDU':  'JHWH',
        'jhwhDL':  'JHWH',
        'jhwhDUA': 'Dem JHWH',
        'jhwhDLA': 'dem JHWH',
        'jhwhAU':  'JHWH',
        'jhwhAL':  'JHWH',
    },
    'HERR': {
        'jhwh':    'HERR',
        'jhwhNU':  'Der HERR',
        'jhwhNL':  'der HERR',
        'jhwhGU':  'Des HERRn',
        'jhwhGL':  'des HERRn',
        'jhwhDU':  'Dem HERRn',
        'jhwhDL':  'dem HERRn',
        'jhwhDUA': 'Dem HERRn',
        'jhwhDLA': 'dem HERRn',
        'jhwhAU':  'Den HERRn',
        'jhwhAL':  'den HERRn',
    },
    'hebrew': {
        'jhwh':    _HEB,
        'jhwhNU':  _HEB,
        'jhwhNL':  _HEB,
        'jhwhGU':  _HEB + 's',
        'jhwhGL':  _HEB + 's',
        'jhwhDU':  _HEB,
        'jhwhDL':  _HEB,
        'jhwhDUA': _HEB,
        'jhwhDLA': _HEB,
        'jhwhAU':  _HEB,
        'jhwhAL':  _HEB,
    },
}

VALID_JHWH = tuple(_JHWH_COMMANDS)


def build_jhwh_commands() -> dict[str, str]:
    """Return the command→replacement map for the configured JHWH mode."""
    mode = Config.get().jhwh
    if mode not in _JHWH_COMMANDS:
        raise ValueError(
            f"[EBOOK] JHWH = {mode!r} ist ungültig. "
            f"Erlaubte Werte: {list(_JHWH_COMMANDS)}"
        )
    commands = _JHWH_COMMANDS[mode]
    _logger.debug("JHWH-Modus: %s (%d Befehle)", mode, len(commands))
    return commands


def apply_personal_commands(text: str, commands: dict[str, str]) -> str:
    """
    Replace \\cmdname with its defined replacement.
    Handles both {\\cmdname} (LaTeX grouping) and bare \\cmdname.
    Longer names are substituted first to avoid prefix collisions.
    """
    for name in sorted(commands, key=len, reverse=True):
        repl = commands[name]
        text = text.replace('{\\' + name + '}', repl)
        text = re.sub(rf'\\{re.escape(name)}(?![a-zA-Z])', lambda m, r=repl: r, text)
    return text
