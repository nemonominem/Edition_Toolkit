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

## Usage

```bash
# Typst engine (default)
md2pdf article.md
md2pdf article.md --style intelligence --compile

# WeasyPrint engine
md2pdf article.md --engine weasyprint
md2pdf article.md --engine weasyprint --css intelligence --custom overrides.css

# Ragged-right text (Typst only)
md2pdf article.md --no-justify
```

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

- `md_harden --style <name>` reads the `hardening` object to know what to flag and how (pull-quote attribution style, confidence thresholds, et al. italics, etc.)
- The `design` object documents the rendering intent; the `.typ` and `.css` files are the implementations.

When a convention changes, update the JSON first, then the engine file(s).

## Structure

```
md_to_pdf/
├── pyproject.toml              Package definition
├── README.md                   This file
├── styles/                     Shared per-style JSON definitions (spec + hardening config)
│   ├── intelligence.json
│   ├── academic.json
│   ├── magazine.json
│   └── thinktank.json
├── etk_md2pdf/
│   ├── __init__.py
│   └── dispatcher.py           md2pdf entry point — parses --engine, delegates
├── engines/
│   ├── typst/                  Typst engine
│   │   ├── convert.py
│   │   ├── styles/             intelligence.typ, magazine.typ, thinktank.typ, academic.typ
│   │   └── README.md
│   └── weasyprint/             WeasyPrint engine
│       ├── convert.py
│       ├── styles/             style_intelligence.css, style_magazine.css, …
│       └── README.md
└── tests/
    ├── shared/                 Input files used by both engines
    │   ├── test_columns.md
    │   ├── WHO_Compromission.md
    │   └── images/
    ├── typst/                  Typst output PDFs + .typ sources (4 styles)
    ├── weasyprint/             WeasyPrint output PDFs (4 styles)
    └── README.md
```

## Per-engine documentation

- [Typst engine](engines/typst/README.md)
- [WeasyPrint engine](engines/weasyprint/README.md)
