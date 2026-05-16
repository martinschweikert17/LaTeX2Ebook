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
_ENUMERATE   = re.compile(r'\\begin\{enumerate\}(?:\[([^\]]*)\])?(.*?)\\end\{enumerate\}', re.DOTALL)
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


_LABEL_TYPES = {
    r'\alph':   'a',
    r'\Alph':   'A',
    r'\roman':  'i',
    r'\Roman':  'I',
    r'\arabic': '1',
}


def _enumerate_type(opt: str | None) -> str:
    """Return the HTML type attribute value from a LaTeX enumerate optional arg."""
    if not opt:
        return ''
    for latex_cmd, html_type in _LABEL_TYPES.items():
        if latex_cmd in opt:
            return f' type="{html_type}"'
    return ''


def _itemize_to_html(content: str, tag: str, type_attr: str = '') -> str:
    parts = _ITEM.split(content)
    items = ''.join(f'<li>{p.strip()}</li>' for p in parts if p.strip())
    return f'<{tag}{type_attr}>{items}</{tag}>'


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


def _replace_textcolor(text: str) -> str:
    """Replace \\textcolor{color}{text} with <span style="color: color;">text</span>."""
    trigger = r'\textcolor{'
    if trigger not in text:
        return text
    out = []
    i = 0
    while i < len(text):
        if text[i:i + len(trigger)] == trigger:
            # parse first arg: color
            j = i + len(trigger)
            d = 1
            while j < len(text) and d > 0:
                if text[j] == '{':   d += 1
                elif text[j] == '}': d -= 1
                j += 1
            color = text[i + len(trigger):j - 1]
            # parse second arg: content
            if j < len(text) and text[j] == '{':
                k = j + 1
                d = 1
                while k < len(text) and d > 0:
                    if text[k] == '{':   d += 1
                    elif text[k] == '}': d -= 1
                    k += 1
                content = text[j + 1:k - 1]
                out.append(f'<span style="color: {color};">{content}</span>')
                i = k
            else:
                out.append(text[i])
                i += 1
        else:
            out.append(text[i])
            i += 1
    return ''.join(out)


def apply_formatting(text: str) -> str:

    text = _ITEMIZE.sub(lambda m: _itemize_to_html(m.group(1), 'ul'), text)
    text = _ENUMERATE.sub(
        lambda m: _itemize_to_html(m.group(2), 'ol', _enumerate_type(m.group(1))), text
    )
    text = _DESCRIPTION.sub(lambda m: _description_to_html(m.group(1)), text)
    text = _BIBLEVERSEFORMAT.sub(lambda m: f'<p class="quotation">{m.group(1)}</p>', text)

    text = _replace_cmd(text, r'\textbf', '<strong>', '</strong>')
    text = _replace_cmd(text, r'\textit', '<i>', '</i>')
    text = _replace_textcolor(text)

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