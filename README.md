# Edition — Publishing & Document Tools

A suite of utilities for extracting, converting, and typesetting articles into publication-ready documents.

---

## Tools

### 1. medium_to_md — Medium Article Extractor

Extract Medium articles to Markdown with properly positioned, embedded images.

- **Input:** Medium article URL
- **Output:** Self-contained `.md` file with images as base64 (or saved to disk with `--disk`)
- Preserves headings, lists, blockquotes, code blocks, captions, image positions

```bash
conda activate python_313x
cd medium_to_md
python medium-to-md.py https://medium.com/path/to/article
```

📖 [Full documentation](medium_to_md/README.md)

---

### 2. md_to_pdf — Markdown to Print-Ready PDF

Convert Markdown articles to professionally typeset, print-ready PDFs.  
Two rendering engines behind a single `md2pdf` command.

| Engine | Default | Technology |
|--------|---------|------------|
| `typst` | ✓ | [Typst](https://typst.app/) — fast, precise, no layout crashes |
| `weasyprint` | | [WeasyPrint](https://weasyprint.org/) — CSS Paged Media |

**Styles:** `intelligence` (US IC two-column, navy/gold), `magazine`, `thinktank`, `academic`

```bash
conda activate python_313x
cd md_to_pdf
conda develop .            # installs md2pdf command
brew install typst         # default engine
brew install font-libre-baskerville

# Use it
md2pdf article.md --compile
md2pdf article.md --engine weasyprint --css intelligence
```

📖 [Full documentation](md_to_pdf/README.md)

---

### 3. md_to_booklet — Markdown to Typeset Booklet

Produce print-ready booklets with page imposition (Pandoc + XeLaTeX).

```bash
conda activate python_313x
cd md_to_booklet
conda install pandoc requests pypdf
python scripts/make_booklet_pandoc.py
```

📖 [Full documentation](md_to_booklet/instructions.md) | [Printing guide](md_to_booklet/README_printing.md)

---

## Full Workflow: Medium → PDF

```bash
conda activate python_313x

# 1. Extract article
cd medium_to_md
python medium-to-md.py https://medium.com/path/to/article -o ../articles/

# 2. Convert to PDF
cd ../md_to_pdf
md2pdf ../articles/article.md --compile
```

---

## File Structure

```
Edition/
├── medium_to_md/
│   ├── medium-to-md.py
│   └── README.md
│
├── md_to_pdf/                  (unified package — installs md2pdf)
│   ├── pyproject.toml
│   ├── etk_md2pdf/
│   │   ├── __init__.py
│   │   └── dispatcher.py       (entry point: parses --engine, delegates)
│   ├── engines/
│   │   ├── typst/              (DEFAULT — convert.py + styles/*.typ)
│   │   └── weasyprint/         (fallback — convert.py + styles/*.css)
│   └── tests/
│       └── shared/             (test_columns.md, WHO article, images/)
│
└── md_to_booklet/
    ├── scripts/
    └── build/
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Extract Medium article | `python medium-to-md.py <url>` |
| Convert to PDF (Typst) | `md2pdf article.md --compile` |
| Convert to PDF (WeasyPrint) | `md2pdf article.md --engine weasyprint --css intelligence` |
| Ragged-right text | `md2pdf article.md --no-justify` |
| Custom CSS override | `md2pdf article.md --engine weasyprint --custom overrides.css` |
| List styles | `md2pdf --list-styles` |
| Debug Medium extraction | `python medium-to-md.py <url> --debug` |

---

## Troubleshooting

**`typst` not found** → `brew install typst`

**Libre Baskerville font warnings** → `brew install font-libre-baskerville`

**WeasyPrint not found** → `conda install markdown weasyprint pygments`

**Medium returns 0 blocks** → Run with `--debug` to inspect selectors

**Large file (embedded images)** → Expected. Use `--disk` to save images separately.
