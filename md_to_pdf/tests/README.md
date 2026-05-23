# Tests

## Structure

```
tests/
├── shared/                        Inputs used by both engines
│   ├── test_columns/              Public test article
│   │   ├── test_columns.md        Comprehensive layout test (columns, images, tables, callouts)
│   │   ├── test_columns.json      Sidecar: metadata + typst_overrides
│   │   └── images/                Static assets
│   ├── WHO/                       Gitignored — private article (not committed)
│   │   ├── WHO_Compromission.md
│   │   ├── WHO_Compromission.json
│   │   ├── WHO_Compromission_overrides.css
│   │   └── images/
│   └── README.md
├── typst/                         Typst engine outputs
│   └── test_columns_<style>.pdf   4 styles: intelligence, magazine, thinktank, academic
├── weasyprint/                    WeasyPrint engine outputs
│   ├── test_columns_<style>.pdf   4 styles
│   ├── test_columns_overrides.css Annotated CSS override template
│   └── run_large_table_test.sh
└── README.md
```

## Running tests

```bash
conda activate python_313x
cd /Users/gillesdemaneuf/Work/Edition/md_to_pdf

# Typst — all 4 styles
for STYLE in intelligence magazine thinktank academic; do
  md2pdf tests/shared/test_columns/test_columns.md --style $STYLE --output tests/typst/test_columns_${STYLE}.pdf --compile
done

# WeasyPrint — all 4 styles
for STYLE in intelligence magazine thinktank academic; do
  md2pdf tests/shared/test_columns/test_columns.md --engine weasyprint --css $STYLE \
         --output tests/weasyprint/test_columns_${STYLE}.pdf
done

# WHO article — Typst (sidecar auto-detected)
md2pdf tests/shared/WHO/WHO_Compromission_hardened.md --style intelligence --compile

# WHO article — WeasyPrint with custom CSS
md2pdf tests/shared/WHO/WHO_Compromission_hardened.md --engine weasyprint --css intelligence \
       --custom tests/shared/WHO/WHO_Compromission_overrides.css
```

## test_columns.md — section index

| Section | Pattern | Expected (both engines) |
|---------|---------|------------------------|
| 1 | Normal two-column body | Two columns |
| 2 | Bare Markdown table | Full-width (spans columns) |
| 3 | Bare Markdown image | Column-width |
| 3b–3e | Images inside divs | Full-width |
| 4–5 | HTML tables inside divs | Full-width |
| 6–7 | Mermaid diagrams | Rendered PNG or placeholder |
| 8 | Prose-only div.single-column | Full-width prose |
| 9 | div.key-takeaways | Blue callout box |
| 10 | Two-column confirmed | Two columns |
| 11 | Large table in div.full-width | Full-width, paginates |
| 12 | Large table in div.single-column | Full-width |
| 13 | Large standalone table | Full-width (spans columns) |
| 14 | Footnote rendering | Superscript numbers |
| 15 | Insights box | Cream box, gold borders |
