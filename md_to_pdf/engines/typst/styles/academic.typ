// academic.typ — Academic paper style for md_to_typst
//
// Single-column, generous margins, classic serif throughout.
// Minimal colour — black/dark-grey only. Suitable for preprints and papers.

// ── Colour palette ──────────────────────────────────────────────────────────
#let dark        = rgb("#111111")
#let mid-grey    = rgb("#444444")
#let faint       = rgb("#777777")
#let rule-grey   = rgb("#bbbbbb")
#let bg-code     = rgb("#f5f5f5")
#let link-blue   = rgb("#1a4f8a")

// ── Font families ───────────────────────────────────────────────────────────
#let font-body   = ("Palatino", "Palatino Linotype", "Book Antiqua", "Georgia", "Times New Roman", "serif")
#let font-mono   = ("Source Code Pro", "Courier New", "monospace")

// ── Main template function ──────────────────────────────────────────────────
#let doc(
  author:   "Author Name",
  title:    "Article Title",
  pub-name: "Journal",
  doc-type: "WORKING PAPER",
  justify:  true,
  body,
) = {

  set page(
    paper:  "a4",
    margin: (top: 3.5cm, bottom: 3cm, left: 3.5cm, right: 3.5cm),
    header: context {
      if counter(page).get().first() == 1 { return }
      set text(font: font-body, size: 9pt, fill: faint, style: "italic")
      grid(
        columns: (1fr, 1fr),
        align: (left, right),
        title,
        author,
      )
      v(3pt)
      line(length: 100%, stroke: 0.5pt + rule-grey)
    },
    footer: context {
      if counter(page).get().first() == 1 { return }
      set text(font: font-body, size: 8pt, fill: faint)
      let pg = counter(page).display()
      align(center, pg)
    },
  )

  set text(font: font-body, size: 11pt, fill: dark, lang: "en", hyphenate: true)
  set par(justify: justify, leading: 0.7em, spacing: 0.6em, first-line-indent: 1.5em)

  show heading.where(level: 1): it => {
    set text(size: 16pt, weight: "bold", fill: dark)
    block(width: 100%, above: 1.2em, below: 0.8em)[
      #it.body
      #v(4pt)
      #line(length: 100%, stroke: 1pt + rule-grey)
    ]
  }

  show heading.where(level: 2): it => {
    set text(size: 12pt, weight: "bold", fill: dark)
    block(width: 100%, above: 1.6em, below: 0.4em, it.body)
  }

  show heading.where(level: 3): it => {
    set text(size: 11pt, weight: "bold", style: "italic", fill: dark)
    block(above: 1.2em, below: 0.3em, it.body)
  }

  show heading.where(level: 4): it => {
    set text(size: 11pt, weight: "bold", fill: mid-grey)
    block(above: 0.9em, below: 0.2em, it.body)
  }

  show heading.where(level: 5): it => {
    set text(size: 11pt, style: "italic", fill: mid-grey)
    block(above: 0.9em, below: 0.2em, it.body)
  }

  show heading.where(level: 6): it => {
    set text(size: 11pt, style: "italic", fill: mid-grey)
    block(above: 0.9em, below: 0.2em, it.body)
  }

  show raw.where(block: false): it => {
    box(fill: bg-code, inset: (x: 2pt, y: 1pt), radius: 1.5pt,
      text(font: font-mono, size: 9pt, it))
  }
  show raw.where(block: true): it => {
    block(width: 100%, fill: bg-code, inset: (x: 10pt, y: 8pt),
      stroke: (left: 2pt + rule-grey),
      text(font: font-mono, size: 9pt, it))
  }

  show link: it => { set text(fill: link-blue); it }

  show quote.where(block: true): it => {
    pad(left: 2em, right: 2em,
      block(
        inset: (left: 1em, top: 0.4em, bottom: 0.4em),
        stroke: (left: 1.5pt + rule-grey),
        text(size: 10.5pt, style: "italic", fill: mid-grey, it.body),
      )
    )
  }

  set list(marker: text(fill: dark)[ – ], indent: 1.6em, spacing: 0.4em)
  set enum(indent: 1.6em, spacing: 0.4em)

  set figure(gap: 0.6em)
  show figure.caption: it => {
    set text(size: 9pt, style: "italic", fill: faint)
    align(center, it)
  }

  set footnote.entry(gap: 0.5em, indent: 1em)
  show footnote.entry: it => { set text(size: 8.5pt, fill: mid-grey); it }

  body
}

// ── Reusable block helpers ──────────────────────────────────────────────────

#let key-takeaways(scope-note: none, body) = block(
  width: 100%, fill: rgb("#f0f0f0"),
  stroke: (top: 1.5pt + rule-grey, bottom: 1.5pt + rule-grey),
  inset: (x: 1.2em, top: 0.7em, bottom: 0.8em),
  above: 1em, below: 1.2em,
  {
    text(size: 10pt, weight: "bold", fill: dark)[Key Takeaways]
    v(3pt)
    line(length: 100%, stroke: 0.5pt + rule-grey)
    v(5pt)
    if scope-note != none { text(style: "italic", scope-note); v(4pt) }
    body
  },
)

#let insights-box(heading: none, body) = block(
  width: 100%, fill: rgb("#f7f7f7"),
  stroke: (top: 1.5pt + mid-grey, bottom: 0.8pt + rule-grey),
  inset: (x: 1.2em, top: 0.8em, bottom: 0.8em),
  above: 0.9em, below: 1em,
  {
    if heading != none {
      text(size: 11pt, weight: "bold", fill: dark, heading)
      v(2pt)
      line(length: 100%, stroke: 0.5pt + rule-grey)
      v(5pt)
    }
    body
  },
)

#let pull-quote(body, source: none) = pad(
  left: 2em, right: 2em,
  block(
    stroke: (left: 1.5pt + rule-grey),
    inset: (left: 1em, top: 0.6em, bottom: 0.6em),
    above: 1em, below: 1em,
    {
      set text(size: 12pt, style: "italic", fill: mid-grey)
      body
      if source != none {
        v(3pt)
        line(length: 100%, stroke: 0.4pt + rule-grey)
        v(2pt)
        text(size: 9pt, style: "normal", fill: faint, source)
      }
    },
  )
)

#let callout-note(label-text: "Note", body) = block(
  width: 100%, fill: rgb("#f0f0f0"),
  stroke: (left: 2pt + mid-grey),
  inset: (left: 0.8em, right: 0.9em, top: 0.6em, bottom: 0.5em),
  above: 1em, below: 1em,
  {
    text(size: 9pt, weight: "bold", fill: dark, upper(label-text))
    linebreak()
    body
  },
)

#let callout-warning(label-text: "Warning", body) = callout-note(label-text: label-text, body)

#let callout(label-text: "Note", style: "note", body) = {
  callout-note(label-text: label-text, body)
}

#let mermaid-placeholder(n) = block(
  width: 100%, fill: rgb("#f5f5f5"),
  stroke: (paint: rule-grey, thickness: 0.8pt, dash: "dashed"),
  inset: (x: 0.9em, y: 0.7em), above: 0.9em, below: 0.9em,
  align(center, text(size: 9pt, style: "italic", fill: faint,
    [Figure #n — diagram not rendered]))
)

#let intel-table(columns: auto, headers: (), rows: ()) = {
  let header-cells = headers.map(h =>
    table.cell(fill: rgb("#333333"))[#text(fill: white, weight: "bold", size: 9pt, h)])
  let all-cells = header-cells
  for (i, row) in rows.enumerate() {
    let bg = if calc.rem(i, 2) == 1 { rgb("#f0f0f0") } else { white }
    for cell in row { all-cells.push(table.cell(fill: bg)[#cell]) }
  }
  set text(size: 10pt)
  table(columns: columns, stroke: 0.5pt + rule-grey, inset: (x: 0.6em, y: 0.4em), ..all-cells)
}
