// intelligence.typ — US Intelligence Community report style for md_to_typst
//
// Modelled on US IC-style analytical reports (two-column, serif body,
// navy + gold accent palette). Defaults to DRASTIC branding.
//
// Usage:
//   #import "styles/intelligence.typ": doc
//   #show: doc.with(
//     author: "Author Name",
//     title: "Article Title",
//     pub-name: "DRASTIC",
//     doc-type: "OSINT RESEARCH PRODUCT",
//   )

// ── Colour palette ──────────────────────────────────────────────────────────
#let navy        = rgb("#1d4b7a")
#let gold        = rgb("#c8a84b")
#let box-blue    = rgb("#d0dce8")
#let box-cream   = rgb("#f5f0dc")
#let stripe      = rgb("#e8eef4")
#let rule-light  = rgb("#c8d4e0")
#let faint       = rgb("#555555")
#let body-black  = rgb("#1a1a1a")
#let highlight   = rgb("#c0392b")
#let bg-code     = rgb("#f2f2f2")

// ── Font families ───────────────────────────────────────────────────────────
#let font-body   = ("Palatino", "Palatino Linotype", "Book Antiqua", "Georgia", "Times New Roman", "serif")
#let font-mono   = ("Source Code Pro", "Courier New", "monospace")

// ── Typography tunables ─────────────────────────────────────────────────────
#let body-size       = 9.5pt    // body text size
#let body-leading    = 0.65em   // inter-line gap (≈1.6× line height at 9.5pt)
#let body-spacing    = 1.4em    // inter-paragraph gap (visibly larger than leading)
#let list-spacing    = 0.9em    // gap between bullet/enum items
#let header-size     = 11pt     // running header text size
#let footer-size     = 7.5pt    // running footer text size
#let h1-size         = 16pt
#let h1-above        = 1.0em
#let h1-below        = 0.6em
#let h2-size         = 11pt
#let h2-above        = 1.6em
#let h2-below        = 0.5em
#let h3-size         = 10.5pt   // visibly larger than body (9.5pt)
#let h3-above        = 1.4em
#let h3-below        = 0.5em
#let h4-size         = 9.5pt
#let h4-above        = 1.0em
#let h4-below        = 0.5em

// ── Page geometry ───────────────────────────────────────────────────────────
#let page-paper      = "a4"
#let page-margin     = (top: 3.2cm, bottom: 2.5cm, left: 2cm, right: 2cm)

// ── Main template function ──────────────────────────────────────────────────
#let doc(
  author:   "Author Name",
  title:    "Article Title",
  pub-name: "DRASTIC",
  doc-type: "OSINT RESEARCH PRODUCT",
  justify:  true,
  body,
) = {

  // ── Page setup ────────────────────────────────────────────────────────────
  set page(
    paper:  page-paper,
    margin: page-margin,
    header: context {
      // Suppress header on first page
      if counter(page).get().first() == 1 { return }
      set text(font: font-body, size: header-size, weight: "bold", fill: navy)
      grid(
        columns: (1fr, 1fr),
        align: (left, right),
        pub-name,
        doc-type,
      )
      v(4pt)
      line(length: 100%, stroke: 1.2pt + navy)
    },
    footer: context {
      if counter(page).get().first() == 1 { return }
      set text(font: font-body, size: footer-size, fill: faint)
      let pg     = counter(page).display()
      let total  = counter(page).final().first()
      grid(
        columns: (1fr, 1fr, 1fr),
        align: (left, center, right),
        author,
        "[ " + pg + "/" + str(total) + " ]",
        emph(title),
      )
    },
  )

  // ── Base typography ───────────────────────────────────────────────────────
  set text(
    font:      font-body,
    size:      body-size,
    fill:      body-black,
    lang:      "en",
    hyphenate: true,
  )
  set par(
    justify: justify,
    leading: body-leading,
    spacing: body-spacing,
  )

  // ── Heading styles ────────────────────────────────────────────────────────
  // h1 — document/chapter title: 16pt bold navy, full-width, gold rule below
  show heading.where(level: 1): it => {
    set text(size: h1-size, weight: "bold", fill: navy)
    set align(left)
    block(width: 100%, above: h1-above, below: h1-below)[
      #it.body
      #v(3pt)
      #line(length: 100%, stroke: 2.5pt + navy)
    ]
  }

  // h2 — section heading: bold navy, navy rule below
  show heading.where(level: 2): it => {
    set text(size: h2-size, weight: "bold", fill: navy)
    set align(left)
    block(width: 100%, above: h2-above, below: h2-below)[
      #it.body
      #v(1pt)
      #line(length: 100%, stroke: 0.8pt + navy)
    ]
  }

  // h3 — sub-section: bold navy, no rule
  show heading.where(level: 3): it => {
    set text(size: h3-size, weight: "bold", fill: navy)
    set align(left)
    block(above: h3-above, below: h3-below, it.body)
  }

  // h4 — minor heading: bold italic black
  show heading.where(level: 4): it => {
    set text(size: h4-size, weight: "bold", style: "italic", fill: body-black)
    set align(left)
    block(above: h4-above, below: h4-below, it.body)
  }

  // h5/h6 — same as h4
  show heading.where(level: 5): it => {
    set text(size: h4-size, weight: "bold", style: "italic", fill: body-black)
    set align(left)
    block(above: h4-above, below: h4-below, it.body)
  }
  show heading.where(level: 6): it => {
    set text(size: h4-size, weight: "bold", style: "italic", fill: body-black)
    set align(left)
    block(above: h4-above, below: h4-below, it.body)
  }

  // ── Code ──────────────────────────────────────────────────────────────────
  show raw.where(block: false): it => {
    box(
      fill:    bg-code,
      inset:   (x: 2pt, y: 1pt),
      radius:  1.5pt,
      text(font: font-mono, size: 8pt, it),
    )
  }
  show raw.where(block: true): it => {
    block(
      width:  100%,
      fill:   bg-code,
      inset:  (x: 8pt, y: 6pt),
      stroke: (left: 2.5pt + navy),
      text(font: font-mono, size: 8pt, it),
    )
  }

  // ── Links ─────────────────────────────────────────────────────────────────
  show link: it => {
    set text(fill: navy)
    it
  }

  // ── Block quotes ──────────────────────────────────────────────────────────
  show quote.where(block: true): it => {
    pad(left: 1.2em,
      block(
        stroke: (left: 2.5pt + navy),
        inset:  (left: 0.8em, top: 0.4em, bottom: 0.4em),
        text(style: "italic", fill: rgb("#333333"), it.body),
      )
    )
  }

  // ── Lists ─────────────────────────────────────────────────────────────────
  set list(
    marker:  text(fill: navy, weight: "bold")[ • ],
    indent:  1.4em,
    spacing: list-spacing,
  )
  set enum(
    indent:  1.4em,
    spacing: list-spacing,
  )

  // ── Figures / images ──────────────────────────────────────────────────────
  set figure(gap: 0.5em)
  show figure.caption: it => {
    set text(size: 8pt, style: "italic", fill: faint)
    align(center, it)
  }

  // ── Footnotes ─────────────────────────────────────────────────────────────
  set footnote.entry(
    gap:    0.4em,
    indent: 1em,
  )
  show footnote.entry: it => {
    set text(size: 7.5pt, fill: faint)
    it
  }

  // ── Horizontal rules ──────────────────────────────────────────────────────
  // (line() calls emitted by convert.py are already styled; this catches
  //  any raw Typst line elements with default stroke)

  // ── Body ─────────────────────────────────────────────────────────────────
  // Two-column layout is managed by the converter: each run of column content
  // is wrapped in #columns(2, gutter: 0.5cm)[...], and full-width blocks
  // (div.single-column, div.full-width) live outside those wrappers.
  body
}


// ── Reusable block helpers (called from convert.py output) ─────────────────

// Key-takeaways box: light-blue bg, navy top+bottom border.
// Renders a "Key Takeaways" label with full-width underline rule,
// then the body (first paragraph treated as scope note in italic by caller).
#let key-takeaways(scope-note: none, body) = block(
  width:  100%,
  fill:   box-blue,
  stroke: (top: 3pt + navy, bottom: 3pt + navy),
  inset:  (x: 1em, top: 0.7em, bottom: 0.8em),
  above:  0.8em,
  below:  1.2em,
  {
    // Label
    text(size: 10pt, weight: "bold", fill: navy)[Key Takeaways]
    v(3pt)
    line(length: 100%, stroke: 0.7pt + navy)
    v(5pt)
    // Optional scope note in italic
    if scope-note != none {
      text(style: "italic", scope-note)
      v(4pt)
    }
    body
  },
)

// Insights box: warm cream bg, gold top+bottom border, bold black heading,
// gold rule under the heading.
// Usage: #insights-box(heading: [Title])[body content]
#let insights-box(heading: none, body) = block(
  width:    100%,
  fill:     box-cream,
  stroke:   (top: 3pt + gold, bottom: 1.5pt + gold),
  inset:    (x: 1em, top: 0.8em, bottom: 0.8em),
  above:    0.9em,
  below:    1em,
  {
    if heading != none {
      text(size: 9.5pt, weight: "bold", fill: body-black, heading)
      v(2pt)
      line(length: 100%, stroke: 0.6pt + gold)
      v(5pt)
    }
    body
  },
)

// Pull-quote block: italic, indented, navy left border + gold source rule
#let pull-quote(body, source: none) = pad(
  left: 1.2em,
  block(
    stroke: (left: 3pt + navy),
    fill:   stripe,
    inset:  (left: 0.8em, top: 0.5em, bottom: 0.5em, right: 0.5em),
    above:  1em,
    below:  1em,
    {
      text(style: "italic", body)
      if source != none {
        v(3pt)
        line(length: 100%, stroke: 0.5pt + gold)
        v(2pt)
        text(size: 8pt, style: "normal", fill: faint, source)
      }
    },
  )
)

// GFM callout — NOTE / TIP style (blue box)
#let callout-note(label-text: "Note", body) = block(
  width:   100%,
  fill:    box-blue,
  stroke:  (top: 3pt + navy, bottom: 3pt + navy),
  inset:   (x: 0.9em, top: 0.6em, bottom: 0.5em),
  above:   1em,
  below:   1em,
  {
    text(size: 8pt, weight: "bold", fill: navy, upper(label-text))
    linebreak()
    body
  },
)

// GFM callout — WARNING / CAUTION style (cream box, gold border)
#let callout-warning(label-text: "Warning", body) = block(
  width:   100%,
  fill:    box-cream,
  stroke:  (left: 4pt + gold, top: 2pt + navy),
  inset:   (left: 0.8em, right: 0.9em, top: 0.6em, bottom: 0.5em),
  above:   1em,
  below:   1em,
  {
    text(size: 8pt, weight: "bold", fill: navy, upper(label-text))
    linebreak()
    body
  },
)

// Generic callout dispatcher — used when type is not specifically NOTE/WARNING
#let callout(label-text: "Note", style: "note", body) = {
  if style == "warning" or style == "caution" or style == "important" {
    callout-warning(label-text: label-text, body)
  } else {
    callout-note(label-text: label-text, body)
  }
}

// Mermaid diagram placeholder
#let mermaid-placeholder(n) = block(
  width:   100%,
  fill:    stripe,
  stroke:  (paint: rule-light, thickness: 1pt, dash: "dashed"),
  inset:   (x: 0.9em, y: 0.7em),
  above:   0.9em,
  below:   0.9em,
  align(center,
    text(size: 8pt, style: "italic", fill: faint,
      [Diagram #n — install mermaid-cli to render]
    )
  )
)

// Styled table helper (used by convert.py for pipe tables)
// Wraps #table() with navy header styling and stripe fill.
// convert.py emits raw #table() with fill: and header styling directly;
// this helper is available for manual use if needed.
#let intel-table(columns: auto, headers: (), rows: ()) = {
  let header-cells = headers.map(h =>
    table.cell(fill: navy)[#text(fill: white, weight: "bold", h)]
  )
  let all-cells = header-cells
  for (i, row) in rows.enumerate() {
    let bg = if calc.rem(i, 2) == 1 { stripe } else { white }
    for cell in row {
      all-cells.push(table.cell(fill: bg)[#cell])
    }
  }
  set text(size: 8.5pt)
  table(
    columns: columns,
    stroke:  none,
    inset:   (x: 0.55em, y: 0.35em),
    ..all-cells,
  )
}
