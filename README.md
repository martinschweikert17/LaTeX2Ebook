# LaTeX2Ebook

Converts a LaTeX document to EPUB or HTML. Designed for book-length documents with chapters, footnotes, Bible references, Hebrew and Greek text, and multilingual support.

## Requirements

- Python 3.11+
- [ebooklib](https://github.com/aerkalov/ebooklib): `pip install ebooklib`

## Usage

```
python main.py --config <file.ini> [options]
```

The INI file is required. All other parameters are optional and override the INI.

| Option | Description |
|---|---|
| `--config FILE` | INI configuration file (required) |
| `--target epub\|html` | Output format (default: epub) |
| `--language LANG` | Document language, e.g. `DE` or `EN` |
| `--output-directory DIR` | Output directory (default: `<input-directory>/L2E`) |
| `--debug` | Write intermediate files to output directory |
| `--log-level LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `--biblerefstyle STYLE` | Bible reference style (see below) |
| `--biblerefformat FORMAT` | `kurz` (short) or `lang` (long) book names |

## INI File

```ini
[PATHS]
InputDirectory = ~/texte/mybook
InputFile      = mybook.tex
BibFile        = ~/texmf/bibtex/bib/literatur.bib
Translations   = ~/texmf/tex/latex/bibel/übersetzungen.tex

[GENERAL]
Language = DE          # DE | EN (and any other language with a LANG_XX section)
Target   = epub        # epub | html

[EBOOK]
SZMode          = normal      # normal | aggressive | radical  (German ß handling)
YHWH            = Jahwe       # Jahwe | JHWH | HERR | hebrew
BibleRefStyle   = LThK        # LThK | Lutherbibel | Einheitsuebersetzung | jerusalem
BibleRefFormat  = kurz        # kurz | lang
GreekFontSize   = 1.05em
HebrewFontSize  = 1.2em
VerseEmphasis   = font-weight: bold;
Transliteration = font-style: italic;
PersonNameFormat = text-transform: uppercase; font-size: 85%;
SmallCaps        = text-transform: uppercase; font-size: 85%;
FullRefTitle     = font-style: italic;
LongVersionName  = font-style: italic;

# Heading numbering: arabic | roman_upper | roman_lower | alpha_upper | alpha_lower | none
NumberingPart          = roman_upper
NumberingChapter       = arabic
NumberingSection       = arabic
NumberingSubsection    = arabic
NumberingSubsubsection = arabic
NumberingAppendices    = alpha_upper

[LANG_DE]
Title       = Mein Buch
Subtitle    = Ein Untertitel
Author      = Vorname Nachname
Year        = 2026
Description = Kurze Beschreibung für Suchmaschinen
Keywords    = Stichwort1, Stichwort2

[LANG_EN]
Title    = My Book
...

[LOGGING]
LogLevel = INFO
LogFile  = /tmp/latex2ebook.log   # optional; default: stdout only
```

Configuration priority (low → high): built-in defaults → INI file → command line.

## LaTeX Source Conventions

### Frontmatter Variables (`\fm*`)

Define metadata with `\newcommand` in the LaTeX preamble. These are used in the generated HTML/EPUB and in CSS class names.

| Command | Purpose |
|---|---|
| `\fmtitle` | Book title |
| `\fmsubtitle` | Subtitle |
| `\fmauthor` | Author |
| `\fmyear` | Publication year |
| `\fmcopyright` | Copyright line |
| `\fmlegalblurb` | Legal notice |
| `\fmebookblurb` | Ebook-specific note |
| `\fmcontact` | Contact information |
| `\fmtypesetting` | Typesetting credit |
| `\fmdedication` | Dedication |
| `\fmtableofcontent` | TOC heading |
| `\fmfooter` | Footer text (HTML only); lines separated by `\\` |
| `\fmkeywords` | Keywords for EPUB/HTML metadata |
| `\fmeditor` | Publisher (EPUB metadata „Verlag") |
| `\fmpublisher` | Publisher override (takes precedence over `\fmeditor`; fallback: `Selbstverlag`) |
| `\fmXXXcss` | CSS override for the `p.fmXXX` class |

Multilingual definitions use `\ifbool{LANG_DE}{...}%LANG_DE` / `\ifbool{LANG_EN}{...}%LANG_EN`.

### Target-Specific Frontmatter

The frontmatter (title page, copyright page, dedication) is defined in a separate file per target:

```latex
\onlyforltoe{\input{frontmatter}}
```

LaTeX2Ebook replaces `\input{frontmatter}` with the contents of `frontmatter_epub.tex` or `frontmatter_html.tex` depending on the active target. An error is raised if the file does not exist.

Inside these files, use `\fmXXX` commands directly. They are rendered as `<p class="fmXXX">value</p>`, which picks up the CSS defined for that class.

### Content Markers

| Marker | Purpose |
|---|---|
| `%%%L2E_TABLE_OF_CONTENT` | Replaced by the generated TOC |
| `%%%L2E_FOOTNOTES_SECTION_BEGIN` … `%%%L2E_FOOTNOTES_SECTION_END` | Contains the footnote section (removed in EPUB, kept in HTML) |
| `%%%L2E_LITERATURE_SECTION_BEGIN` … `%%%L2E_LITERATURE_SECTION_END` | Contains the bibliography section |
| `%%%L2E_SKIP_BEGIN` … `%%%L2E_SKIP_END` | Block skipped entirely by LaTeX2Ebook |

### Visibility Commands

| Command | Effect in LaTeX | Effect in LaTeX2Ebook |
|---|---|---|
| `\hidefromltoe{...}` | Shows content | Content removed |
| `\onlyforltoe{...}` | No-op | Content kept |

### Page Layout

| LaTeX | HTML/EPUB output |
|---|---|
| `\newpage` | `<div class="pagebreak">` (CSS page break) |
| `\hrule` | `<hr/>` |
| `\bigskip`, `\medskip` | `<br/>` |

### Footnotes

- `\footnote{...}` — standard footnote; rendered inline as superscript link in EPUB, collected at `%%%L2E_FOOTNOTES` in HTML.
- `\pfootnote{...}` — compact footnote (no vertical gap between consecutive entries).

In EPUB mode, `\enquote{}` inside footnotes resets the quotation depth to 0.

### Quotation Marks

`\enquote{...}` is replaced with typographic quotation marks, nested:
- Outer: „ … "
- Inner: ‚ … '

### Bible References

Formatted via `\ibibleverse`, `\ibiblechvs` etc. Style and format are configured via `BibleRefStyle` / `BibleRefFormat`.

### Hebrew and Greek

| Command | Renders as |
|---|---|
| `\cjRL{...}` | Hebrew text (right-to-left, sized via `HebrewFontSize`) |
| `\quotehebrew{word}{transliteration}{longform}` | Hebrew word with transliteration |
| Greek text | Sized via `GreekFontSize` |

### Special Characters

| LaTeX | Output |
|---|---|
| `---` | — (em dash) |
| `--` | – (en dash) |
| `\ldots` | … |
| `~` | (non-breaking space → regular space) |
| `{\sz}` | ß (or ss, depending on SZMode) |
| `{\szquoted}` | ß (or ss, depending on SZMode) |
| `\LaTeX` | L<sup>a</sup>T<sub>e</sub>X (styled via `.latex` CSS class) |
| `\S` | § |
| `\copyright` | © |

## Pipeline

```
.tex file
  └─ _inline_frontmatter()        replace \input{frontmatter} with target-specific file
  └─ deflate()                    remove \ifbool{LANG_XX} blocks for inactive languages,
  │                               process %%%L2E_SKIP_BEGIN/END blocks
  └─ decomment()                  remove LaTeX comments (% lines)
  └─ expand_newcommands()         collect and expand \newcommand definitions
  └─ apply_personal_commands()    expand YHWH and other personal settings
  └─ convert_bibleref()           format Bible references
  └─ convert_expressions()        replace LaTeX expressions with HTML equivalents
  └─ apply_formatting()           \textbf → <strong>, \textit → <i>, tables, lists, …
  └─ convert_headings()           \chapter, \section, … → <h1>, <h2>, …
  └─ process_footnotes()          inline footnotes (EPUB) or collect at marker (HTML)
  └─ process_toc()                replace %%%L2E_TABLE_OF_CONTENT with <nav>
  └─ process_refs()               resolve \label / \ref cross-references
  └─ process_literature()         render \citetitle bibliography entries
  └─ build_paragraphs()           wrap text blocks in <p>…</p>
       │
       └─ HtmlConverter           write .html to output directory
            └─ EbookBuilder       package .html + epub.css into .epub
```

## Output

All output is written to `<input-directory>/L2E/` (or the configured `OutputDirectory`).

| File | Description |
|---|---|
| `<name>_<LANG>.html` | Intermediate HTML (always written) |
| `<name>_<LANG>.epub` | Final EPUB (target=epub only) |

With `--debug`, additional intermediate files are written: `deflated.txt`, `comments_pre.txt`, `comments_post.txt`, `expressions.txt`.
