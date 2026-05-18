# Engine: WeasyPrint

Converts Markdown to PDF using [WeasyPrint](https://weasyprint.org/) — CSS Paged Media renderer.  
Use via `md2pdf --engine weasyprint`; Typst is the default engine.

## Dependencies

```bash
conda activate python_313x
conda install markdown weasyprint pygments
brew install pango gdk-pixbuf libffi   # macOS system deps
```

## Styles

| Style | File | Description |
|-------|------|-------------|
| `intelligence` | `styles/style_intelligence.css` | US IC-style, two-column, navy/gold |
| `magazine` | `styles/style_magazine.css` | Two-column magazine, copper accent |
| `thinktank` | `styles/style_thinktank.css` | Single-column, Source Serif 4 |
| `academic` | `styles/style_academic.css` | Single-column, EB Garamond |

## Usage via dispatcher

```bash
md2pdf article.md --engine weasyprint
md2pdf article.md --engine weasyprint --css intelligence
md2pdf article.md --engine weasyprint --css magazine --custom overrides.css
```

## Usage direct

```bash
python engines/weasyprint/convert.py article.md --css intelligence
python engines/weasyprint/convert.py article.md --css magazine --custom overrides.css
```

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--css` | `intelligence` | Style name or path to CSS file |
| `--custom` | none | Additional CSS override file |
| `--output` | same stem, `.pdf` | Output PDF path |
| `--list-styles` | — | Print available styles and exit |

## Special div classes

```html
<!-- Full-width block (spans both columns) — use for tables/images -->
<div class="full-width"> ... </div>

<!-- Single-column section (annexes, notes) -->
<div class="single-column"> ... </div>

<!-- Key findings box -->
<div class="key-takeaways"> ... </div>

<!-- Explicit page break -->
<div class="page-break"></div>
```

## Known limitations

- `column-span: all` on elements taller than one page triggers a WeasyPrint assertion.
  The pipeline auto-mitigates by marking oversized elements `no-span`.
- Markdown syntax inside raw HTML divs is pre-processed automatically.
- Mermaid requires `mmdc` (`npm install -g @mermaid-js/mermaid-cli`).
