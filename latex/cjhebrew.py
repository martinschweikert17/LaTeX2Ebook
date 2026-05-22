"""
latex/cjhebrew.py – Convert cjhebrew ASCII encoding to Unicode Hebrew
=====================================================================

Handles two input forms:
  \\cjRL{k'rw}                    – plain command
  {\\larger[1]\\cjRL{k'rw}}      – grouped with font-size modifier

Both are converted to <span class="hebrew">Unicode</span>.

Encoding notes
--------------
Two-character sequences (.h, .t, .s, .S, /s, /S, +s, ,s, wo, w*, hataf)
are resolved before single characters.

Bare / (not followed by s or S) is a patah-furtivum marker: the vowel
that follows belongs to the next consonant, so they are emitted in
swapped order (consonant first, then vowel).

Unknown characters are passed through unchanged.
"""

import re

# ------------------------------------------------------------------
# Encoding tables
# ------------------------------------------------------------------

# Must be tried before single-char to avoid multi-char sequences being split.
_TWO_CHAR: dict[str, str] = {
    # Consonants (dot-prefix = emphatic)
    '.h': 'ח',   # ח het
    '.t': 'ט',   # ט tet
    '.s': 'צ',   # צ tsadi (non-final)
    '.S': 'ץ',   # ץ tsadi (final)
    '/s': 'שׁ',  # שׁ shin (with shin dot)   – original convention
    '/S': 'שׂ',  # שׂ sin  (with sin dot)    – original convention
    '+s': 'שׁ',  # שׁ shin (with shin dot)   – BuZ.tex convention
    ',s': 'שׂ',  # שׂ sin  (with sin dot)    – BuZ.tex convention
    # Punctuation
    '--': '־',   # ־ maqqef
    # Long vowels with vav (alternatives to O / U)
    'wo': 'וֹ',  # וֹ holam-male (vav + holam)
    'w*': 'וּ',  # וּ shuruk (vav + dagesh)
    # Hataf (reduced) vowels
    'E:': 'ֱ',   # ֱ hataf-segol
    'a:': 'ֲ',   # ֲ hataf-patah
    'A:': 'ֳ',   # ֳ hataf-qamets
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
    '(': 'ע',  # ע ayin (alternative)
    '`': 'ע',  # ע ayin (backtick – BuZ.tex convention)
    'p': 'פ',  # פ pe
    'P': 'ף',  # ף final pe
    'c': 'צ',  # צ tsadi
    'C': 'ץ',  # ץ final tsadi
    'q': 'ק',  # ק qof
    'r': 'ר',  # ר resh
    'S': 'שׁ',  # שׁ shin (uppercase shorthand)
    't': 'ת',  # ת tav

    # Niqqud (vowel points)
    '*': 'ּ',   # ּ dagesh
    ';': 'ֽ',   # ֽ meteg (secondary stress)
    ':': 'ְ',   # ְ sheva
    'A': 'ָ',   # ָ qamets
    'a': 'ַ',   # ַ patah
    'e': 'ֶ',   # ֶ segol
    'E': 'ֵ',   # ֵ tsere
    'i': 'ִ',   # ִ hiriq
    'o': 'ֹ',   # ֹ holam
    'O': 'וֹ',  # וֹ holam-male (vav + holam)
    'u': 'ֻ',   # ֻ qibbuts
    'U': 'וּ',  # וּ shuruk (vav + dagesh)
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
    n = len(encoded)
    while i < n:
        two = encoded[i:i + 2]
        if two in _TWO_CHAR:
            result.append(_TWO_CHAR[two])
            i += 2
        elif encoded[i] == '/':
            # Bare / (not /s or /S): patah-furtivum marker.
            # The vowel that follows belongs to the consonant after it,
            # so emit: consonant first, then vowel.
            i += 1
            if i >= n:
                break
            # Decode the vowel
            two = encoded[i:i + 2]
            if two in _TWO_CHAR:
                vowel = _TWO_CHAR[two]; i += 2
            elif encoded[i] in _ONE_CHAR:
                vowel = _ONE_CHAR[encoded[i]]; i += 1
            else:
                continue  # unrecognised char after /, skip
            # Decode the consonant
            if i >= n:
                result.append(vowel); break
            two = encoded[i:i + 2]
            if two in _TWO_CHAR:
                consonant = _TWO_CHAR[two]; i += 2
            elif encoded[i] in _ONE_CHAR:
                consonant = _ONE_CHAR[encoded[i]]; i += 1
            else:
                result.append(vowel); continue
            result.append(consonant)
            result.append(vowel)
        elif encoded[i] in _ONE_CHAR:
            result.append(_ONE_CHAR[encoded[i]])
            i += 1
        else:
            result.append(encoded[i])  # pass through unchanged
            i += 1
    return ''.join(result)
