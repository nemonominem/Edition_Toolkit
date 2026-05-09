# Edition — Publishing & Document Tools

A suite of utilities for extracting, converting, and typesetting articles into publication-ready documents.

---

## Projects

### 1. **medium_to_md** — Medium Article Extractor

Extract Medium articles to Markdown with properly positioned, embedded images.

- **Input:** Medium article URL
- **Output:** Self-contained `.md` file with images as base64 (or saved separately with `--disk`)
- **Key features:**
  - Images appear in correct positions (not appended at end)
  - Embedded base64 images by default (single file, no broken links)
  - Optional disk storage for smaller files
  - Preserves headings, lists, blockquotes, code blocks, captions
  - HTML `<img>` tags with fixed width (800px)
  - Debug mode for troubleshooting

**Quick start:**
```bash
conda activate python_313x
cd medium_to_md
conda install -c conda-forge playwright
playwright install chromium
python medium-to-md.py https://medium.com/path/to/article
```

📖 [Full documentation](medium_to_md/README.md)

---

### 2. **md_to_pdf** — Markdown to Print-Ready PDF

Convert Markdown articles to beautifully typeset, print-ready PDFs using WeasyPrint.

- **Input:** Markdown file (`.md`)
- **Output:** Professional PDF with custom typography, layout, and page styling
- **Key features:**
  - Full CSS Paged Media support (headers, footers, margins, page breaks)
  - Footnotes, tables, syntax-highlighted code blocks
  - Mermaid diagram rendering (optional)
  - Customizable fonts, sizes, colors, and spacing via `style.css`
  - Image sizing via CSS selectors (no need to edit markdown)
  - Callout boxes, glossary formatting, automatic page breaks
  - Orphan/widow control, long URL wrapping

**Quick start:**
```bash
conda activate python_313x
cd md_to_pdf
conda install markdown weasyprint pygments
python md_to_pdf.py article.md
```

📖 [Full documentation](md_to_pdf/README.md)

---

### 3. **md_to_booklet** — Markdown to Typeset Booklet

Specialized pipeline for producing print-ready booklets (like the Res Gestae translation project).

- **Input:** Markdown with structured sections
- **Output:** Small-page PDF (e.g., A5) + imposed A4 duplex spreads for booklet printing
- **Key features:**
  - Pandoc + XeLaTeX typesetting
  - Precise imposition for short-edge duplex printing
  - Crop marks and fold guides
  - Side-by-side layouts (e.g., Latin/English, original/translation)
  - Vocabulary, grammar, and historical notes formatting
  - Reproducible Python pipeline

**Quick start:**
```bash
conda activate python_313x
cd md_to_booklet
conda install pandoc requests pypdf
python scripts/make_booklet_pandoc.py
```

📖 [Full documentation](instructions.md) | [Printing guide](README_printing.md)

---

## Workflow Examples

### Extract Medium → PDF

```bash
conda activate python_313x

# 1. Extract Medium article to markdown
cd medium_to_md
python medium-to-md.py https://medium.com/path/to/article -o ../articles/

# 2. Convert markdown to PDF
cd ../md_to_pdf
python md_to_pdf.py ../articles/article.md
```

### Medium → Booklet

```bash
# Extract Medium articles to markdown
# Merge into a single markdown file with booklet structure
# Use md_to_booklet pipeline to produce imposed spreads
```

---

## Setup (One-Time)

### Python Environment

All tools use Python 3.7+ via conda environment `python_313x`. Install dependencies:

```bash
conda activate python_313x

# For medium_to_md
conda install -c conda-forge playwright
playwright install chromium

# For md_to_pdf
conda install markdown weasyprint pygments

# For md_to_booklet
conda install pandoc requests pypdf
```

### Optional System Dependencies

**For md_to_pdf:**
```bash
# macOS
brew install pango gdk-pixbuf libffi

# For Mermaid diagram rendering (optional)
brew install node
npm install -g @mermaid-js/mermaid-cli
```

**For md_to_booklet:**
```bash
# macOS
brew install pandoc wkhtmltopdf
```

---

## File Structure

```
Edition/
├── README.md                          (this file)
│
├── medium_to_md/
│   ├── README.md                      (feature docs)
│   ├── medium-to-md.py                (main script)
│   ├── requirements.txt
│   ├── approach.md
│   └── the-emi-fix-*.md               (example output)
│
├── md_to_pdf/
│   ├── README.md                      (detailed guide)
│   ├── md_to_pdf.py                   (main script)
│   ├── style.css                      (typography & layout)
│   └── requirements.txt
│
└── md_to_booklet/
    ├── instructions.md                (project spec)
    ├── README_printing.md             (printing workflow)
    ├── scripts/
    │   ├── make_booklet.py
    │   ├── make_booklet_pandoc.py
    │   ├── make_front_test.py
    │   └── make_back_test.py
    ├── data/
    │   ├── latin.txt
    │   ├── english.txt
    │   └── backpage.txt
    ├── build/
    │   ├── smallpages/
    │   └── imposed/
    ├── examples/
    │   └── ResGestae/
    └── requirements.txt
```

---

## Architecture & Design Principles

**Modular pipeline:** Each tool is independent—use one, two, or all three in sequence.

**Markdown-centric:** Markdown is the universal intermediate format. Any tool can read or write it.

**Embedded defaults:** Images, styles, and metadata are embedded by default (single file, no broken links). Options exist for disk-based workflows.

**Reproducible:** All conversions are deterministic. The same input always produces the same output.

**Extensible:** Each tool has hooks for new content types (videos, audio, custom embeds, etc.).

---

## Quick Reference

| Task | Tool | Input | Output |
|---|---|---|---|
| Extract Medium article | `medium_to_md` | URL | `.md` (with embedded images) |
| Convert to PDF | `md_to_pdf` | `.md` | `.pdf` (print-ready) |
| Create booklet | `md_to_booklet` | structured `.md` | A5 + imposed A4 `.pdf` |
| Save images separately | `medium_to_md --disk` | URL | `.md` + folder of images |
| Customize PDF look | edit `style.css` | — | fonts, colors, margins, footer, etc. |
| Debug extraction | `medium_to_md --debug` | URL | extraction details in stderr |

---

## Troubleshooting

**Medium article not extracted**
- Run with `--debug` to see block counts and types
- Try again—page rendering can vary

**PDF fonts missing**
- Check `style.css`—fonts must be installed locally or imported from Google Fonts
- Edit `FONT_BODY` and `FONT_MONO` variables to use system fonts

**Large markdown file (embedded images)**
- This is expected. Use `--disk` to save images separately

**Booklet imposition issues**
- Confirm `pandoc` and `xelatex` are installed
- Check `instructions.md` for phase-by-phase setup

---

## Development Notes

- All scripts resolve paths automatically—run from anywhere
- Python 3.7+ required
- Conda environment `python_313x` available for reproducible builds
- Logs go to stderr; output paths go to stdout

---

## References

- [Medium to Markdown](medium_to_md/README.md)
- [Markdown to PDF](md_to_pdf/README.md)
- [Markdown to Booklet](md_to_booklet/instructions.md)
- [Booklet Printing](md_to_booklet/README_printing.md)
