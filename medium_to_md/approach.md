# Converting a Medium Article to Markdown, EPUB, and PDF — Best Approach

## Recommended Pipeline: Playwright browser + `pandoc`

**Important:** `mediumexporter` is broken (Medium now embeds reCAPTCHA and requires JavaScript rendering). The working approach uses a headless browser to render the page, then extract the content as Markdown.

The companion script **`medium-to-md.py`** (in this repo) automates everything:
- Launches a headless Chromium via Playwright
- Waits for the Medium article to fully render
- Extracts all text with proper heading/blockquote/list formatting
- Downloads all images locally (20 images for the test article)
- Produces a clean `.md` file with `![Image](path)` references

---

## 1. Install the tools (one-time setup)

```bash
# Install pandoc (the universal document converter)
brew install pandoc

# Install Playwright for Python (use your conda env)
pip install playwright
playwright install chromium
```

---

## 2. Convert to Markdown (.md) — one command

**Tool:** `medium-to-md.py` (Playwright + Python)

```bash
# Install dependencies once
pip install playwright
playwright install chromium

# Convert ANY Medium article
/opt/anaconda3/envs/python_313x/bin/python medium-to-md.py \
  https://medium.com/@author/article-slug \
  /path/to/output/folder
```

This produces:
- `article-slug.md` — full Markdown with proper headings, blockquotes, lists
- `article-slug_images/` — folder with all article images downloaded locally, referenced in the `.md` via `![Image](path)`

---

## 3. Convert to ebook (.epub / .mobi)

**Tool:** `pandoc`

### EPUB (universal ebook format)

```bash
pandoc article.md -o article.epub
```

### MOBI (Amazon Kindle) — requires Calibre

```bash
# Install Calibre first
brew install --cask calibre

# Convert Markdown → EPUB → MOBI
pandoc article.md -o article.epub
ebook-convert article.epub article.mobi
```

### With enhanced formatting

```bash
pandoc article.md \
  --metadata title="Article Title" \
  --metadata author="Author Name" \
  --metadata lang="en" \
  --css epub-style.css \
  --toc \
  -o article.epub
```

- `--toc` generates a table of contents
- `--css` applies custom styling (fonts, spacing, etc.)
- EPUB is the open standard; MOBI can be derived from it via Calibre

---

## 4. Convert to PDF

**Tool:** `pandoc` + a PDF engine

### Option A: Quick & simple (using `wkhtmltopdf` — no LaTeX needed)

```bash
# Install wkhtmltopdf
brew install wkhtmltopdf

# Convert via HTML intermediate
pandoc article.md --pdf-engine=wkhtmltopdf -o article.pdf
```

### Option B: Polished, print-ready (using `xelatex` — requires LaTeX)

```bash
# Install MacTeX (large download)
brew install --cask mactex

# Or install BasicTeX (smaller alternative)
brew install --cask basictex

# Convert with custom formatting
pandoc article.md \
  --pdf-engine=xelatex \
  -V mainfont="Helvetica" \
  -V fontsize=12pt \
  -V geometry:margin=1in \
  --toc \
  -o article.pdf
```

### Option C: Browser Print-to-PDF (zero setup, preserves original formatting)

1. Open the Medium article in a browser (Safari, Chrome, Firefox)
2. Enable **Reader Mode** (for clean formatting)
3. Press `⌘+P` → **Save as PDF**

Best for one-off conversions where you want the exact visual formatting of the original article.

---

## Comparison Summary

| Format | Recommended Tool(s) | Quality | Effort | Preserves Images |
|--------|---------------------|---------|--------|------------------|
| **Markdown (.md)** | Playwright browser | ★★★★★ | Medium (needs browser) | ✅ (as links) |
| **EPUB** | `pandoc` from .md | ★★★★☆ | Low | ✅ |
| **MOBI (Kindle)** | `pandoc` + `calibre` | ★★★★☆ | Medium | ✅ |
| **PDF (quick)** | `pandoc` + `wkhtmltopdf` | ★★★☆☆ | Low | ✅ |
| **PDF (polished)** | `pandoc` + `xelatex` | ★★★★★ | Medium (needs LaTeX) | ✅ |
| **PDF (browser)** | Reader Mode → ⌘+P | ★★★★★ | None | ✅ |

---

## Key Advantages of This Approach

1. **Single canonical source** — Markdown is your master document; all other formats are derived from it
2. **Open-source and free** — no subscriptions, no lock-in, no paywalls
3. **Automation-friendly** — script the entire pipeline for batch processing
4. **Version-controllable** — Markdown files diff cleanly in git
5. **Customizable** — use CSS for ebooks, LaTeX templates for PDFs, or write your own Pandoc filters

---

## 3. Convert to ebook or PDF (from Markdown)

Once you have the `.md` file, convert with pandoc:

```bash
# Install pandoc
brew install pandoc

# EPUB
pandoc article-slug.md -o article-slug.epub

# PDF (quick)
brew install wkhtmltopdf
pandoc article-slug.md --pdf-engine=wkhtmltopdf -o article-slug.pdf

# PDF (polished)
brew install --cask mactex
pandoc article-slug.md --pdf-engine=xelatex -V mainfont="Helvetica" -V geometry:margin=1in -o article-slug.pdf
```
