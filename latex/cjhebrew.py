"""
latex/cjhebrew.py – Convert cjhebrew ASCII encoding to Unicode Hebrew
=====================================================================

Handles two input forms:
  \\cjRL{k'rw}                    – plain command
  {\\larger[1]\\cjRL{k'rw}}      – grouped with font-size modifier

Both are converted to <span class="hebrew">Unicode</span>.

Encoding notes
--------------
Two-character sequences (/s, /S) are resolved before single characters.
Unknown characters are passed through unchanged so they appear visibly
in the output rather than being silently dropped.

Niqqud (vowel points) are included but marked as approximate – the
cjhebrew package documentation should be consulted if exact vowel
rendering is required.
"""

import re

# ------------------------------------------------------------------
# Encoding tables
# ------------------------------------------------------------------

# Must be tried before single-char to avoid /s being read as two chars
_TWO_CHAR: dict[str, str] = {
    '/s': 'שׁ',  # שׁ shin (with shin dot)
    '/S': 'שׂ',  # שׂ sin  (with sin dot)
}

_ONE_CHAR: dict[str, str] = {
    # Consonants
    "'": 'א',  # א alef
    'b': 'ב',  # ב bet
    'g': 'ג',  # ג gimel
    'd': 'ד',  # ד dalet
    'h': 'ה',  # ה he
    'w': 'ו',  # ו vav
    'z': 'ז',  # ז zayin
    'x': 'ח',  # ח het
    'T': 'ט',  # ט tet
    'y': 'י',  # י yod
    'k': 'כ',  # כ kaf
    'K': 'ך',  # ך final kaf
    'l': 'ל',  # ל lamed
    'm': 'מ',  # מ mem
    'M': 'ם',  # ם final mem
    'n': 'נ',  # נ nun
    'N': 'ן',  # ן final nun
    's': 'ס',  # ס samekh
    '(': 'ע',  # ע ayin
    'p': 'פ',  # פ pe
    'P': 'ף',  # ף final pe
    'c': 'צ',  # צ tsadi
    'C': 'ץ',  # ץ final tsadi
    'q': 'ק',  # ק qof
    'r': 'ר',  # ר resh
    't': 'ת',  # ת tav

    # Niqqud (vowel points) – approximate; verify against cjhebrew docs
    '*': 'ּ',  # ּ dagesh (dot inside preceding letter, e.g. כּ)
    ':': 'ְ',  # ְ sheva
    'A': 'ָ',  # ָ qamats
    'a': 'ַ',  # ַ patah
    'e': 'ֶ',  # ֶ segol
    'E': 'ֵ',  # ֵ tsere
    'i': 'ִ',  # ִ hiriq
    'o': 'ֹ',  # ֹ holam
    'u': 'ֻ',  # ֻ qibbuts
    'U': 'וּ', # וּ shuruk (vav + dagesh = long "u" vowel) / shuruk
}

# ------------------------------------------------------------------
# Regex patterns
# ------------------------------------------------------------------

# {\larger[n]\cjRL{...}}  – grouped with optional font-size modifier
_GROUPED = re.compile(r'\{\\larger\[\d+\]\\cjRL\{([^}]*)\}\}')

# \cjRL{...}  – plain command
_PLAIN = re.compile(r'\\cjRL\{([^}]*)\}')

# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def convert_cjhebrew(text: str) -> str:
    """Replace cjhebrew expressions with <span class="hebrew"> Unicode.</span>"""
    text = _GROUPED.sub(lambda m: _wrap(_decode(m.group(1))), text)
    text = _PLAIN.sub(  lambda m: _wrap(_decode(m.group(1))), text)
    return text

# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _wrap(hebrew: str) -> str:
    return f'<span class="hebrew">{hebrew}</span>'


def _decode(encoded: str) -> str:
    """Translate cjhebrew ASCII token sequence to Unicode Hebrew characters."""
    result = []
    i = 0
    while i < len(encoded):
        two = encoded[i:i + 2]
        if two in _TWO_CHAR:
            result.append(_TWO_CHAR[two])
            i += 2
        elif encoded[i] in _ONE_CHAR:
            result.append(_ONE_CHAR[encoded[i]])
            i += 1
        else:
            result.append(encoded[i])  # pass through unchanged
            i += 1
    return ''.join(result)
