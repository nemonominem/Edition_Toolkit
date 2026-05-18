# etk-md2pdf

Markdown → PDF converter for the Edition ToolKit.  
Two rendering engines, one command.

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

## Structure

```
md_to_pdf/
├── pyproject.toml              Package definition
├── README.md                   This file
├── etk_md2pdf/
│   ├── __init__.py
│   └── dispatcher.py           md2pdf entry point — parses --engine, delegates
├── engines/
│   ├── typst/                  Typst engine
│   │   ├── convert.py
│   │   ├── styles/*.typ
│   │   └── README.md
│   └── weasyprint/             WeasyPrint engine
│       ├── convert.py
│       ├── styles/*.css
│       └── README.md
└── tests/
    ├── shared/                 Input files used by both engines
    │   ├── test_columns.md
    │   ├── WHO_Compromission.md
    │   └── images/
    └── README.md
```

## Per-engine documentation

- [Typst engine](engines/typst/README.md)
- [WeasyPrint engine](engines/weasyprint/README.md)
