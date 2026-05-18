# Edition Project — Claude Context

## Project Overview

Suite of publishing utilities for extracting, converting, and typesetting articles into publication-ready documents.

Three independent tools:
1. **medium_to_md** — Extract Medium articles to Markdown with embedded images
2. **md_to_pdf** — Convert Markdown to print-ready PDF (Typst default; WeasyPrint fallback)
3. **md_to_booklet** — Produce typeset booklets with imposition (Pandoc + XeLaTeX)

---

## Environment & Dependencies

### Golden Rule: Use Conda, Not Pip

All package management uses **conda** exclusively. Pip is only for:
- `playwright install chromium` (browser binary download, not a package)
- Packages truly unavailable via conda (rare)

### Current Setup

- **Python environment:** `python_313x` (conda environment)
- **Working directory:** `/Users/gillesdemaneuf/Work/Edition`
- **Run scripts:** Always from within the project subdirectories

### Conda Workflow

```bash
# Activate the environment
conda activate python_313x

# Install packages (use conda, not pip)
conda install package_name

# Check installed packages
conda list

# See what a script needs before installing
head -20 scripts/filename.py  # check imports
```

---

## Tools & Dependencies

### medium_to_md
- **Requires:** `playwright` (browser automation)
- **Install:** `conda install -c conda-forge playwright`
- **Then:** `playwright install chromium` (binary download, one-time)
- **No requirements.txt needed** — conda handles it

### md_to_pdf
- **Default engine:** Typst — `brew install typst`; Python stdlib only
- **WeasyPrint engine (optional):** `conda install markdown weasyprint pygments`
- **System deps for WeasyPrint (macOS):** `brew install pango gdk-pixbuf libffi`
- **Install package:** `conda develop md_to_pdf/` (puts `md2pdf` on PATH)
- **Fonts:** `brew install font-libre-baskerville` (intelligence style)

### md_to_booklet
- **Requires:** `pandoc`, `pypdf`, `requests`
- **Install:** `conda install pandoc pypdf requests`
- **Optional:** `pdfjam` (if not using pypdf fallback)

---

## When to Edit README Files

Update a tool's README when:
- Adding/removing features
- Changing command syntax
- Adding new content types
- Installation process changes

**Do NOT list pip commands** in READMEs — use conda instead.

---

## File Structure

```
Edition/
├── CLAUDE.md                  (this file — project context)
├── README.md                  (top-level overview)
│
├── medium_to_md/
│   ├── README.md
│   ├── medium-to-md.py
│   └── approach.md
│
├── md_to_pdf/                 (unified package — installs md2pdf command)
│   ├── pyproject.toml
│   ├── README.md
│   ├── etk_md2pdf/
│   │   ├── __init__.py
│   │   └── dispatcher.py      (entry point: parses --engine, delegates)
│   ├── engines/
│   │   ├── typst/             (DEFAULT engine)
│   │   │   ├── convert.py
│   │   │   ├── styles/*.typ
│   │   │   └── README.md
│   │   └── weasyprint/        (fallback engine: --engine weasyprint)
│   │       ├── convert.py
│   │       ├── styles/*.css
│   │       └── README.md
│   └── tests/
│       ├── shared/            (test_columns.md, WHO article, images/)
│       └── README.md
│
└── md_to_booklet/
    ├── instructions.md
    ├── README_printing.md
    ├── scripts/
    └── build/
```

---

## Key Design Decisions

1. **Embedded by default** — Images/styles embedded in output (single file, no broken links)
2. **Markdown-centric** — Markdown is the universal interchange format
3. **Path resolution** — Scripts auto-resolve paths; run from anywhere
4. **Reproducible** — Same input always produces same output
5. **Extensible** — Ready for videos, audio, iframes, custom embeds

---

## Common Commands

```bash
# Activate environment
conda activate python_313x

# Extract Medium article (with embedded images)
cd medium_to_md
python medium-to-md.py https://medium.com/path/to/article

# Extract with debug info
python medium-to-md.py https://medium.com/path/to/article --debug

# Save images to disk instead of embedding
python medium-to-md.py https://medium.com/path/to/article --disk

# Convert Markdown to PDF (Typst, default)
md2pdf article.md --compile

# Convert with WeasyPrint engine
md2pdf article.md --engine weasyprint --css intelligence

# Ragged-right text
md2pdf article.md --no-justify

# Build booklet (Res Gestae example)
cd ../md_to_booklet
python scripts/make_booklet_pandoc.py
```

---

## Troubleshooting

**"No playwright found"**
→ `conda install -c conda-forge playwright && playwright install chromium`

**"WeasyPrint not found"**
→ `conda install weasyprint markdown pygments`

**"pandoc not found"**
→ `conda install pandoc`

**Medium extraction returns 0 blocks**
→ Run with `--debug` flag to see what selectors were found

**PDF fonts look wrong**
→ Check the bundled CSS in `md_to_pdf/etk_md2pdf/styles/` — ensure fonts are conda-installed or imported via Google Fonts in the stylesheet

---

## Future Enhancements

- [ ] Add video embed support (iframe extraction + placeholder generation)
- [ ] Add audio embed support
- [ ] Add Twitter/CodePen iframe handling
- [ ] Custom Markdown extensions for Medium-specific features
- [ ] Batch processing (multiple articles → single booklet)
- [ ] Style review utility (validate against Demaneuf_Medium style profile)
- [ ] Fact-check utility (validate claims, cross-reference footnotes)

---

## Additional Resources (in .github/)

The `.github/` folder contains optional workflows and style guides for article writing projects:

- **`.github/docs/writing-styles.md`** — Detailed style profiles (Demaneuf_Medium, etc.) for reference when creating or editing long-form articles
- **`.github/docs/peer-review.md`** — Systematic peer-review methodology (factual accuracy, citation quality, argumentative integrity, fairness, tone, readability, consistency)
- **`.github/docs/grounding-protocol.md`** — Protocol for requesting external LLM grounding on factual claims
- **`.github/workflow/`** — Workflow conventions, todo management, transient file handling

These are optional and project-specific. Not all Edition projects will use them.
