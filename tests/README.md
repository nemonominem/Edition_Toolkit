# Edition Tests

Test files for validating `md2pdf` rendering behaviour across layout patterns.

---

## Files

### `test_columns.md`

Comprehensive test for column-span and image rendering in WeasyPrint. Each section isolates one pattern so regressions are easy to locate.

| Section | Pattern | Expected |
|---------|---------|----------|
| 1 | Normal two-column body text | Two columns |
| 2 | Bare Markdown table (no wrapper) | Two columns, table spans column width |
| 3 | Bare Markdown image `![]()` | Column-width image |
| 3b | Markdown `![]()` inside `div.single-column` | Full-width image (pre-converted to `<img>` by pipeline) |
| 3c | Raw `<img>` inside `div.single-column` | Full-width image |
| 3d | Raw `<img>` inside `div.full-width` | Full-width image, two-column resumes after |
| 3e | Raw `<img>` inside `div.single-column` (canonical pattern) | Full-width image |
| 4 | HTML table inside `div.single-column` | Full-width table, two-column resumes after |
| 5 | HTML table inside `div.full-width` | Full-width table, two-column resumes after |
| 6 | Mermaid diagram, no wrapper | Rendered PNG, column-width |
| 7 | Mermaid diagram inside `div.single-column` | Rendered PNG, full width |
| 8 | Prose-only `div.single-column` | Full-width prose and list |
| 9 | `div.key-takeaways` box | Full-width box |
| 10 | Two-column confirmed | Two columns |

### `images/`

Static assets referenced by test files (`test_img1.png`, etc.).

---

## Running the tests

```bash
conda activate python_313x
cd /Users/gillesdemaneuf/Work/Edition/tests

# Default style
md2pdf test_columns.md

# Intelligence style
md2pdf test_columns.md --css intelligence
```

Output PDF lands in the same directory as the input file.

---

## Notes

- **Section 3b** was an expected failure before the `convert_md_images()` pre-processing step was added to the pipeline. It now passes: Markdown `![]()` syntax inside raw HTML divs is converted to `<img>` tags before python-markdown processes the document.
- **Section 3e / 3c** are the canonical patterns for full-width images and remain the reference implementation.
- Mermaid rendering requires `mmdc` (`npm install -g @mermaid-js/mermaid-cli`). Without it, diagrams render as placeholder text — that is expected behaviour, not a failure.
