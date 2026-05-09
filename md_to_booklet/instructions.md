## Goal
Produce a printable, annotated translation booklet of the Res Gestae Divi Augustae with an end-to-end Python/Pandoc pipeline and robust reproducible commands.

Current Implementation:
- A5 production: one page = 148 × 210 mm (available in `build/smallpages/res_gestae_smallpages.pdf`).
- Imposed A4 duplex: 2 × A5 per face (available in `build/imposed/res_gestae_imposed_A4.pdf`).
- Phase-testing outputs exist: `build/imposed/test_front_folio1.pdf`, `build/imposed/test_back_folio1.pdf`.

Current workflow preferences:
- Latin left pages, English + notes right pages.
- 2 sections per page for better density and reduced total page count.
- cover page with portrait and author is on actual page 1.
- Impressum is on actual page 2.
- Start numbering at actual page 3 from 1 (Latin text first page).
- Back cover + inside back cover are unnumbered.

Current text sources:
- Latin: scraped from TheLatinLibrary resgestae page.
- English translation: hand-crafted mapping for section 1–10 + fallback approximate translation.
- Notes: vocabulary provides case/declension for names/adjectives and verb form hints (am-o/as/are/atum); grammar and short history bullets are generated.

Current artifacts:
- `data/latin.txt` (clean section markers)
- `build/smallpages/booklet.md` (intermediate markdown)
- `build/smallpages/res_gestae_smallpages.pdf` (A5)
- `build/imposed/res_gestae_imposed_A4.pdf` (A4 duplex)
- `README_printing.md` (process instructions)
- `scripts/make_booklet_pandoc.py` (pipeline script) 

Dependencies:
- `pandoc` + `xelatex`/`pdflatex` (fallback used if fonts missing)
- `pdfjam` or internal pypdf imposition fallback
- `requests`, `pypdf` Python libraries

How to run (fresh session):
1. `cd /Users/gillesdemaneuf/Work/Edition/md_to_booklet`
2. `conda activate python_313x`
3. `conda install pandoc requests pypdf`
4. `python scripts/make_booklet_pandoc.py`
5. Inspect:
   - `build/smallpages/res_gestae_smallpages.pdf`
   - `build/imposed/res_gestae_imposed_A4.pdf`

Notes for tomorrow:
- If changing to 13×21.5 mm final trim, switch `render_smallpages()` geometry to 130×215 mm and adjust penned layout accordingly.
- If `EB Garamond` is installed, make sure fonts are placed in `fonts/` and fontspec line in script references TTF path.
- For continuing from new chat, run above commands and use `scripts/make_booklet_pandoc.py` to reproduce precisely.

Phase status:
- Phase 1: complete
- Phase 2: complete
- Phase 3: mostly complete, final UI checks and polish are done


## Phase 1 — Minimal front test (no content)

Create build/imposed/test_front_folio1.pdf
A4 landscape, centered 26.0 × 21.5 cm rectangle with:
Right panel labeled “Page 1 (Front cover placeholder)”
Left panel labeled “Page 4 (Back of folio placeholder)”
Crop marks and center fold guide.
No scaling; ensure the 26 × 21.5 frame measures true size.
After generating, pause and wait for me to confirm the print looks correct.

## Phase 2 — Matching back test with first content (Sections 1–2 start)

Create build/imposed/test_back_folio1.pdf with:
Left panel = Page 2: Latin, beginning of Res Gestae, Section 1. Provide clean Latin text, section heading “Sectio I,” and a short running header.
Right panel = Page 3: English (original translation) of the same lines on p2 + medium notes below. Notes format:
Vocabulary: brief glosses with lemma and sense

Grammar: bullet points for key constructions; cite Latin snippets

History: 2–4 bullets for context (e.g., cursus honorum, dona militaria, senatorial decrees)
Keep type sizes consistent with final plan. Ensure mirrored margins/gutter so fold doesn’t crowd text.
After generating, pause for confirmation of duplex alignment.

## Phase 3 — Build pipeline and full text

Implement scripts/make_booklet.py to:
Fetch/normalize Latin text (public domain) and write to data/latin.txt with clear section markers (e.g., “== SECTION 1 ==”).
Generate an original English translation section by section.
Produce notes (medium density) per section as specified.
Typeset small pages (13 × 21.5 cm) with consistent styles, page numbers, and headers: output build/smallpages/res_gestae_smallpages.pdf
Impose into A4 duplex spreads with precise arrangement and crop/fold guides: output build/imposed/res_gestae_imposed_A4.pdf
Ensure that each imposed spread is exactly one folio (4 pages), sequenced through the entire work.
Acceptance criteria

## Dimensions:
Small pages: exactly 130 mm × 215 mm per page.
Imposed A4 spreads: 210 mm × 297 mm sheet with a centered 260 mm × 215 mm content rectangle. Panels are 130 mm × 215 mm each.
Ordering and imposition:
For every folio n: Side A shows (p4n | p4n−3); Side B shows (p4n−2 | p4n−1).
After duplex printing “flip on short edge,” trimming, and folding, page order reads correctly.

## Content:
All sections of Res Gestae covered.
Latin on left pages; right pages have English translation + notes.
Notes are concise, accurate, and tied to the Latin lines present on the facing page.

Typography:
Body text is legible at small trim size; headings and running headers are consistent.
Page numbers bottom outer; headers as specified.

Files:
test_front_folio1.pdf and test_back_folio1.pdf produced first.
res_gestae_smallpages.pdf and res_gestae_imposed_A4.pdf produced after approval.


## Implementation guidance (you choose the stack; be explicit and reproducible)

### Option A — Python (recommended for portability)
Use reportlab (or cairo + pango) to typeset small pages and draw imposed spreads with vector crop marks.
Embed fonts from fonts/ directory (download EB Garamond + Noto Serif). Fall back to built-ins if not available, but keep metrics stable.

Write an imposition function that:
Places two 130×215 mm pages onto a centered 260×215 mm area on A4 landscape.
Draws light crop marks and a faint fold line at the center.
Ensures 0 scaling, 1:1 mapping of points to mm.

### Option B — LaTeX
Use geometry to create a 130×215 mm document for small pages.
Use pdfjam (or LaTeX’s pdfpages + custom offset) to impose onto A4 with precise centering, crop marks, and 2-up layout (short-edge duplex).
Provide a Makefile to build everything reproducibly.

### Style guide for notes (apply consistently)

Vocabulary:
“imperium: ‘command, authority’; here esp. the legal right to command armies”
Mark idioms: “consul octavianum gerere — to hold the consulship as an octavian (eighth time)”

Grammar:
“abl. abs.: bello confecto — temporal circumstance ‘after the war was finished’”
“indirect statement: dixit se fecisse — acc. + inf.”

History:
Concise bullets: institutions, offices, dates (rounded), geography, Augustan propaganda context.
Keep notes proportional to the Latin on the facing page (don’t overflow).

### Next steps for you (Claude)

Start with Phase 1: generate build/imposed/test_front_folio1.pdf and show me a download link.
Pause and wait for my feedback before continuing to Phase 2.