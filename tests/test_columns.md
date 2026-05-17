# Column Layout Test

*Testing column-span behaviour in WeasyPrint — comprehensive.*

## Section 1: Normal Two-Column Flow

This is normal two-column body text. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.

More two-column text. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium.

## Section 2: Bare Markdown Table (no wrapper)

Two-column text before the table.

| Actor | Role | Confidence |
|-------|------|------------|
| Alice | Lead analyst | High |
| Bob   | Support | Medium |
| Carol | Field officer | Low |
| Dave  | Coordinator | High |

Two-column text after the bare table. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

## Section 3: Bare Markdown Image (no wrapper — stays column-width)

Two-column text before the image.

![Test image — bare Markdown syntax, stays column-width](images/test_img1.png)

Two-column text after the bare image. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

## Section 3e: WORKING single-column image (raw HTML img + div.single-column)

Two-column text before the div. This is the canonical working pattern for full-width images.

<div class="single-column">
<img src="images/test_img1.png" alt="Full-width image — working pattern" style="max-width:100%;display:block;margin:0.5em auto;">
<p style="text-align:center;font-style:italic;font-size:8pt;">Fig. 1 — This image spans the full page width using raw HTML img inside div.single-column.</p>
</div>

Two-column text resumes here after the full-width image. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

## Section 3b: Markdown image inside div.single-column (EXPECTED FAIL)

Two-column text before the div.

<div class="single-column">

![Test image — Markdown syntax inside div — will NOT render](images/test_img1.png)

</div>

Two-column text after the div. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

## Section 3c: Raw HTML img inside div.single-column (EXPECTED PASS — full width)

Two-column text before the div.

<div class="single-column">
<img src="images/test_img1.png" alt="Test image — raw HTML img, full width" style="max-width:100%;display:block;margin:0 auto;">
<p><em>Caption: this image should be full width.</em></p>
</div>

Two-column text after the div. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

## Section 3d: Raw HTML img inside div.full-width (EXPECTED PASS — full width, two-col resumes)

Two-column text before the div.

<div class="full-width">
<img src="images/test_img1.png" alt="Test image — raw HTML img inside div.full-width" style="max-width:100%;display:block;margin:0 auto;">
<p><em>Caption: div.full-width — two-column flow should resume after.</em></p>
</div>

Two-column text after the div. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

## Section 4: HTML table inside div.single-column

Two-column text before the div.

<div class="single-column">
<table>
<thead><tr><th>Actor</th><th>Role</th><th>Notes</th></tr></thead>
<tbody>
<tr><td>Alice</td><td>Lead analyst</td><td>Section 4 — HTML table inside div.single-column</td></tr>
<tr><td>Bob</td><td>Support</td><td>This table is raw HTML, not Markdown</td></tr>
<tr><td>Carol</td><td>Field officer</td><td>Should span full width</td></tr>
<tr><td>Dave</td><td>Coordinator</td><td>And text after should return to two columns</td></tr>
</tbody>
</table>

This prose is also inside div.single-column — should be full width. Lorem ipsum dolor sit amet.
</div>

Two-column text after the div. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

## Section 5: HTML table inside div.full-width

Two-column text before the div.

<div class="full-width">
<table>
<thead><tr><th>Actor</th><th>Role</th><th>Notes</th></tr></thead>
<tbody>
<tr><td>Alice</td><td>Lead analyst</td><td>Section 5 — HTML table inside div.full-width</td></tr>
<tr><td>Bob</td><td>Support</td><td>This table is raw HTML, not Markdown</td></tr>
<tr><td>Carol</td><td>Field officer</td><td>Should span full width</td></tr>
<tr><td>Dave</td><td>Coordinator</td><td>Two-column flow should resume after the div</td></tr>
</tbody>
</table>
</div>

Two-column text after the div. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

## Section 6: Mermaid diagram (no wrapper)

Two-column text before the diagram.

```mermaid
flowchart LR
  A[Alice] --> B[Bob]
  B --> C[Carol]
  C --> D[Dave]
  A --> D
```

Two-column text after the diagram. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

## Section 7: Mermaid diagram inside div.single-column

Two-column text before the div.

<div class="single-column">

This prose is inside div.single-column before the diagram. Lorem ipsum dolor sit amet.

```mermaid
flowchart LR
  A[Alice] --> B[Bob]
  B --> C[Carol]
  C --> D[Dave]
```

This prose is inside div.single-column after the diagram. Lorem ipsum dolor sit amet.

</div>

Two-column text after the div. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

## Section 8: Prose-only div.single-column

Two-column text before the div.

<div class="single-column">

This is prose-only content inside div.single-column. No tables, no images, no diagrams. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

- Item one in a list
- Item two in a list
- Item three in a list

More prose after the list. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

</div>

Two-column text after the div. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

## Section 9: Key Takeaways box (existing class)

Two-column text before the box.

<div class="key-takeaways">
<h2>Key Takeaways</h2>
<p class="scope-note"><em>Scope note: this is the existing key-takeaways class — should already span full width.</em></p>
<ul>
<li>Finding one: the bare table in Section 2 works.</li>
<li>Finding two: HTML tables inside divs — see Sections 4 and 5.</li>
<li>Finding three: Mermaid diagrams — see Sections 6 and 7.</li>
</ul>
</div>

Two-column text after the box. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

## Section 10: Two columns confirmed

Final two-column section. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident.
