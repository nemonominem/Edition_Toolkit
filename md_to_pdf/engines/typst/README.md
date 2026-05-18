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
| `<div class="single-column">` / `<div class="full-width">` | Full-width block |
| `\| pull-quote` | `#pull-quote[...]` |
| `> [!NOTE]` / `> [!WARNING]` | `#callout[...]` |
| `---` | `#line(...)` |
