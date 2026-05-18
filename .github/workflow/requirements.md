## Environment

- Python 3.13+ via conda (`conda activate python_313x`)
- All packages managed with **conda**, not pip

---

## medium_to_md

| Package | Install | Purpose |
|---------|---------|---------|
| `playwright` | `conda install -c conda-forge playwright` | Headless browser for Medium extraction |
| Chromium binary | `playwright install chromium` (one-time) | Browser driver |

---

## md_to_pdf (Typst engine — default)

| Tool/Package | Install | Purpose |
|---------|---------|---------|
| `typst` binary | `brew install typst` | Compiles .typ → PDF |
| Libre Baskerville font | `brew install font-libre-baskerville` | Used in intelligence style |
| Python stdlib only | — | No Python packages needed |
| md2pdf entry point | `conda develop md_to_pdf/` | Puts the `md2pdf` command on PATH |

---

## md_to_pdf (WeasyPrint engine — optional)

| Package | Install | Purpose |
|---------|---------|---------|
| `weasyprint` | `conda install weasyprint` | HTML/CSS → PDF renderer |
| `markdown` | `conda install markdown` | Markdown → HTML conversion |
| `pygments` | `conda install pygments` | Syntax highlighting in code blocks |
| `pango`, `gdk-pixbuf`, `libffi` | `brew install pango gdk-pixbuf libffi` | WeasyPrint system deps (macOS) |
| `mmdc` (mermaid-cli) | `npm install -g @mermaid-js/mermaid-cli` | Renders Mermaid diagrams to PNG (optional) |

---

## md_to_booklet

| Package | Install | Purpose |
|---------|---------|---------|
| `pandoc` | `conda install pandoc` | Markdown → LaTeX conversion |
| `pypdf` | `conda install pypdf` | PDF page imposition |
| `requests` | `conda install requests` | HTTP downloads if needed |

---

## Deliberate non-requirements

- No `requests` or `beautifulsoup4` — Medium extraction uses Playwright (full browser), not raw HTTP
- No `pillow` or `pytesseract` — no OCR in this pipeline
- No pip — use conda for all packages
- Keep engines lean: Typst engine requires only Python stdlib + the typst binary
