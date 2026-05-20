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

_XLTABULAR = re.compile(
    r'\\begin\{xltabular\}\{[^}]*\}\{[^}]*\}(.*?)\\end\{xltabular\}',
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


def _format_personname(content: str) -> str:
    """Wrap lowercase runs in <span class="personname">; uppercase/non-alpha chars pass through."""
    result = []
    i = 0
    while i < len(content):
        if content[i].islower():
            j = i + 1
            while j < len(content) and content[j].islower():
                j += 1
            result.append(f'<span class="personname">{content[i:j]}</span>')
            i = j
        else:
            result.append(content[i])
            i += 1
    return ''.join(result)


def _personname_to_html(text: str) -> str:
    return _replace_cmd_fn(text, r'\personenname', _format_personname)


def _replace_cmd_fn(text: str, cmd: str, fn) -> str:
    """Replace \\cmd{content} with fn(content), handling nested braces."""
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
                if text[j] == '{':   d += 1
                elif text[j] == '}': d -= 1
                j += 1
            out.append(fn(text[i + len(trigger):j - 1]))
            i = j
        else:
            out.append(text[i])
            i += 1
    return ''.join(out)


def _xltabular_to_html(body: str) -> str:
    rows_html = []
    for row in re.split(r'\\\\\s*', body):
        row = row.strip()
        if '&' not in row:
            continue
        td1, td2 = (c.strip() for c in row.split('&', 1))
        rows_html.append(f'<tr><td>{td1}</td><td>{td2}</td></tr>')
    return '<table>\n' + '\n'.join(rows_html) + '\n</table>' if rows_html else ''


def convert_quotehebrew(text: str, hebrew_class: str = 'hebrew') -> str:
    """Replace \\quotehebrew{arg1}{arg2}{arg3} with HTML spans.

    If arg2 is non-empty: <span class=hebrew_class>arg2</span> <span class="transliteration">arg3</span>
    If arg2 is empty:     arg1 <span class="transliteration">arg3</span>
    """
    trigger = r'\quotehebrew{'
    if trigger not in text:
        return text

    out = []
    i   = 0
    n   = len(text)

    def _brace_arg(start: int) -> tuple[str, int]:
        depth = 1
        j = start
        while j < n and depth > 0:
            if   text[j] == '{': depth += 1
            elif text[j] == '}': depth -= 1
            j += 1
        return text[start:j - 1], j

    def _skip_to_arg(start: int) -> int:
        j = start
        while j < n and text[j] != '{':
            j += 1
        return j + 1   # points to first char inside '{'

    while i < n:
        pos = text.find(trigger, i)
        if pos < 0:
            out.append(text[i:])
            break
        out.append(text[i:pos])

        j        = pos + len(trigger)   # first char of arg1 body
        arg1, j  = _brace_arg(j)
        j        = _skip_to_arg(j)
        arg2, j  = _brace_arg(j)
        j        = _skip_to_arg(j)
        arg3, j  = _brace_arg(j)

        hebrew = arg2 if arg2.strip() else arg1
        out.append(
            f'<span class="{hebrew_class}">{hebrew}</span>'
            f' <span class="transliteration">{arg3}</span>'
        )

        i = j

    return ''.join(out)


def apply_formatting(text: str) -> str:

    text = _ITEMIZE.sub(lambda m: _itemize_to_html(m.group(1), 'ul'), text)
    text = _ENUMERATE.sub(
        lambda m: _itemize_to_html(m.group(2), 'ol', _enumerate_type(m.group(1))), text
    )
    text = _DESCRIPTION.sub(lambda m: _description_to_html(m.group(1)), text)
    text = _BIBLEVERSEFORMAT.sub(lambda m: f'<p class="quotation">{m.group(1)}</p>', text)

    text = _replace_cmd(text, r'\centerline', '<p class="centerline">', '</p>')
    text = _replace_cmd(text, r'\minisec',   '<p class="minisec">',    '</p>')
    text = _replace_cmd(text, r'\textbf', '<strong>', '</strong>')
    text = _replace_cmd(text, r'\textit', '<i>', '</i>')
    text = _replace_textcolor(text)

    for cmd, cls in _SPAN_COMMANDS:
        text = _replace_cmd(text, f'\\{cmd}', f'<span class="{cls}">', '</span>')
    text = _personname_to_html(text)
    text = _XLTABULAR.sub(lambda m: _xltabular_to_html(m.group(1)), text)
    return text


def _eliminate_cmd(text: str, cmd: str) -> str:
    """Remove \\cmd{...} including its content entirely, handling nested braces.

    If the command is the only non-whitespace content on its line the entire
    line (including its trailing newline) is removed, so no spurious blank
    line is left behind in the output.
    """
    trigger = cmd + '{'
    if trigger not in text:
        return text

    out  = []
    prev = 0
    i    = 0
    n    = len(text)

    while True:
        pos = text.find(trigger, i)
        if pos < 0:
            out.append(text[prev:])
            break

        # Brace-counted end of command body
        j = pos + len(trigger)
        d = 1
        while j < n and d > 0:
            if   text[j] == '{': d += 1
            elif text[j] == '}': d -= 1
            j += 1

        # Line boundaries around the command
        ls = text.rfind('\n', 0, pos)
        ls = ls + 1 if ls >= 0 else 0
        le = text.find('\n', j)

        before_on_line = text[ls:pos]
        after_on_line  = text[j:le] if le >= 0 else text[j:]

        if before_on_line.strip() == '' and after_on_line.strip() == '':
            # Command is alone on its line → remove the whole line
            out.append(text[prev:ls])
            prev = (le + 1) if le >= 0 else n
        else:
            # Command is inline → remove only the command
            out.append(text[prev:pos])
            prev = j

        i = j

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