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

# LaTeX special-character escapes that may appear in main text after
# \newcommand expansion (e.g. \prozent -> \%, \euml -> \"e).
# Rules:
#   - Longer / more-specific patterns must precede any shorter prefix match
#     (e.g. \ldots before \l, \ddag before \dag, \OE before \O).
#   - Applied at the END of apply_formatting() after all LaTeX commands
#     (\item, \textit, etc.) have been consumed.
_LATEX_SPECIALS: list[tuple[str, str]] = [

    # -- \text... named character commands (most specific; process first) --
    (r'\textasciiacute',     '´'),
    (r'\textasciicircum',    '^'),
    (r'\textasciidieresis',  '¨'),
    (r'\textasciigrave',     '`'),
    (r'\textasciimacron',    '¯'),
    (r'\textasciitilde',     '~'),
    (r'\textbackslash',      '\\'),
    (r'\textbar',            '|'),
    (r'\textbraceleft',      '{'),
    (r'\textbraceright',     '}'),
    (r'\textbullet',         '•'),
    (r'\textcent',           '¢'),
    (r'\textcopyright',      '©'),
    (r'\textdaggerdbl',      '‡'),
    (r'\textdagger',         '†'),
    (r'\textdegree',         '°'),
    (r'\textellipsis',       '…'),
    (r'\textemdash',         '—'),
    (r'\textendash',         '–'),
    (r'\texteuro',           '€'),
    (r'\textgreater',        '>'),
    (r'\textless',           '<'),
    (r'\textminus',          '−'),
    (r'\textnumero',         '№'),
    (r'\textordfeminine',    'ª'),
    (r'\textordmasculine',   'º'),
    (r'\textparagraph',      '¶'),
    (r'\textperiodcentered', '·'),
    (r'\textperthousand',    '‰'),
    (r'\textpm',             '±'),
    (r'\textquotedblleft',   '“'),
    (r'\textquotedblright',  '”'),
    (r'\textquoteleft',      '‘'),
    (r'\textquoteright',     '’'),
    (r'\textregistered',     '®'),
    (r'\textsection',        '§'),
    (r'\textsterling',       '£'),
    (r'\texttimes',          '×'),
    (r'\texttrademark',      '™'),
    (r'\textunderscore',     '_'),
    (r'\textyen',            '¥'),

    # -- Em/en dashes (longer form first) ----------------------------------
    ('---', '—'),
    ('--',  '–'),

    # -- LaTeX reserved characters -----------------------------------------
    (r'\&',  '&amp;'),
    (r'\%',  '%'),
    (r'\#',  '#'),
    (r'\$',  '$'),
    (r'\{',  '{'),
    (r'\}',  '}'),
    (r'\_',  '_'),

    # -- Braced special letters (must precede unbraced \X forms) -----------
    (r'{\OE}', 'Œ'), (r'{\oe}', 'œ'),
    (r'{\AE}', 'Æ'), (r'{\ae}', 'æ'),
    (r'{\AA}', 'Å'), (r'{\aa}', 'å'),
    (r'{\NG}', 'Ŋ'), (r'{\ng}', 'ŋ'),
    (r'{\ss}', 'ß'),
    (r'{\O}',  'Ø'), (r'{\o}',  'ø'),
    (r'{\L}',  'Ł'), (r'{\l}',  'ł'),
    (r'{\i}',  'ı'), (r'{\j}',  'ȷ'),

    # -- Symbols that are prefixes of special letters (must precede them) --
    (r'\ddag',  '‡'),   # before \dag
    (r'\dag',   '†'),
    (r'\ldots', '…'),   # before \l
    (r'\dots',  '…'),

    # -- Unbraced special letters (longer forms first within each group) ---
    (r'\OE', 'Œ'), (r'\oe', 'œ'),   # \OE before \O, \oe before \o
    (r'\AE', 'Æ'), (r'\ae', 'æ'),
    (r'\AA', 'Å'), (r'\aa', 'å'),
    (r'\NG', 'Ŋ'), (r'\ng', 'ŋ'),
    (r'\ss', 'ß'),
    (r'\O',  'Ø'), (r'\o',  'ø'),
    (r'\L',  'Ł'), (r'\l',  'ł'),
    (r'\i',  'ı'), (r'\j',  'ȷ'),

    # -- Diacritics -- braced arg form \cmd{letter} ------------------------
    # umlaut \"
    (r'\"{A}', 'Ä'), (r'\"{a}', 'ä'),
    (r'\"{E}', 'Ë'), (r'\"{e}', 'ë'),
    (r'\"{I}', 'Ï'), (r'\"{i}', 'ï'),
    (r'\"{O}', 'Ö'), (r'\"{o}', 'ö'),
    (r'\"{U}', 'Ü'), (r'\"{u}', 'ü'),
    (r'\"{Y}', 'Ÿ'), (r'\"{y}', 'ÿ'),
    # acute \'
    (r"\'{A}", 'Á'), (r"\'{a}", 'á'),
    (r"\'{C}", 'Ć'), (r"\'{c}", 'ć'),
    (r"\'{E}", 'É'), (r"\'{e}", 'é'),
    (r"\'{I}", 'Í'), (r"\'{i}", 'í'),
    (r"\'{L}", 'Ĺ'), (r"\'{l}", 'ĺ'),
    (r"\'{N}", 'Ń'), (r"\'{n}", 'ń'),
    (r"\'{O}", 'Ó'), (r"\'{o}", 'ó'),
    (r"\'{R}", 'Ŕ'), (r"\'{r}", 'ŕ'),
    (r"\'{S}", 'Ś'), (r"\'{s}", 'ś'),
    (r"\'{U}", 'Ú'), (r"\'{u}", 'ú'),
    (r"\'{Y}", 'Ý'), (r"\'{y}", 'ý'),
    (r"\'{Z}", 'Ź'), (r"\'{z}", 'ź'),
    # grave \`
    (r'\`{A}', 'À'), (r'\`{a}', 'à'),
    (r'\`{E}', 'È'), (r'\`{e}', 'è'),
    (r'\`{I}', 'Ì'), (r'\`{i}', 'ì'),
    (r'\`{O}', 'Ò'), (r'\`{o}', 'ò'),
    (r'\`{U}', 'Ù'), (r'\`{u}', 'ù'),
    # circumflex \^
    (r'\^{A}', 'Â'), (r'\^{a}', 'â'),
    (r'\^{C}', 'Ĉ'), (r'\^{c}', 'ĉ'),
    (r'\^{E}', 'Ê'), (r'\^{e}', 'ê'),
    (r'\^{G}', 'Ĝ'), (r'\^{g}', 'ĝ'),
    (r'\^{H}', 'Ĥ'), (r'\^{h}', 'ĥ'),
    (r'\^{I}', 'Î'), (r'\^{i}', 'î'),
    (r'\^{J}', 'Ĵ'), (r'\^{j}', 'ĵ'),
    (r'\^{O}', 'Ô'), (r'\^{o}', 'ô'),
    (r'\^{S}', 'Ŝ'), (r'\^{s}', 'ŝ'),
    (r'\^{U}', 'Û'), (r'\^{u}', 'û'),
    (r'\^{W}', 'Ŵ'), (r'\^{w}', 'ŵ'),
    (r'\^{Y}', 'Ŷ'), (r'\^{y}', 'ŷ'),
    # tilde \~
    (r'\~{A}', 'Ã'), (r'\~{a}', 'ã'),
    (r'\~{N}', 'Ñ'), (r'\~{n}', 'ñ'),
    (r'\~{O}', 'Õ'), (r'\~{o}', 'õ'),
    (r'\~{U}', 'Ũ'), (r'\~{u}', 'ũ'),
    # cedilla \c
    (r'\c{C}', 'Ç'), (r'\c{c}', 'ç'),
    (r'\c{G}', 'Ģ'), (r'\c{g}', 'ģ'),
    (r'\c{K}', 'Ķ'), (r'\c{k}', 'ķ'),
    (r'\c{L}', 'Ļ'), (r'\c{l}', 'ļ'),
    (r'\c{N}', 'Ņ'), (r'\c{n}', 'ņ'),
    (r'\c{R}', 'Ŗ'), (r'\c{r}', 'ŗ'),
    (r'\c{S}', 'Ş'), (r'\c{s}', 'ş'),
    (r'\c{T}', 'Ţ'), (r'\c{t}', 'ţ'),
    # macron \=
    (r'\={A}', 'Ā'), (r'\={a}', 'ā'),
    (r'\={E}', 'Ē'), (r'\={e}', 'ē'),
    (r'\={I}', 'Ī'), (r'\={i}', 'ī'),
    (r'\={O}', 'Ō'), (r'\={o}', 'ō'),
    (r'\={U}', 'Ū'), (r'\={u}', 'ū'),
    # dot above \.
    (r'\.{C}', 'Ċ'), (r'\.{c}', 'ċ'),
    (r'\.{E}', 'Ė'), (r'\.{e}', 'ė'),
    (r'\.{G}', 'Ġ'), (r'\.{g}', 'ġ'),
    (r'\.{I}', 'İ'), (r'\.{i}', 'i'),
    (r'\.{O}', 'Ȯ'), (r'\.{o}', 'ȯ'),
    (r'\.{Z}', 'Ż'), (r'\.{z}', 'ż'),
    # dot below \d
    (r'\d{H}', 'Ḥ'), (r'\d{h}', 'ḥ'),
    (r'\d{L}', 'Ḷ'), (r'\d{l}', 'ḷ'),
    (r'\d{M}', 'Ṃ'), (r'\d{m}', 'ṃ'),
    (r'\d{N}', 'Ṇ'), (r'\d{n}', 'ṇ'),
    (r'\d{R}', 'Ṛ'), (r'\d{r}', 'ṛ'),
    (r'\d{S}', 'Ṣ'), (r'\d{s}', 'ṣ'),
    (r'\d{T}', 'Ṭ'), (r'\d{t}', 'ṭ'),
    # breve \u
    (r'\u{A}', 'Ă'), (r'\u{a}', 'ă'),
    (r'\u{E}', 'Ĕ'), (r'\u{e}', 'ĕ'),
    (r'\u{G}', 'Ğ'), (r'\u{g}', 'ğ'),
    (r'\u{I}', 'Ĭ'), (r'\u{i}', 'ĭ'),
    (r'\u{O}', 'Ŏ'), (r'\u{o}', 'ŏ'),
    (r'\u{U}', 'Ŭ'), (r'\u{u}', 'ŭ'),
    # caron \v
    (r'\v{C}', 'Č'), (r'\v{c}', 'č'),
    (r'\v{D}', 'Ď'), (r'\v{d}', 'ď'),
    (r'\v{E}', 'Ě'), (r'\v{e}', 'ě'),
    (r'\v{G}', 'Ǧ'), (r'\v{g}', 'ǧ'),
    (r'\v{L}', 'Ľ'), (r'\v{l}', 'ľ'),
    (r'\v{N}', 'Ň'), (r'\v{n}', 'ň'),
    (r'\v{R}', 'Ř'), (r'\v{r}', 'ř'),
    (r'\v{S}', 'Š'), (r'\v{s}', 'š'),
    (r'\v{T}', 'Ť'), (r'\v{t}', 'ť'),
    (r'\v{Z}', 'Ž'), (r'\v{z}', 'ž'),
    # double acute \H
    (r'\H{O}', 'Ő'), (r'\H{o}', 'ő'),
    (r'\H{U}', 'Ű'), (r'\H{u}', 'ű'),
    # ring above \r
    (r'\r{A}', 'Å'), (r'\r{a}', 'å'),
    (r'\r{U}', 'Ů'), (r'\r{u}', 'ů'),

    # -- Diacritics -- bare arg form (e.g. \"a -> ae) ----------------------
    # umlaut \"
    (r'\"A', 'Ä'), (r'\"a', 'ä'),
    (r'\"E', 'Ë'), (r'\"e', 'ë'),
    (r'\"I', 'Ï'), (r'\"i', 'ï'),
    (r'\"O', 'Ö'), (r'\"o', 'ö'),
    (r'\"U', 'Ü'), (r'\"u', 'ü'),
    (r'\"Y', 'Ÿ'), (r'\"y', 'ÿ'),
    # acute \'
    (r"\'A", 'Á'), (r"\'a", 'á'),
    (r"\'E", 'É'), (r"\'e", 'é'),
    (r"\'I", 'Í'), (r"\'i", 'í'),
    (r"\'O", 'Ó'), (r"\'o", 'ó'),
    (r"\'U", 'Ú'), (r"\'u", 'ú'),
    (r"\'Y", 'Ý'), (r"\'y", 'ý'),
    # grave \`
    (r'\`A', 'À'), (r'\`a', 'à'),
    (r'\`E', 'È'), (r'\`e', 'è'),
    (r'\`I', 'Ì'), (r'\`i', 'ì'),
    (r'\`O', 'Ò'), (r'\`o', 'ò'),
    (r'\`U', 'Ù'), (r'\`u', 'ù'),
    # circumflex \^
    (r'\^A', 'Â'), (r'\^a', 'â'),
    (r'\^E', 'Ê'), (r'\^e', 'ê'),
    (r'\^I', 'Î'), (r'\^i', 'î'),
    (r'\^O', 'Ô'), (r'\^o', 'ô'),
    (r'\^U', 'Û'), (r'\^u', 'û'),
    # tilde \~
    (r'\~A', 'Ã'), (r'\~a', 'ã'),
    (r'\~N', 'Ñ'), (r'\~n', 'ñ'),
    (r'\~O', 'Õ'), (r'\~o', 'õ'),

    # -- Remaining symbols -------------------------------------------------
    (r'\copyright', '©'),
    (r'\pounds',    '£'),
    (r'\euro',      '€'),
    (r'\cdot',      '·'),
    (r'\S',         '§'),
    (r'\P',         '¶'),

    # -- Spacing / invisible commands --------------------------------------
    (r'\ ',  ' '),  # explicit space -> non-breaking space
    (r'\,',  ' '),  # thin space -> narrow no-break space
    (r'\;',  ' '),
    (r'\:',  ' '),
    (r'\!',  ''),
    (r'\@',  ''),        # sentence-end hint
    (r'\/',  ''),        # italic correction
    (r'\-',  ''),        # discretionary hyphen

    # -- Square-bracket escapes --------------------------------------------
    ('{[}', '['),
    ('{]}', ']'),

    # -- Non-breaking space (tie) ------------------------------------------
    ('~', ' '),
]

# Alphabetic LaTeX commands (\l, \ss, \ldots, ...) must only match when NOT
# followed by a letter; otherwise \l corrupts \label, \ss corrupts \sshape.
# Non-alpha entries (\"a, ---, ~, {[}) use plain str.replace since their
# second character already delimits the match.
_ALPHA_CMD = re.compile(r'^\\[a-zA-Z]+$')
_COMPILED_SPECIALS: list = []
for _lat, _uni in _LATEX_SPECIALS:
    if _ALPHA_CMD.match(_lat):
        _COMPILED_SPECIALS.append((re.compile(re.escape(_lat) + r'(?![a-zA-Z])'), _uni))
    else:
        _COMPILED_SPECIALS.append((_lat, _uni))
del _lat, _uni

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
    text = _replace_cmd(text, r'\textbf', '<strong>', '</strong>')
    text = _replace_cmd(text, r'\textit', '<i>', '</i>')
    text = _replace_textcolor(text)

    for cmd, cls in _SPAN_COMMANDS:
        text = _replace_cmd(text, f'\\{cmd}', f'<span class="{cls}">', '</span>')
    text = _personname_to_html(text)
    text = _XLTABULAR.sub(lambda m: _xltabular_to_html(m.group(1)), text)
    text = text.replace('\\\\', '<br/>')

    for item, uni in _COMPILED_SPECIALS:
        if isinstance(item, str):
            text = text.replace(item, uni)
        else:
            text = item.sub(lambda _, u=uni: u, text)

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
            # Command is alone on its line -> remove the whole line
            out.append(text[prev:ls])
            prev = (le + 1) if le >= 0 else n
        else:
            # Command is inline -> remove only the command
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
