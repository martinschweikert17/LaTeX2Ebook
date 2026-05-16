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

_ITEMIZE     = re.compile(r'\\begin\{itemize\}(.*?)\\end\{itemize\}',       re.DOTALL)
_ENUMERATE   = re.compile(r'\\begin\{enumerate\}(.*?)\\end\{enumerate\}',   re.DOTALL)
_DESCRIPTION = re.compile(r'\\begin\{description\}(.*?)\\end\{description\}', re.DOTALL)
_ITEM        = re.compile(r'[ \t]*\\item(?:\[[^\]]*\])?\s*')
_ITEM_DESC   = re.compile(r'[ \t]*\\item(?:\[([^\]]*)\])?\s*')

_SPAN_COMMANDS = (
    # (latex-command, css-class)
    # css-class may differ from the command name so that multiple commands
    # can share the same CSS rule.
    ('transliteration', 'transliteration'),
    ('verseemphasis',   'verseemphasis'),
    ('versenumber',     'versenumber'),
    ('quotegreek',      'greek'),
)


def _itemize_to_html(content: str, tag: str) -> str:
    parts = _ITEM.split(content)
    items = ''.join(f'<li>{p.strip()}</li>' for p in parts if p.strip())
    return f'<{tag}>{items}</{tag}>'


def _description_to_html(content: str) -> str:
    # re.split with one capturing group yields [pre, label0, text0, label1, text1, ...]
    parts   = _ITEM_DESC.split(content)
    labels  = parts[1::2]   # captured label or None
    texts   = parts[2::2]   # item content
    entries = []
    for label, text in zip(labels, texts):
        text = text.strip()
        if label is not None:
            entries.append(f'<dt>{label}</dt><dd>{text}</dd>')
        else:
            entries.append(f'<dd>{text}</dd>')
    return '<dl>' + ''.join(entries) + '</dl>'


def apply_formatting(text: str) -> str:

    text = _ITEMIZE.sub(lambda m: _itemize_to_html(m.group(1), 'ul'), text)
    text = _ENUMERATE.sub(lambda m: _itemize_to_html(m.group(1), 'ol'), text)
    text = _DESCRIPTION.sub(lambda m: _description_to_html(m.group(1)), text)
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