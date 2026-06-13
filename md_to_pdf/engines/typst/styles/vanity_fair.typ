// vanity_fair.typ — Long-form investigative feature style for md_to_typst
//
// Vanity Fair print register: warm cream page, Didot display, Palatino body,
// black primary type, VF red accent used sparingly. Single column, airy margins.

// ── Colour palette ──────────────────────────────────────────────────────────
#let vf-red       = rgb("#c41230")
#let vf-black     = rgb("#111111")
#let warm-grey    = rgb("#4a4a4a")
#let faint        = rgb("#666666")
#let rule-light   = rgb("#d8d4cf")
#let page-cream   = rgb("#faf8f5")
#let quote-fill   = rgb("#f3f0eb")
#let bg-code      = rgb("#f5f5f5")

// ── Font families ───────────────────────────────────────────────────────────
#let font-body    = ("Palatino", "Georgia", "Times New Roman")
#let font-display = ("Didot", "Bodoni 72", "Baskerville", "Georgia")
#let font-sans    = ("Helvetica Neue", "Helvetica", "Arial")
#let font-mono    = ("Menlo", "Courier New")

// ── Typography tunables (overridable via sidecar typst_overrides) ───────────
#let body-size       = 11pt
#let body-leading    = 0.82em
#let body-spacing    = 0.75em
#let list-spacing    = 0.45em
#let header-size     = 8pt
#let footer-size     = 8pt
#let h1-size         = 28pt
#let h1-above        = 0em
#let h1-below        = 0.55em
#let h2-size         = 14pt
#let h2-above        = 1.8em
#let h2-below        = 0.45em
#let h3-size         = 11pt
#let h3-above        = 1.4em
#let h3-below        = 0.35em
#let h4-size         = 10.5pt
#let h4-above        = 1.1em
#let h4-below        = 0.3em
#let page-paper      = "a4"

// ── Main template function ──────────────────────────────────────────────────
#let doc(
  author:   "Author Name",
  title:    "Article Title",
  pub-name: "Edition",
  doc-type: "FEATURE",
  justify:  true,
  body,
) = {

  set page(
    paper:  page-paper,
    fill:   page-cream,
    margin: (top: 2.8cm, bottom: 2.6cm, left: 2.9cm, right: 2.9cm),
    header: context {
      if counter(page).get().first() == 1 { return }
      set text(font: font-sans, size: header-size, fill: faint, tracking: 0.08em)
      grid(
        columns: (1fr, auto),
        align: (left, right),
        upper(title),
        counter(page).display(),
      )
      v(4pt)
      line(length: 100%, stroke: 0.35pt + rule-light)
    },
    footer: none,
  )

  set text(font: font-body, size: body-size, fill: vf-black, lang: "en", hyphenate: true)
  set par(justify: justify, leading: body-leading, spacing: body-spacing, first-line-indent: 0pt)

  show heading.where(level: 1): it => {
    set text(font: font-display, size: h1-size, weight: "regular", fill: vf-black, tracking: 0.01em)
    block(width: 100%, above: h1-above, below: h1-below)[
      #it.body
      #v(8pt)
      #line(length: 4.5cm, stroke: 0.75pt + vf-black)
    ]
  }

  show heading.where(level: 2): it => {
    set text(font: font-display, size: h2-size, weight: "regular", fill: vf-black)
    block(width: 100%, above: h2-above, below: h2-below, it.body)
  }

  show heading.where(level: 3): it => {
    set text(font: font-sans, size: h3-size, weight: "bold", fill: warm-grey, tracking: 0.04em)
    block(above: h3-above, below: h3-below, upper(it.body))
  }

  show heading.where(level: 4): it => {
    set text(font: font-sans, size: h4-size, weight: "bold", style: "italic", fill: warm-grey)
    block(above: h4-above, below: h4-below, it.body)
  }

  show heading.where(level: 5): it => {
    set text(font: font-sans, size: h4-size, weight: "bold", style: "italic", fill: warm-grey)
    block(above: h4-above, below: h4-below, it.body)
  }

  show heading.where(level: 6): it => {
    set text(font: font-sans, size: h4-size, weight: "bold", style: "italic", fill: warm-grey)
    block(above: h4-above, below: h4-below, it.body)
  }

  show raw.where(block: false): it => {
    box(fill: bg-code, inset: (x: 2pt, y: 1pt), radius: 1pt,
      text(font: font-mono, size: 9pt, it))
  }
  show raw.where(block: true): it => {
    block(width: 100%, fill: bg-code, inset: (x: 8pt, y: 6pt),
      stroke: (left: 2pt + vf-black),
      text(font: font-mono, size: 9pt, it))
  }

  show link: it => { set text(fill: vf-red); it }

  show quote.where(block: true): it => {
    pad(left: 0em,
      block(
        stroke: (left: 2pt + vf-black),
        fill: quote-fill,
        inset: (left: 1.1em, right: 1.1em, top: 0.7em, bottom: 0.7em),
        text(size: 11.5pt, style: "italic", fill: warm-grey, it.body),
      )
    )
  }

  set list(marker: text(fill: vf-black)[—], indent: 1.2em, spacing: list-spacing)
  set enum(indent: 1.2em, spacing: list-spacing)

  set figure(gap: 0.45em)
  show figure.caption: it => {
    set text(font: font-sans, size: 7.5pt, style: "italic", fill: faint)
    align(left, it)
  }

  set footnote.entry(gap: 0.35em, indent: 1em)
  show footnote.entry: it => { set text(size: 8pt, fill: faint); it }

  // Title page treatment — author / pub / doc-type before body h1
  align(left)[
    #text(font: font-sans, size: 8pt, tracking: 0.14em, fill: faint, upper(pub-name))
    #v(0.35em)
    #text(font: font-sans, size: 8pt, tracking: 0.12em, fill: vf-red, upper(doc-type))
    #v(1.2em)
    #text(font: font-body, size: 10.5pt, fill: warm-grey, author)
    #v(0.2em)
    #line(length: 2.5cm, stroke: 0.5pt + rule-light)
    #v(1.4em)
  ]

  body
}

// ── Reusable block helpers (same API as magazine.typ) ───────────────────────

#let key-takeaways(scope-note: none, body) = block(
  width: 100%, fill: quote-fill,
  stroke: (top: 1.5pt + vf-black, bottom: 0.5pt + rule-light),
  inset: (x: 1.1em, top: 0.75em, bottom: 0.85em),
  above: 1em, below: 1.1em,
  {
    text(size: 9pt, weight: "bold", font: font-sans, tracking: 0.1em, fill: vf-black)[KEY POINTS]
    v(4pt)
    line(length: 100%, stroke: 0.4pt + rule-light)
    v(6pt)
    if scope-note != none { text(style: "italic", size: 9.5pt, scope-note); v(4pt) }
    body
  },
)

#let insights-box(heading: none, body) = block(
  width: 100%, fill: white,
  stroke: (left: 2pt + vf-black),
  inset: (x: 1em, top: 0.7em, bottom: 0.7em),
  above: 0.9em, below: 1em,
  {
    if heading != none {
      text(size: 10pt, weight: "bold", font: font-sans, fill: vf-black, heading)
      v(3pt)
      line(length: 100%, stroke: 0.4pt + rule-light)
      v(5pt)
    }
    body
  },
)

#let pull-quote(body, source: none) = pad(
  left: 0.8em, right: 0.8em,
  block(
    above: 1.4em, below: 1.4em,
    align(center)[
      #line(length: 30%, stroke: 0.5pt + rule-light)
      #v(0.6em)
      #text(font: font-display, size: 15pt, style: "italic", fill: vf-black, body)
      #v(0.6em)
      #line(length: 30%, stroke: 0.5pt + rule-light)
      if source != none {
        v(0.5em)
        text(size: 8pt, style: "normal", fill: faint, source)
      }
    ],
  )
)

#let callout-note(label-text: "Note", body) = block(
  width: 100%, fill: quote-fill,
  stroke: (left: 2pt + vf-black),
  inset: (left: 0.9em, right: 0.9em, top: 0.55em, bottom: 0.5em),
  above: 1em, below: 1em,
  {
    text(size: 8pt, weight: "bold", font: font-sans, tracking: 0.08em, fill: vf-black, upper(label-text))
    linebreak()
    body
  },
)

#let callout-warning(label-text: "Warning", body) = block(
  width: 100%, fill: white,
  stroke: (left: 2pt + vf-red),
  inset: (left: 0.9em, right: 0.9em, top: 0.55em, bottom: 0.5em),
  above: 1em, below: 1em,
  {
    text(size: 8pt, weight: "bold", font: font-sans, tracking: 0.08em, fill: vf-red, upper(label-text))
    linebreak()
    body
  },
)

#let callout(label-text: "Note", style: "note", body) = {
  if style == "warning" or style == "caution" or style == "important" {
    callout-warning(label-text: label-text, body)
  } else {
    callout-note(label-text: label-text, body)
  }
}

#let mermaid-placeholder(n) = block(
  width: 100%, fill: quote-fill,
  stroke: (paint: rule-light, thickness: 1pt, dash: "dashed"),
  inset: (x: 0.9em, y: 0.7em), above: 0.9em, below: 0.9em,
  align(center, text(size: 8pt, style: "italic", fill: faint,
    [Diagram #n — install mermaid-cli to render]))
)

#let intel-table(columns: auto, headers: (), rows: ()) = {
  let header-cells = headers.map(h =>
    table.cell(fill: vf-black)[#text(fill: white, weight: "bold", font: font-sans, size: 8.5pt, h)])
  let all-cells = header-cells
  for (i, row) in rows.enumerate() {
    let bg = if calc.rem(i, 2) == 1 { quote-fill } else { white }
    for cell in row { all-cells.push(table.cell(fill: bg)[#cell]) }
  }
  set text(size: 9.5pt)
  table(columns: columns, stroke: 0.35pt + rule-light, inset: (x: 0.6em, y: 0.4em), ..all-cells)
}