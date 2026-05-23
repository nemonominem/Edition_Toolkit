# Engine: Typst

Converts Markdown to PDF using [Typst](https://typst.app/) — fast, modern typesetting.  
This is the **default engine** for `md2pdf`.

## Dependencies

- `typst` binary: `brew install typst`
- Python 3.9+ stdlib only — no pip packages needed

## Styles

| Style | File | Description |
|-------|------|-------------|
| `intelligence` | `styles/intelligence.typ` | US IC-style two-column, serif, navy/gold palette |

## Usage via dispatcher (recommended)

```bash
md2pdf article.md                          # typst is the default
md2pdf article.md --style intelligence --compile
md2pdf article.md --no-justify
```

## Usage direct

```bash
python engines/typst/convert.py article.md --style intelligence --compile
```

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--style` | `intelligence` | Style name (must exist in `styles/`) |
| `--output` | same stem, `.typ` | Output path |
| `--compile` | off | Run `typst compile` to produce PDF |
| `--no-justify` | off | Ragged-right text |
| `--list-styles` | — | Print available styles and exit |

## Adding a style

Create `styles/your-style.typ` implementing `doc(author, title, pub-name, doc-type, justify, body)`
and the helpers `key-takeaways`, `insights-box`, `pull-quote`, `callout`, `callout-note`,
`callout-warning`, `mermaid-placeholder`. See `styles/intelligence.typ` for a complete example.

## Markdown conventions

| Syntax | Typst output |
|--------|-------------|
| `# H1` … `###### H6` | `=` … `======` (h1 always full-width) |
| `**bold**`, `*italic*` | `*bold*`, `_italic_` |
| `` `code` `` | `` `code` `` |
| `[text](url)` | `#link("url")[text]` |
| `![alt](src){width=60%}` | `#figure(image(...), caption: [...])` |
| `[^key]` footnotes | `#footnote[...]` inline |
| Pipe tables | `#table(...)` navy header, stripe rows, full-width |
| ` ```mermaid ``` ` | pre-rendered PNG if available, else placeholder |
| `<div class="page-break">` | `#pagebreak()` |
| `<div class="key-takeaways">` | Blue callout box with "Key Takeaways" label + rule |
| `<div class="insights">` | Cream sidebar box, gold borders |
| `<div class="single-column">` / `<div class="full-width">` | Full-width block (breaks out of two-column) |
| `\| pull-quote` | `#pull-quote[...]` |
| `> [!NOTE]` / `> [!WARNING]` | `#callout[...]` |
| `---` | `#line(...)` |

## Tweaking layout in the Markdown

These are the common manual adjustments you will make directly in the `.md` file
before conversion. All use standard HTML `<div>` wrappers that the converter
recognises by `class` name.

### Force a section to one column (full page width)

Use `single-column` for any content that should span the full page — introductory
notes, annexes, wide diagrams, the Further Reading section, etc.

```html
<div class="single-column">

Your content here — headings, paragraphs, lists, images.

</div>
```

`full-width` is an alias; use it for individual wide tables or figures inside
an otherwise two-column flow.

### Start a new page

```html
<div class="page-break"></div>
```

Combine with `single-column` for sections that must both break to a new page
and run full-width (e.g. Notes, Further Reading, each Annex):

```html
<div class="page-break"></div>

<div class="single-column">

## Further Reading

…

</div>
```

For annexes that stay two-column, the page-break alone is enough:

```html
<div class="page-break"></div>

## Annex 1 — Title

…
```

### Highlighted boxes

**Key Takeaways** — navy label, blue tint, gold rule:

```html
<div class="key-takeaways">

Scope Note: *Optional one-line framing sentence.*

- Point one
- Point two

</div>
```

**Insights / Key Insights** — cream box, gold borders. Optional heading:

```html
<div class="insights">

### Box heading

Body text here.

</div>
```

### Callouts (GFM alert syntax)

```markdown
> [!NOTE]
> Text of the note.

> [!WARNING]
> Text of the warning.
```

### Pull-quotes

```markdown
| This is the pull-quote text — pipe-prefixed, no closing pipe.
| source: Author Name
```

### Mermaid diagrams

Diagrams render as PNGs if `mmdc` (mermaid-cli) is on PATH:

```bash
npm install -g @mermaid-js/mermaid-cli
```

Without it, a placeholder is emitted. Mermaid sections inside `single-column`
divs render at full page width — recommended for network graphs and flow charts.
