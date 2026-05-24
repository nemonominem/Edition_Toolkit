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
| `# H1` … `###### H6` | `=` … `======` (all heading levels always left-aligned, regardless of column context) |
| `**bold**`, `*italic*` | `*bold*`, `_italic_` |
| `` `code` `` | `` `code` `` |
| `[text](url)` | `#link("url")[text]` |
| `![alt](src){width=60%}` | `#figure(image(...), caption: [...])` |
| `[^key]` footnotes | `#footnote[...]` inline (see caveat below) |
| Pipe tables | `#table(...)` navy header, stripe rows, full-width |
| ` ```mermaid ``` ` | pre-rendered PNG if available, else placeholder |
| Bullet lists, numbered lists | always ragged-right (not justified) — standard for lists and avoids ugly spacing on URL-heavy items such as Further Reading |
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

Use `<br>` for explicit line breaks inside a callout block — a bare newline
inside a `>` block is treated as a paragraph continuation:

```markdown
> [!NOTE]
> First line.<br>
> Second line.<br>
> Third line.
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

### Table column widths

By default, all table columns share equal width (`1fr` each).  For **2-column
tables** the converter automatically applies a `0.28fr / 1fr` split (roughly
22% / 78%), which suits label-plus-content layouts (actor/role, key/value,
comparison tables).

For **3- or 4-column tables** all columns remain equal.  If you need a
different split — e.g. a wide first column or a narrow index column — wrap
the table in a `<div class="single-column">` and note the desired widths in a
comment above it so the next editor knows what to adjust in `convert.py`:

```html
<!-- table-col-widths: 0.5fr 1fr 1fr -->
<div class="single-column">

| Col A | Col B | Col C |
| ----- | ----- | ----- |
| …     | …     | …     |

</div>
```

*(Custom per-table width injection is not yet implemented; the comment is a
human reminder for now.)*

### Footnote reference collision with URLs

If a footnote key appears immediately before `:` elsewhere in the text — for
example inside a URL like `https://example.com/path[^ref]:more` or in a
sentence ending `…as shown[^ref]:` — the converter's footnote-definition
regex may consume it as a definition line, stripping the reference from the
output.

**Workaround:** add a space before the colon in the *reference* (not the
definition): write `[^someref] :` instead of `[^someref]:` anywhere in the
main body or notes text other than the actual `[^someref]: definition` line.
The definition line itself must keep the colon flush.

---

## Known Limitations

### No two-column flow above a full-width table on the same page

Typst's multi-column model is grid-based: you are either inside a column flow
or outside it.  There is no mechanism to run two columns for the upper half of
a page and then place a full-width block on the lower half of the same page.

**Consequence:** when a bare table (or any `single-column` / `full-width`
block) appears in the middle of a two-column section, Typst flushes the open
columns and starts the full-width block on a fresh baseline.  This produces a
visible gap — unused white space at the bottom of one column before the table.

**Workarounds:**

1. **Wrap the lead-in paragraph and the table together in `single-column`.**
   The prose runs full-width immediately above the table — no gap.  This is
   the recommended fix when the lead-in is short (one or two sentences).

2. **Insert a `page-break` before the table.**  The gap moves to the bottom of
   the previous page, which is less noticeable.  Use this when the table is
   large enough to fill most of a new page on its own.

3. **Accept the gap.**  For tables that land near the bottom of a page the
   gap is often small and unremarkable.
