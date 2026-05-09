# produce_pdf

Converts a Markdown article to a print-ready PDF using WeasyPrint.

## Files

| File | Purpose |
|---|---|
| `md_to_pdf.py` | Conversion script — run this |
| `style.css` | All typography, layout, and page rules — edit this to change appearance |

---

## One-time setup

```bash
# 1. Activate conda environment
conda activate python_313x

# 2. Python dependencies (WeasyPrint + Markdown parser)
conda install markdown weasyprint pygments

# 3. WeasyPrint system libraries (macOS)
brew install pango gdk-pixbuf libffi

# 4. Mermaid diagram renderer (optional — diagrams show as placeholders without it)
brew install node
npm install -g @mermaid-js/mermaid-cli
```

---

## Running a conversion

Activate the conda environment first, then run from anywhere — paths are resolved automatically.

```bash
# Activate environment
conda activate python_313x

# Outputs mytext.pdf next to the .md file
python md_to_pdf.py somemd.md

# Explicit output path
python md_to_pdf.py somemd.md output/draft.pdf

# Force a specific engine
python md_to_pdf.py somemd.md --engine weasyprint
```

---

## What the script handles

| Feature | How |
|---|---|
| Headings, paragraphs, lists | Standard Markdown |
| **Bold**, *italic*, `code` | Standard Markdown |
| Footnotes (`[^key]`) | python-markdown `footnotes` extension — rendered at end of document |
| Tables (`\| col \| col \|`) | python-markdown `tables` extension |
| Fenced code blocks (` ``` `) | python-markdown `fenced_code` + optional syntax highlighting via Pygments |
| Inline HTML (`<img>`, `<div>`, `<small>`) | Passed through as-is |
| Images (`<img src="...">`) | Relative paths rewritten to `file://` URIs so WeasyPrint finds them |
| Image sizing | Set `width="40%"` in the `<img>` tag; fine-tune per-image in `style.css` using `img[src*="filename"]` selectors |
| Mermaid diagrams (` ```mermaid `) | Rendered to PNG via `mmdc` if installed; otherwise a labelled placeholder box |
| `<div class="glossary-box">` | Styled aside box (grey left border, smaller italic text) |
| Page breaks before Annexes | Injected automatically before `## Annex N`, `## Notes`, `## Further Reading` |
| Footer (author / page n∕m / title) | CSS `@page` margin boxes — edit in `style.css` |
| No footer on page 1 | `@page :first` rule in `style.css` |
| Long URL wrapping | `word-break: break-all` on `<a>` tags |
| Orphan/widow control | `orphans: 3; widows: 3` on `<p>` |

**Not supported by WeasyPrint** (CSS Paged Media, not a browser):
- JavaScript
- CSS `position: fixed`
- CSS Grid (partial support only)
- Video or audio embeds

---

## Configuring style.css

`style.css` is structured as a settings file. The top of the file contains a
reference block listing every tuneable variable with its current value and
what it controls. The implementation rules below that block are annotated with
the variable name they correspond to, so you can find any rule quickly.

### Quick-reference: what you can change

| Variable | Default | Controls |
|---|---|---|
| `FONT_BODY` | Source Serif 4, Georgia | Body, headings, footer |
| `FONT_MONO` | Source Code Pro, Courier New | Inline code, code blocks |
| `SIZE_BODY` | 10pt | Base size — all others scale from this |
| `SIZE_H1–H4` | 18 / 14 / 11.5 / 10pt | Heading levels |
| `SIZE_SMALL` | 8.5pt | Footnotes, captions, footer, code |
| `SIZE_TABLE` | 9pt | Table body text |
| `SIZE_FOOTER` | 8.5pt | Footer left/centre/right |
| `COLOR_BODY` | #1a1a1a | Main text |
| `COLOR_LINK` | #1a5276 | Hyperlinks |
| `COLOR_FAINT` | #666 | Footer, footnotes, attribution lines |
| `PAGE_SIZE` | A4 | Change to `Letter` for US letter |
| `MARGIN_*` | 2.5–2.8cm | Page margins (extra bottom for footer) |
| `FOOTER_LEFT` | "G. Demaneuf" | Left footer slot |
| `FOOTER_CENTER` | p. n / m | Centre footer slot |
| `FOOTER_RIGHT` | article title | Right footer slot |
| `LINE_HEIGHT` | 1.6 | Body line spacing |
| `PARA_SPACING` | 0.75em | Space below paragraphs |

### Fonts

```css
/* Web font (requires internet at render time) */
@import url('https://fonts.googleapis.com/css2?family=...');

body { font-family: 'Your Font', Georgia, serif; }
code { font-family: 'Your Mono Font', 'Courier New', monospace; }
```

For fully offline rendering, remove the `@import` and use locally installed
font names such as `Georgia`, `"Palatino Linotype"`, or `"Times New Roman"`.

### Font sizes

```css
body { font-size: 10pt; }    /* SIZE_BODY — change this first */
h1   { font-size: 18pt; }    /* SIZE_H1 */
h2   { font-size: 14pt; }    /* SIZE_H2 */
h3   { font-size: 11.5pt; }  /* SIZE_H3 */
```

### Page size and margins

```css
@page {
    size: A4;                              /* or: Letter */
    margin: 2.5cm 2.8cm 2.8cm 2.8cm;      /* top right bottom left */
}
```

### Footer

```css
@bottom-left   { content: "Author Name"; }
@bottom-center { content: "p. " counter(page) " / " counter(pages); }
@bottom-right  { content: "Article Title"; }
```

Use `\2018` / `\2019` for curly single quotes (' '). Set any slot to
`content: none` to suppress it. The `@page :first` block already suppresses
all three slots on page 1.

### Per-image size control

Use a CSS attribute selector on a substring of the filename — no need to touch
the source Markdown:

```css
img[src*="houssin"]      { max-width: 42%; margin-left: 0; }
img[src*="wide-figure"]  { max-width: 85%; }
img[src*="small-inset"]  { max-width: 35%; float: right; margin-left: 1em; }
```

### Callout box colours

Each callout type has its own border and background colour:

```css
div.callout-note      { border-color: #6c9fc2; background: #f0f6fb; }
div.callout-warning   { border-color: #c2a040; background: #fdf8ee; }
/* etc. */
```

### Page breaks

The script automatically inserts a page break before `## Annex N`,
`## Notes`, and `## Further Reading`. To force a break before any other
heading, add this immediately before it in the Markdown:

```html
<div class="annex-break"></div>

## My Section
```

### Override without editing style.css

Pass a second CSS file with `--css`. It is loaded after `style.css` so you
only need to include the rules you want to change:

```bash
conda run -n python_313x python produce_pdf/md_to_pdf.py article.md --css overrides.css
```

---

## Pandoc fallback

If WeasyPrint is unavailable, the script falls back to pandoc + wkhtmltopdf.
This path does not support CSS Paged Media (no footer, no per-image CSS selectors).
Install if needed:

```bash
conda activate python_313x

conda install pandoc
brew install --cask wkhtmltopdf
```
