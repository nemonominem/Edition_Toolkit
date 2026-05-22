# TODO

## Management rules

- **Statuses:** `Open` · `Working` · `Validate` · `Closed` · `Implicit`
- **Open** — task is queued and not yet started.
- **Working** — task is actively in progress in the current session.
- **Validate** — task is finished by the AI and awaiting human review. Use automatically for any non-trivial completed task where genAI output should be checked (substantive writing, structural changes, factual claims). Trivial tasks with no genAI risk (formatting, file moves, mechanical edits) skip this and go straight to `Closed`.
- **Closed** — task is fully done and verified (or trivial enough to need no review); keep the entry for record.
- **Implicit** — task was requested directly in chat without referencing this list, was large enough to be worth logging, and has been completed. Kept for record.
- On each pass, move tasks through their correct status before starting work and again after completing it. Never leave a task as `Working` at the end of a session.
- Menial or trivial tasks (single-step edits, quick formatting fixes) do not need an entry here.

---

## Tasks
1. `Open` · **Fix footer declaration in md_to_pdf** — there is some hardcoding going on, that refers to the generic style css. We need to keep that generic. So either have a local copy, or a local json, with specific overwrite.

2. `Open` · **There are issues with the references/notes in the Proximal Origin mds** — oddities - needs investigating then fixing.

3. `Open` · **Style review / style conversion utility** — Create utility to review Markdown against Demaneuf_Medium style guide or convert between article writing styles (see `.github/docs/writing-styles.md` for style definitions).

4. `Open` · **Fact-check utility** — Create utility to validate factual claims in Markdown articles against sources, cross-reference footnotes, and flag unsourced assertions (integrates with grounding protocol if needed).

5. `Open` · **Batch processing pipeline** — Extend medium_to_md to support extracting multiple Medium articles and combining into single Markdown file or booklet structure for md_to_booklet.

6. `Open` · **Better style differentiation: magazine, thinktank, academic** — Current Typst styles (and WeasyPrint to a lesser extent) are too visually similar. Each style should have a clearly distinct identity: different layout (single vs two-column), font choices, colour palette, spacing rhythm, and header/footer treatment. Typst is the priority since it is the default engine.

7. `Open` · **Apply constants refactor to academic.typ, magazine.typ, thinktank.typ** — `intelligence.typ` was refactored so all tuneable values (font sizes, spacing, colours, page geometry) are named constants at the top of the file. The same pattern must be applied to the other three Typst style files.

---

## Canonical commands

### md_to_pdf — convert and compile

Always use the `md2pdf` entry point, not `typst compile` directly:

```bash
conda activate python_313x

# Typst engine (default) — convert + compile in one step
md2pdf WHO_Compromission.md --style intelligence --output WHO_Compromission_intelligence_typst.pdf --compile

# Typst only — other styles
md2pdf article.md --style academic --output out.pdf --compile
md2pdf article.md --style magazine --output out.pdf --compile

# WeasyPrint engine
md2pdf article.md --engine weasyprint --css intelligence

# Ragged-right text
md2pdf article.md --no-justify --compile
```

`typst compile` directly is only acceptable when iterating on a `.typ` file in isolation (style-only changes, no Markdown source involved).

---

## Implicit (completed this session)

7. `Implicit` · **Pre-process Markdown image syntax to `<img>` tags** — Added `convert_md_images()` in `convert.py` to convert `![]()` (including `{width=}`) to raw `<img>` before python-markdown runs, fixing images inside raw HTML divs rendering as plain text.

8. `Implicit` · **Fix WeasyPrint crash on column + image/float** — Wrapped standalone and Mermaid images in `<p class="img-block">`. Removed automatic `h1 + p::first-letter` drop-cap selector in `style_magazine.css` (WeasyPrint bug: asserts on `::first-letter` when first inline child is `<em>` or replaced element). Drop cap is now explicit opt-in via `p.drop-cap`.

9. `Implicit` · **Rename serif style to thinktank** — Fixed bad `.pdf` extension from rename; updated default in `convert.py`; updated all references in `README.md`, `CLAUDE.md`, `md_to_pdf/README.md`.

10. `Implicit` · **Move root-level CSS duplicates to `etk_md2pdf/styles/`** — Deleted 4 duplicate `style_*.css` files from `md_to_pdf/` root; updated file trees and references in all three READMEs and `CLAUDE.md`.

11. `Implicit` · **Magazine style fixes** — Replaced dark footer bar with clean three-slot footer matching intelligence style. Added missing `div.single-column` and `div.key-takeaways` rules (fixes Sections 3e, 4, 7, 9 in test). Fixed Section 9 test to use raw HTML headings inside the div (python-markdown limitation).

12. `Implicit` · **Tag v0.1.0 and fix installation docs** — Tagged first distribution release; replaced `pip install -e` with `git+ssh` tagged install in `md_to_pdf/README.md`; tag kept up to date with HEAD across multiple commits.
