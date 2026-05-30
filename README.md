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

### 2. md_harden — Markdown Hardener

Normalize and validate a Markdown file before conversion. Produces a human-reviewable `_review.md` with numbered Before/After suggestion blocks — the author approves every change before the file goes to `md2pdf`.

**Transforms:** bold-only paragraphs → H4, bare Notes/References headings removed, pull-quote spacing and attribution normalised, consistency advisories (et al. italics, apostrophe style, unquoted pull-quotes).

Pass `--style <name>` to load per-style conventions (pull-quote attribution format, confidence thresholds) from `md_to_pdf/styles/<name>.json`.

```bash
conda activate python_313x

# Generate review document (open in VSCode Preview, edit, then apply)
# Run from the Edition/ root; path to source file is relative to cwd
python md_harden/md_harden.py path/to/article.md --review --claude --style intelligence

# Apply surviving suggestions from reviewed file
python md_harden/md_harden.py path/to/article.md --apply path/to/article_review.md

# Skip the bold-heading promotion (ambiguous — needs human judgement)
python md_harden/md_harden.py path/to/article.md --review --skip bold-headings
```

---

### 3. md_to_pdf — Markdown to Print-Ready PDF

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

### 4. md_to_booklet — Markdown to Typeset Booklet

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

# 2. Harden the Markdown — generate review, approve, apply
python md_harden/md_harden.py ../articles/article.md --review --claude --style intelligence
# → open article_review.md in VSCode Preview, delete/edit suggestions
python md_harden/md_harden.py ../articles/article.md --apply ../articles/article_review.md
# → produces articles/article_hardened.md

# 3. Convert hardened file to PDF
md2pdf ../articles/article_hardened.md --style intelligence --compile
```

---

## File Structure

```
Edition/
├── medium_to_md/
│   ├── medium-to-md.py
│   └── README.md
│
├── md_harden/
│   └── md_harden.py            (Markdown normalizer — run before md2pdf)
│
├── md_to_pdf/                  (unified package — installs md2pdf)
│   ├── pyproject.toml
│   ├── styles/                 (shared per-style JSON — spec + hardening config)
│   │   ├── intelligence.json   (2-col, navy/gold, source: attribution)
│   │   ├── academic.json       (1-col, serif, Source: attribution)
│   │   ├── magazine.json       (1-col, rust accent, source: attribution)
│   │   └── thinktank.json      (2-col, green accent, Source: attribution)
│   ├── etk_md2pdf/
│   │   ├── __init__.py
│   │   └── dispatcher.py       (entry point: parses --engine, delegates)
│   ├── engines/
│   │   ├── typst/              (DEFAULT — convert.py + styles/*.typ)
│   │   └── weasyprint/         (fallback — convert.py + styles/*.css)
│   └── tests/
│       ├── shared/             (test_columns.md, images/)
│       ├── typst/              (output PDFs + .typ sources, 4 styles)
│       └── weasyprint/         (output PDFs, 4 styles)
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
| Harden — generate review | `python md_harden/md_harden.py article.md --review --style intelligence` |
| Harden — apply review | `python md_harden/md_harden.py article.md --apply article_review.md` |
| Harden + Claude review | `python md_harden/md_harden.py article.md --review --claude --style intelligence` |
| Convert to PDF (Typst) | `md2pdf article_hardened.md --style intelligence --compile` |
| Convert to PDF (WeasyPrint) | `md2pdf article_hardened.md --engine weasyprint --css intelligence` |
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
