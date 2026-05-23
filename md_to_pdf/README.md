# etk-md2pdf

Markdown → PDF converter for the Edition ToolKit.  
Two rendering engines, one command.

> **Pre-requisite:** Run `md_harden` on your Markdown file before passing it here.
> `md2pdf` assumes clean, hardened input — it applies no heuristic pre-passes.

## Engines

| Engine | Default | Technology | Best for |
|--------|---------|------------|----------|
| `typst` | ✓ | [Typst](https://typst.app/) | All new work — fast, precise, no crashes |
| `weasyprint` | | [WeasyPrint](https://weasyprint.org/) | CSS-based legacy workflow |

## Installation

```bash
conda activate python_313x

# Install the package (puts md2pdf on PATH)
conda develop .

# Typst engine (default) — install the typst binary
brew install typst

# WeasyPrint engine (optional)
conda install markdown weasyprint pygments
brew install pango gdk-pixbuf libffi
```

## Typical workflow

A complete article goes through three steps: harden, customise, convert.

### Step 1 — Harden the Markdown

```bash
# Generate a review file listing all suggested fixes
python md_harden/md_harden.py article.md --review --claude --style intelligence

# Edit article_review.md — delete any suggestion you disagree with
# Then apply what remains
python md_harden/md_harden.py article.md \
       --style intelligence --apply article_review.md
```

### Step 2 — Create the per-article sidecar

Create `article.json` alongside `article.md`.  It is auto-detected — no flag required.

```json
{
  "author":   "G. Demaneuf",
  "title":    "My Article Title",
  "pub_name": "DRASTIC",
  "doc_type": "OSINT RESEARCH PRODUCT",

  "typst_overrides": {
    "body_size":    "9.5pt",
    "body_leading": "0.65em",
    "body_spacing": "1.4em",
    "h1_size": "16pt",
    "h2_size": "11pt",
    "h3_size": "10.5pt"
  }
}
```

`typst_overrides` is Typst-only (WeasyPrint ignores it).  All keys are optional — omit any you don't want to change.  See `tests/shared/test_columns.json` for the full list of supported keys with their intelligence-style defaults.

For WeasyPrint visual tweaks, create a companion CSS file (see Step 3b).

### Step 3a — Convert with Typst (recommended for complex pieces)

```bash
# Sidecar auto-detected; --compile produces the PDF directly
md2pdf article.md --style intelligence --compile
```

Typst is faster, more layout-stable, and handles long documents without crashing.  Use it by default.

### Step 3b — Convert with WeasyPrint

```bash
md2pdf article.md --engine weasyprint --css intelligence \
       --custom article_overrides.css
```

The `--custom` CSS file handles WeasyPrint visual tweaks.  Typical contents:

```css
/* Body font and size */
body { font-family: 'Source Serif 4', Georgia, serif; font-size: 9pt; }

/* Paragraph spacing */
body, p, li { line-height: 1.5; }
p { margin-bottom: 0.4em; }

/* Heading alignment */
h1 { text-align: center; }
h2, h3 { text-align: justify; }

/* Accent colour */
h2, h3 { color: #8b0000; }
div.full-width, div.single-column { border-top-color: #8b0000; }
```

See `tests/weasyprint/test_columns_overrides.css` for a fully annotated template.

---

## Style configuration

Each style has a shared JSON definition in `styles/`:

```
styles/
├── intelligence.json   US IC report — 2-col, navy/gold, source: attribution
├── academic.json       Academic paper — 1-col, serif, Source: attribution
├── magazine.json       Magazine feature — 1-col, rust accent, source: attribution
└── thinktank.json      Policy brief — 2-col, green accent, Source: attribution
```

These files are the **single source of truth** for per-style conventions shared across the pipeline:

- `md_harden --style <name>` reads the `hardening` object (pull-quote attribution style, confidence thresholds, et al. italics, etc.)
- `md2pdf` reads `design.branding_defaults` as the baseline for author, title, pub_name, doc_type — overridden by sidecar JSON, then by YAML frontmatter.
- The `.typ` and `.css` engine files implement `design`; update JSON first when a convention changes.

## Metadata precedence

```
style branding_defaults  (styles/<name>.json)
  ↓  sidecar JSON        (<stem>.json alongside .md)
     ↓  YAML frontmatter (--- block at top of .md)
```

Use `--meta path/to/file.json` to point at a sidecar at a non-default path.

## Structure

```
md_to_pdf/
├── pyproject.toml
├── README.md
├── styles/                     Shared per-style JSON (spec + hardening config)
│   ├── intelligence.json
│   ├── academic.json
│   ├── magazine.json
│   └── thinktank.json
├── etk_md2pdf/
│   ├── __init__.py
│   └── dispatcher.py           md2pdf entry point — parses --engine, delegates
├── engines/
│   ├── __init__.py             Shared: parse_frontmatter, load_sidecar,
│   │                           load_typst_overrides, load_style_defaults
│   ├── typst/
│   │   ├── convert.py
│   │   ├── styles/             intelligence.typ, magazine.typ, thinktank.typ, academic.typ
│   │   └── README.md
│   └── weasyprint/
│       ├── convert.py
│       ├── styles/             style_intelligence.css, style_magazine.css, …
│       └── README.md
└── tests/
    ├── shared/                 Engine-agnostic inputs (see shared/README.md)
    │   ├── test_columns/       Public test article
    │   │   ├── test_columns.md
    │   │   ├── test_columns.json   Sidecar: metadata + typst_overrides example
    │   │   └── images/
    │   └── README.md
    ├── typst/                  Typst outputs: PDFs, .typ sources, test scripts
    ├── weasyprint/             WeasyPrint outputs: PDFs, CSS overrides
    │   └── test_columns_overrides.css  WeasyPrint CSS override template
    └── README.md
```

## Per-engine documentation

- [Typst engine](engines/typst/README.md)
- [WeasyPrint engine](engines/weasyprint/README.md)
