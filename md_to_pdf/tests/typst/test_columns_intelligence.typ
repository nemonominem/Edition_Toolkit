#import "/Users/gillesdemaneuf/Work/Edition/md_to_pdf/engines/typst/styles/intelligence.typ": doc, key-takeaways, insights-box, pull-quote, callout, callout-note, callout-warning, mermaid-placeholder

#show: doc.with(
  author:   "Author Name",
  title:    "Article Title",
  pub-name: "DRASTIC",
  doc-type: "OSINT RESEARCH PRODUCT",
  justify:  true,
)

= Column Layout Test

#columns(2, gutter: 0.5cm)[
_Testing column-span behaviour in WeasyPrint — comprehensive._

== Section 1: Normal Two-Column Flow

This is normal two-column body text. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.

More two-column text. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium.

== Section 2: Bare Markdown Table (no wrapper)

Two-column text before the table.
]

#block(width: 100%)[
#set text(size: 8.5pt)  // tables slightly smaller than body
#table(
  columns: (1fr, 1fr, 1fr),
  stroke: none,
  inset: (x: 0.55em, y: 0.35em),
  table.cell(fill: rgb("#1d4b7a"), align: left)[#text(fill: white, weight: "bold")[Actor]],
  table.cell(fill: rgb("#1d4b7a"), align: left)[#text(fill: white, weight: "bold")[Role]],
  table.cell(fill: rgb("#1d4b7a"), align: left)[#text(fill: white, weight: "bold")[Confidence]],
  table.cell(fill: white, align: left)[Alice],
  table.cell(fill: white, align: left)[Lead analyst],
  table.cell(fill: white, align: left)[High],
  table.cell(fill: rgb("#e8eef4"), align: left)[Bob],
  table.cell(fill: rgb("#e8eef4"), align: left)[Support],
  table.cell(fill: rgb("#e8eef4"), align: left)[Medium],
  table.cell(fill: white, align: left)[Carol],
  table.cell(fill: white, align: left)[Field officer],
  table.cell(fill: white, align: left)[Low],
  table.cell(fill: rgb("#e8eef4"), align: left)[Dave],
  table.cell(fill: rgb("#e8eef4"), align: left)[Coordinator],
  table.cell(fill: rgb("#e8eef4"), align: left)[High],
)
]

#columns(2, gutter: 0.5cm)[
Two-column text after the bare table. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

== Section 3: Bare Markdown Image (no wrapper — stays column-width)

Two-column text before the image.

#figure(
  image("/Users/gillesdemaneuf/Work/Edition/md_to_pdf/tests/shared/images/test_img1.png", width: 100%),
  caption: [Test image — bare Markdown syntax, stays column-width],
)

Two-column text after the bare image. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

== Section 3e: WORKING single-column image (raw HTML img + div.single-column)

Two-column text before the div. This is the canonical working pattern for full-width images.
]

#figure(image("/Users/gillesdemaneuf/Work/Edition/md_to_pdf/tests/shared/images/test_img1.png", width: 100%), caption: [Full-width image — working pattern]) Fig. 1 — This image spans the full page width using raw HTML img inside div.single-column.

#columns(2, gutter: 0.5cm)[
Two-column text resumes here after the full-width image. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

== Section 3b: Markdown image inside div.single-column (EXPECTED FAIL)

Two-column text before the div.
]

#figure(
  image("/Users/gillesdemaneuf/Work/Edition/md_to_pdf/tests/shared/images/test_img1.png", width: 100%),
  caption: [Test image — Markdown syntax inside div — will NOT render],
)

#columns(2, gutter: 0.5cm)[
Two-column text after the div. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

== Section 3c: Raw HTML img inside div.single-column (EXPECTED PASS — full width)

Two-column text before the div.
]

#figure(image("/Users/gillesdemaneuf/Work/Edition/md_to_pdf/tests/shared/images/test_img1.png", width: 100%), caption: [Test image — raw HTML img, full width]) _Caption: this image should be full width._

#columns(2, gutter: 0.5cm)[
Two-column text after the div. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

== Section 3d: Raw HTML img inside div.full-width (EXPECTED PASS — full width, two-col resumes)

Two-column text before the div.
]

#figure(image("/Users/gillesdemaneuf/Work/Edition/md_to_pdf/tests/shared/images/test_img1.png", width: 100%), caption: [Test image — raw HTML img inside div.full-width]) _Caption: div.full-width — two-column flow should resume after._

#columns(2, gutter: 0.5cm)[
Two-column text after the div. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

== Section 4: HTML table inside div.single-column

Two-column text before the div.
]

ActorRoleNotes  AliceLead analystSection 4 — HTML table inside div.single-column BobSupportThis table is raw HTML, not Markdown CarolField officerShould span full width DaveCoordinatorAnd text after should return to two columns  

This prose is also inside div.single-column — should be full width. Lorem ipsum dolor sit amet.

#columns(2, gutter: 0.5cm)[
Two-column text after the div. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

== Section 5: HTML table inside div.full-width

Two-column text before the div.
]

ActorRoleNotes  AliceLead analystSection 5 — HTML table inside div.full-width BobSupportThis table is raw HTML, not Markdown CarolField officerShould span full width DaveCoordinatorTwo-column flow should resume after the div

#columns(2, gutter: 0.5cm)[
Two-column text after the div. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

== Section 6: Mermaid diagram (no wrapper)

Two-column text before the diagram.

#figure(
  image("/Users/gillesdemaneuf/Work/Edition/md_to_pdf/tests/shared/images/_mermaid_1.png", width: 100%),
  caption: [Diagram 1],
)

Two-column text after the diagram. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

== Section 7: Mermaid diagram inside div.single-column

Two-column text before the div.
]

This prose is inside div.single-column before the diagram. Lorem ipsum dolor sit amet.

#figure(
  image("/Users/gillesdemaneuf/Work/Edition/md_to_pdf/tests/shared/images/_mermaid_2.png", width: 100%),
  caption: [Diagram 2],
)

This prose is inside div.single-column after the diagram. Lorem ipsum dolor sit amet.

#columns(2, gutter: 0.5cm)[
Two-column text after the div. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

== Section 8: Prose-only div.single-column

Two-column text before the div.
]

This is prose-only content inside div.single-column. No tables, no images, no diagrams. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

- Item one in a list
- Item two in a list
- Item three in a list

More prose after the list. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

#columns(2, gutter: 0.5cm)[
Two-column text after the div. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

== Section 9: Key Takeaways box (existing class)

Two-column text before the box.

#key-takeaways[
Key Takeaways _Scope note: this is the existing key-takeaways class — should already span full width._  Finding one: the bare table in Section 2 works. Finding two: HTML tables inside divs — see Sections 4 and 5. Finding three: Mermaid diagrams — see Sections 6 and 7. 
]

Two-column text after the box. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

== Section 10: Two columns confirmed

Final two-column section. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident.

== Section 11: Large Markdown table inside div.full-width (EXPECTED: full-width, no crash)

Two-column text before the div.
]

#block(width: 100%)[
#set text(size: 8.5pt)  // tables slightly smaller than body
#table(
  columns: (1fr, 1fr, 1fr, 1fr),
  stroke: none,
  inset: (x: 0.55em, y: 0.35em),
  table.cell(fill: rgb("#1d4b7a"), align: left)[#text(fill: white, weight: "bold")[Actor]],
  table.cell(fill: rgb("#1d4b7a"), align: left)[#text(fill: white, weight: "bold")[Role]],
  table.cell(fill: rgb("#1d4b7a"), align: left)[#text(fill: white, weight: "bold")[Organisation]],
  table.cell(fill: rgb("#1d4b7a"), align: left)[#text(fill: white, weight: "bold")[Notes]],
  table.cell(fill: white, align: left)[Row 01],
  table.cell(fill: white, align: left)[Lead analyst],
  table.cell(fill: white, align: left)[WHO],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 02],
  table.cell(fill: rgb("#e8eef4"), align: left)[Support],
  table.cell(fill: rgb("#e8eef4"), align: left)[UNAIDS],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 03],
  table.cell(fill: white, align: left)[Field officer],
  table.cell(fill: white, align: left)[CDC],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 04],
  table.cell(fill: rgb("#e8eef4"), align: left)[Coordinator],
  table.cell(fill: rgb("#e8eef4"), align: left)[ECDC],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 05],
  table.cell(fill: white, align: left)[Director],
  table.cell(fill: white, align: left)[NIH],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 06],
  table.cell(fill: rgb("#e8eef4"), align: left)[Adviser],
  table.cell(fill: rgb("#e8eef4"), align: left)[Wellcome],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 07],
  table.cell(fill: white, align: left)[Researcher],
  table.cell(fill: white, align: left)[EcoHealth],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 08],
  table.cell(fill: rgb("#e8eef4"), align: left)[Analyst],
  table.cell(fill: rgb("#e8eef4"), align: left)[DARPA],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 09],
  table.cell(fill: white, align: left)[Observer],
  table.cell(fill: white, align: left)[State Dept],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 10],
  table.cell(fill: rgb("#e8eef4"), align: left)[Consultant],
  table.cell(fill: rgb("#e8eef4"), align: left)[WEF],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 11],
  table.cell(fill: white, align: left)[Lead analyst],
  table.cell(fill: white, align: left)[WHO],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 12],
  table.cell(fill: rgb("#e8eef4"), align: left)[Support],
  table.cell(fill: rgb("#e8eef4"), align: left)[UNAIDS],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 13],
  table.cell(fill: white, align: left)[Field officer],
  table.cell(fill: white, align: left)[CDC],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 14],
  table.cell(fill: rgb("#e8eef4"), align: left)[Coordinator],
  table.cell(fill: rgb("#e8eef4"), align: left)[ECDC],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 15],
  table.cell(fill: white, align: left)[Director],
  table.cell(fill: white, align: left)[NIH],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 16],
  table.cell(fill: rgb("#e8eef4"), align: left)[Adviser],
  table.cell(fill: rgb("#e8eef4"), align: left)[Wellcome],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 17],
  table.cell(fill: white, align: left)[Researcher],
  table.cell(fill: white, align: left)[EcoHealth],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 18],
  table.cell(fill: rgb("#e8eef4"), align: left)[Analyst],
  table.cell(fill: rgb("#e8eef4"), align: left)[DARPA],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 19],
  table.cell(fill: white, align: left)[Observer],
  table.cell(fill: white, align: left)[State Dept],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 20],
  table.cell(fill: rgb("#e8eef4"), align: left)[Consultant],
  table.cell(fill: rgb("#e8eef4"), align: left)[WEF],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
)
]

#columns(2, gutter: 0.5cm)[
Two-column text resumes after Section 11. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

== Section 12: Large Markdown table inside div.single-column (EXPECTED: single-column, no crash)

Two-column text before the div.
]

#block(width: 100%)[
#set text(size: 8.5pt)  // tables slightly smaller than body
#table(
  columns: (1fr, 1fr, 1fr, 1fr),
  stroke: none,
  inset: (x: 0.55em, y: 0.35em),
  table.cell(fill: rgb("#1d4b7a"), align: left)[#text(fill: white, weight: "bold")[Actor]],
  table.cell(fill: rgb("#1d4b7a"), align: left)[#text(fill: white, weight: "bold")[Role]],
  table.cell(fill: rgb("#1d4b7a"), align: left)[#text(fill: white, weight: "bold")[Organisation]],
  table.cell(fill: rgb("#1d4b7a"), align: left)[#text(fill: white, weight: "bold")[Notes]],
  table.cell(fill: white, align: left)[Row 01],
  table.cell(fill: white, align: left)[Lead analyst],
  table.cell(fill: white, align: left)[WHO],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 02],
  table.cell(fill: rgb("#e8eef4"), align: left)[Support],
  table.cell(fill: rgb("#e8eef4"), align: left)[UNAIDS],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 03],
  table.cell(fill: white, align: left)[Field officer],
  table.cell(fill: white, align: left)[CDC],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 04],
  table.cell(fill: rgb("#e8eef4"), align: left)[Coordinator],
  table.cell(fill: rgb("#e8eef4"), align: left)[ECDC],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 05],
  table.cell(fill: white, align: left)[Director],
  table.cell(fill: white, align: left)[NIH],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 06],
  table.cell(fill: rgb("#e8eef4"), align: left)[Adviser],
  table.cell(fill: rgb("#e8eef4"), align: left)[Wellcome],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 07],
  table.cell(fill: white, align: left)[Researcher],
  table.cell(fill: white, align: left)[EcoHealth],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 08],
  table.cell(fill: rgb("#e8eef4"), align: left)[Analyst],
  table.cell(fill: rgb("#e8eef4"), align: left)[DARPA],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 09],
  table.cell(fill: white, align: left)[Observer],
  table.cell(fill: white, align: left)[State Dept],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 10],
  table.cell(fill: rgb("#e8eef4"), align: left)[Consultant],
  table.cell(fill: rgb("#e8eef4"), align: left)[WEF],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 11],
  table.cell(fill: white, align: left)[Lead analyst],
  table.cell(fill: white, align: left)[WHO],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 12],
  table.cell(fill: rgb("#e8eef4"), align: left)[Support],
  table.cell(fill: rgb("#e8eef4"), align: left)[UNAIDS],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 13],
  table.cell(fill: white, align: left)[Field officer],
  table.cell(fill: white, align: left)[CDC],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 14],
  table.cell(fill: rgb("#e8eef4"), align: left)[Coordinator],
  table.cell(fill: rgb("#e8eef4"), align: left)[ECDC],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 15],
  table.cell(fill: white, align: left)[Director],
  table.cell(fill: white, align: left)[NIH],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 16],
  table.cell(fill: rgb("#e8eef4"), align: left)[Adviser],
  table.cell(fill: rgb("#e8eef4"), align: left)[Wellcome],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 17],
  table.cell(fill: white, align: left)[Researcher],
  table.cell(fill: white, align: left)[EcoHealth],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 18],
  table.cell(fill: rgb("#e8eef4"), align: left)[Analyst],
  table.cell(fill: rgb("#e8eef4"), align: left)[DARPA],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 19],
  table.cell(fill: white, align: left)[Observer],
  table.cell(fill: white, align: left)[State Dept],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 20],
  table.cell(fill: rgb("#e8eef4"), align: left)[Consultant],
  table.cell(fill: rgb("#e8eef4"), align: left)[WEF],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
)
]

#columns(2, gutter: 0.5cm)[
Two-column text resumes after Section 12. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

== Section 13: Large standalone Markdown table (EXPECTED: full-width span, no crash)

Two-column text before the table. No div wrapper — the table CSS applies column-span:all directly.
]

#block(width: 100%)[
#set text(size: 8.5pt)  // tables slightly smaller than body
#table(
  columns: (1fr, 1fr, 1fr, 1fr),
  stroke: none,
  inset: (x: 0.55em, y: 0.35em),
  table.cell(fill: rgb("#1d4b7a"), align: left)[#text(fill: white, weight: "bold")[Actor]],
  table.cell(fill: rgb("#1d4b7a"), align: left)[#text(fill: white, weight: "bold")[Role]],
  table.cell(fill: rgb("#1d4b7a"), align: left)[#text(fill: white, weight: "bold")[Organisation]],
  table.cell(fill: rgb("#1d4b7a"), align: left)[#text(fill: white, weight: "bold")[Notes]],
  table.cell(fill: white, align: left)[Row 01],
  table.cell(fill: white, align: left)[Lead analyst],
  table.cell(fill: white, align: left)[WHO],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 02],
  table.cell(fill: rgb("#e8eef4"), align: left)[Support],
  table.cell(fill: rgb("#e8eef4"), align: left)[UNAIDS],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 03],
  table.cell(fill: white, align: left)[Field officer],
  table.cell(fill: white, align: left)[CDC],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 04],
  table.cell(fill: rgb("#e8eef4"), align: left)[Coordinator],
  table.cell(fill: rgb("#e8eef4"), align: left)[ECDC],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 05],
  table.cell(fill: white, align: left)[Director],
  table.cell(fill: white, align: left)[NIH],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 06],
  table.cell(fill: rgb("#e8eef4"), align: left)[Adviser],
  table.cell(fill: rgb("#e8eef4"), align: left)[Wellcome],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 07],
  table.cell(fill: white, align: left)[Researcher],
  table.cell(fill: white, align: left)[EcoHealth],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 08],
  table.cell(fill: rgb("#e8eef4"), align: left)[Analyst],
  table.cell(fill: rgb("#e8eef4"), align: left)[DARPA],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 09],
  table.cell(fill: white, align: left)[Observer],
  table.cell(fill: white, align: left)[State Dept],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 10],
  table.cell(fill: rgb("#e8eef4"), align: left)[Consultant],
  table.cell(fill: rgb("#e8eef4"), align: left)[WEF],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 11],
  table.cell(fill: white, align: left)[Lead analyst],
  table.cell(fill: white, align: left)[WHO],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 12],
  table.cell(fill: rgb("#e8eef4"), align: left)[Support],
  table.cell(fill: rgb("#e8eef4"), align: left)[UNAIDS],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 13],
  table.cell(fill: white, align: left)[Field officer],
  table.cell(fill: white, align: left)[CDC],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 14],
  table.cell(fill: rgb("#e8eef4"), align: left)[Coordinator],
  table.cell(fill: rgb("#e8eef4"), align: left)[ECDC],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 15],
  table.cell(fill: white, align: left)[Director],
  table.cell(fill: white, align: left)[NIH],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 16],
  table.cell(fill: rgb("#e8eef4"), align: left)[Adviser],
  table.cell(fill: rgb("#e8eef4"), align: left)[Wellcome],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 17],
  table.cell(fill: white, align: left)[Researcher],
  table.cell(fill: white, align: left)[EcoHealth],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 18],
  table.cell(fill: rgb("#e8eef4"), align: left)[Analyst],
  table.cell(fill: rgb("#e8eef4"), align: left)[DARPA],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: white, align: left)[Row 19],
  table.cell(fill: white, align: left)[Observer],
  table.cell(fill: white, align: left)[State Dept],
  table.cell(fill: white, align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
  table.cell(fill: rgb("#e8eef4"), align: left)[Row 20],
  table.cell(fill: rgb("#e8eef4"), align: left)[Consultant],
  table.cell(fill: rgb("#e8eef4"), align: left)[WEF],
  table.cell(fill: rgb("#e8eef4"), align: left)[Long cell content to make rows tall: Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor.],
)
]

#columns(2, gutter: 0.5cm)[
Two-column text resumes after Section 13. Lorem ipsum dolor sit amet, consectetur adipiscing elit.

== Section 14: Footnote rendering tests

=== 14a: Footnote in normal flow (EXPECTED: superscript number)

This sentence has a footnote in normal two-column flow.#footnote[This is the footnote definition for Section 14a — normal flow.] And this sentence has a second footnote also in normal flow.#footnote[This is the second footnote definition for Section 14a.]

=== 14b: Same footnote key used twice (EXPECTED: both render as superscript)

First use of a repeated key.#footnote[This footnote is referenced twice in Section 14b.] Some text between. Second use of the same key.#footnote[This footnote is referenced twice in Section 14b.]

=== 14c: Footnote inside pull-quote (EXPECTED: superscript in blockquote)

#pull-quote(source: [Test source, 2024.])["This is a pull-quote with a footnote ref inside it."#footnote[This footnote is referenced inside a pull-quote and after it in Section 14c.]]

Text after the pull-quote with a ref to the same key.#footnote[This footnote is referenced inside a pull-quote and after it in Section 14c.]

=== 14d: Footnote ref inside div.single-column (EXPECTED: superscript)
]

This text is inside div.single-column and has a footnote.#footnote[This footnote is referenced inside div.single-column and after it in Section 14d.] The ref should render as a superscript number, not as literal text.

#columns(2, gutter: 0.5cm)[
Text after the div with same key.#footnote[This footnote is referenced inside div.single-column and after it in Section 14d.]

=== 14e: Footnote ref inside div.full-width (EXPECTED: superscript)
]

This text is inside div.full-width and has a footnote.#footnote[This footnote is referenced inside div.full-width and after it in Section 14e.] The ref should render as a superscript number.

#columns(2, gutter: 0.5cm)[
Text after the div. Lorem ipsum dolor sit amet.

=== 14f: Image in normal flow (EXPECTED: visible, column-width)

This is text before a Markdown image in normal flow.

#figure(
  image("/Users/gillesdemaneuf/Work/Edition/md_to_pdf/tests/shared/images/test_img1.png", width: 100%),
  caption: [Test image in normal flow],
)

Text after the image.

=== 14g: Image inside div.single-column (EXPECTED: visible, full-width)
]

#figure(
  image("/Users/gillesdemaneuf/Work/Edition/md_to_pdf/tests/shared/images/test_img1.png", width: 100%),
  caption: [Test image inside div.single-column],
)

#columns(2, gutter: 0.5cm)[
Text after the div. Lorem ipsum.

== Section 15: Insights box

Two-column text before the insights box.

#insights-box(heading: [The Role of the Huanan Seafood Wholesale Market])[
Some scientists and China's public health officials have shifted their view on the role of the Huanan Seafood Wholesale Market in the pandemic since early 2020. Some now view the market as a potential site of community spread rather than where the initial human infection may have occurred.

- On January 1, 2020, China's security authorities shut down the market after several workers fell ill in late December 2019. China focused early source tracing on the market and Hubei Province.
- In January 2020, a scientific article described clinical features of initial COVID-19 infections and found that some patients did not have any known association with the market.
]

Two-column text resumes after the insights box. Lorem ipsum dolor sit amet, consectetur adipiscing elit.
]