#import "/sessions/zealous-cool-ride/mnt/Edition/md_to_pdf/engines/typst/styles/intelligence.typ": doc, key-takeaways, insights-box, pull-quote, callout, callout-note, callout-warning, mermaid-placeholder

#show: doc.with(
  author:   "Author Name",
  title:    "Article Title",
  pub-name: "DRASTIC",
  doc-type: "OSINT RESEARCH PRODUCT",
  justify:  true,
)

= Image Caption Test

#columns(2, gutter: 0.5cm)[
This paragraph precedes the image.

#figure(
  image("/sessions/zealous-cool-ride/mnt/Edition/md_to_pdf/tests/shared/test_columns/images/test_img1.png", width: 100%),
  caption: [A simple image with no footnote.],
)

This paragraph follows after a blank line.

#figure(
  image("/sessions/zealous-cool-ride/mnt/Edition/md_to_pdf/tests/shared/test_columns/images/test_img1.png", width: 100%),
  caption: [Image caption with footnote reference.#link(<en-myref>)[#text(size: 6pt, baseline: -5pt)[1]]],
)

Another paragraph after.
]

#pagebreak()
// ── Endnotes ──────────────────────────────────────────────────────────────
#text(size: 11pt, weight: "bold", fill: rgb("#1d4b7a"))[Notes]
#v(2pt)
#line(length: 100%, stroke: 0.8pt + rgb("#1d4b7a"))
#v(0.5em)
#block(height: 0pt, above: 0pt, below: 0pt)[] <en-myref>
#block(below: 1.2em, inset: (left: 1.8em), clip: false)[#pad(left: -1.8em)[#text(size: 8.5pt)[1.#h(0.4em)This is the footnote definition for the image caption.]]]