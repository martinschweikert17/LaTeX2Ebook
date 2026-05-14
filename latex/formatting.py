"""
latex/formatting.py – Convert LaTeX formatting commands to HTML spans
=====================================================================

Responsibility
--------------
Replaces LaTeX formatting commands of the form \\cmd{...} with
HTML <span class="cls">...</span> elements. The mapping of commands
to CSS classes is defined in _SPAN_COMMANDS.

Pipeline position
-----------------
  latex/expressions.py calls apply_formatting()
"""

import re

_BIBLEVERSEFORMAT = re.compile(
    r'\\begin\{\\bibleverseformat\}(.*?)\\end\{\\bibleverseformat\}',
    re.DOTALL,
)

_SPAN_COMMANDS = (
    # (latex-command, css-class)
    # css-class may differ from the command name so that multiple commands
    # can share the same CSS rule.
    ('transliteration', 'transliteration'),
    ('verseemphasis',   'verseemphasis'),
    ('quotegreek',      'greek'),
)


def apply_formatting(text: str) -> str:

    text = _BIBLEVERSEFORMAT.sub(lambda m: f'<p class="quotation">{m.group(1)}</p>', text)

    for cmd, cls in _SPAN_COMMANDS:
        text = _replace_cmd(text, f'\\{cmd}', f'<span class="{cls}">', '</span>')
    return text


def _eliminate_cmd(text: str, cmd: str) -> str:
    """Remove \\cmd{...} including its content entirely, handling nested braces."""
    trigger = cmd + '{'
    if trigger not in text:
        return text

    out = []
    i = 0
    while i < len(text):
        if text[i:i + len(trigger)] == trigger:
            j = i + len(trigger)
            d = 1
            while j < len(text) and d > 0:
                if text[j] == '{':
                    d += 1
                elif text[j] == '}':
                    d -= 1
                j += 1
            i = j
        else:
            out.append(text[i])
            i += 1
    return ''.join(out)


def _replace_cmd(text: str, cmd: str, open_tag: str, close_tag: str) -> str:
    """Replace \\cmd{...} with open_tag + content + close_tag, handling nested braces."""
    trigger = cmd + '{'
    if trigger not in text:
        return text

    out = []
    i = 0
    while i < len(text):
        if text[i:i + len(trigger)] == trigger:
            j = i + len(trigger)
            d = 1
            while j < len(text) and d > 0:
                if text[j] == '{':
                    d += 1
                elif text[j] == '}':
                    d -= 1
                j += 1
            out.append(open_tag + text[i + len(trigger):j - 1] + close_tag)
            i = j
        else:
            out.append(text[i])
            i += 1
    return ''.join(out)