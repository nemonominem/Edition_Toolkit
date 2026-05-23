# tests/shared — Engine-agnostic test inputs

This directory contains source files consumed by **both** the Typst and WeasyPrint
engines. Nothing here is engine-specific.

## Contents

```
shared/
├── test_columns/            Public test article and its inputs.
│   ├── test_columns.md      Exercises two-column layout, pull-quotes, footnotes,
│   │                        tables, callouts, images.
│   ├── test_columns.json    Per-article sidecar (metadata + Typst overrides).
│   │                        Auto-detected by md2pdf alongside the .md file.
│   └── images/              Images embedded in test_columns.md.
│
├── WHO/                     Gitignored — private article inputs. Not committed.
│   ├── WHO_Compromission.md          Original extracted article
│   ├── WHO_Compromission.md.bak      Backup before --apply
│   ├── WHO_Compromission_hardened.md Hardened source — convert this one
│   ├── WHO_Compromission.json        Sidecar (metadata + Typst overrides)
│   ├── WHO_Compromission_overrides.css  WeasyPrint CSS overrides
│   ├── WHO_Compromission_review.md   Hardening review file
│   └── images/                       Article images + pre-rendered mermaid PNGs
│
└── README.md                This file.
```

## What does NOT belong here

- Engine-specific CSS override files → `tests/weasyprint/`
- Engine output PDFs or `.typ` sources → `tests/typst/` or `tests/weasyprint/`

## Per-article sidecar schema

`test_columns/test_columns.json` (and any `<stem>.json` sidecar) supports two blocks:

**Metadata** — applies to both engines, overridden by YAML frontmatter:

```json
{
  "author":   "G. Demaneuf",
  "title":    "Article Title",
  "pub_name": "DRASTIC",
  "doc_type": "OSINT RESEARCH PRODUCT"
}
```

**Typst overrides** — Typst only; injected as `#let` redefinitions after `#import`,
before `#show: doc.with()`. WeasyPrint ignores this block:

```json
{
  "typst_overrides": {
    "body_size":    "9.5pt",
    "body_leading": "0.65em",
    "body_spacing": "1.4em",
    "list_spacing": "0.9em",
    "h1_size": "16pt",  "h1_above": "1.0em",  "h1_below": "0.6em",
    "h2_size": "11pt",  "h2_above": "1.6em",  "h2_below": "0.5em",
    "h3_size": "10.5pt","h3_above": "1.4em",  "h3_below": "0.5em",
    "h4_size": "9.5pt", "h4_above": "1.0em",  "h4_below": "0.5em",
    "header_size": "11pt",
    "footer_size": "7.5pt",
    "page_paper": "a4"
  }
}
```

For WeasyPrint visual tweaks (font, spacing, heading alignment, colours), use a
`--custom` CSS file. See `tests/weasyprint/test_columns_overrides.css` for an
annotated template.

## Pipeline

```bash
# Step 1 — harden (run from project root)
python md_harden/md_harden.py md_to_pdf/tests/shared/test_columns/test_columns.md \
       --review --claude --style intelligence

# Step 2 — review test_columns_review.md, delete unwanted suggestions

# Step 3 — apply
python md_harden/md_harden.py md_to_pdf/tests/shared/test_columns/test_columns.md \
       --style intelligence \
       --apply md_to_pdf/tests/shared/test_columns/test_columns_review.md

# Step 4a — convert with Typst (sidecar auto-detected)
md2pdf md_to_pdf/tests/shared/test_columns/test_columns.md --style intelligence --compile

# Step 4b — convert with WeasyPrint
md2pdf md_to_pdf/tests/shared/test_columns/test_columns.md \
       --engine weasyprint --css intelligence \
       --custom md_to_pdf/tests/weasyprint/test_columns_overrides.css
```
