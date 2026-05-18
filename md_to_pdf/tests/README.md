# Tests

Shared test inputs for both engines.

## Structure

```
tests/
├── shared/
│   ├── test_columns.md       Comprehensive layout test (columns, images, tables, callouts)
│   ├── WHO_Compromission.md  Real-world article for end-to-end validation
│   ├── who.css               Per-article CSS override (WeasyPrint engine)
│   └── images/               Static assets referenced by test files
└── README.md
```

## Running tests

```bash
conda activate python_313x
cd /Users/gillesdemaneuf/Work/Edition/md_to_pdf

# Typst engine (default)
md2pdf tests/shared/test_columns.md --compile

# WeasyPrint engine
md2pdf tests/shared/test_columns.md --engine weasyprint --css intelligence
md2pdf tests/shared/test_columns.md --engine weasyprint --css magazine

# WHO article — Typst
md2pdf tests/shared/WHO_Compromission.md --compile

# WHO article — WeasyPrint with custom CSS
md2pdf tests/shared/WHO_Compromission.md --engine weasyprint --css intelligence --custom tests/shared/who.css
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
