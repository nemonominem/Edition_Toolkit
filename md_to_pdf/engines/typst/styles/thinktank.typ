// thinktank.typ — Policy/think-tank report style for md_to_typst
//
// Formal two-column layout with forest green accent. Clean, authoritative,
// suitable for policy briefs and research reports.

// ── Colour palette ──────────────────────────────────────────────────────────
#let green       = rgb("#2a5c3f")
#let light-green = rgb("#d4e6da")
#let pale-green  = rgb("#f0f5f2")
#let warm-grey   = rgb("#4a4a4a")
#let faint       = rgb("#666666")
#let body-black  = rgb("#1a1a1a")
#let bg-code     = rgb("#f2f2f2")
#let rule-light  = rgb("#b0c4b8")
#let stripe      = rgb("#e8eeeb")

// ── Font families ───────────────────────────────────────────────────────────
#let font-body   = ("Palatino", "Palatino Linotype", "Book Antiqua", "Georgia", "Times New Roman", "serif")
#let font-mono   = ("Source Code Pro", "Courier New", "monospace")

// ── Main template function ──────────────────────────────────────────────────
#let doc(
  author:   "Author Name",
  title:    "Article Title",
  pub-name: "Policy Brief",
  doc-type: "RESEARCH REPORT",
  justify:  true,
  body,
) = {

  set page(
    paper:  "a4",
    margin: (top: 3cm, bottom: 2.5cm, left: 2cm, right: 2cm),
    header: context {
      if counter(page).get().first() == 1 { return }
      set text(font: font-body, size: 10pt, weight: "bold", fill: green)
      grid(
        columns: (1fr, 1fr),
        align: (left, right),
        pub-name,
        doc-type,
      )
      v(4pt)
      line(length: 100%, stroke: 1.5pt + green)
    },
    footer: context {
      if counter(page).get().first() == 1 { return }
      set text(font: font-body, size: 7.5pt, fill: faint)
      let pg    = counter(page).display()
      let total = counter(page).final().first()
      grid(
        columns: (1fr, 1fr, 1fr),
        align: (left, center, right),
        author,
        "[ " + pg + "/" + str(total) + " ]",
        emph(title),
      )
    },
  )

  set text(font: font-body, size: 9.5pt, fill: body-black, lang: "en", hyphenate: true)
  set par(justify: justify, leading: 0.65em, spacing: 0.5em)

  show heading.where(level: 1): it => {
    set text(size: 16pt, weight: "bold", fill: green)
    block(width: 100%, above: 1em, below: 0.6em)[
      #it.body
      #v(3pt)
      #line(length: 100%, stroke: 2.5pt + green)
    ]
  }

  show heading.where(level: 2): it => {
    set text(size: 11pt, weight: "bold", fill: green)
    block(width: 100%, above: 1.4em, below: 0.35em)[
      #it.body
      #v(1pt)
      #line(length: 100%, stroke: 0.8pt + green)
    ]
  }

  show heading.where(level: 3): it => {
    set text(size: 9.5pt, weight: "bold", fill: body-black)
    block(above: 1.2em, below: 0.25em, it.body)
  }

  show heading.where(level: 4): it => {
    set text(size: 9.5pt, weight: "bold", style: "italic", fill: warm-grey)
    block(above: 0.9em, below: 0.2em, it.body)
  }

  show heading.where(level: 5): it => {
    set text(size: 9.5pt, weight: "bold", style: "italic", fill: warm-grey)
    block(above: 0.9em, below: 0.2em, it.body)
  }

  show heading.where(level: 6): it => {
    set text(size: 9.5pt, weight: "bold", style: "italic", fill: warm-grey)
    block(above: 0.9em, below: 0.2em, it.body)
  }

  show raw.where(block: false): it => {
    box(fill: bg-code, inset: (x: 2pt, y: 1pt), radius: 1.5pt,
      text(font: font-mono, size: 8pt, it))
  }
  show raw.where(block: true): it => {
    block(width: 100%, fill: bg-code, inset: (x: 8pt, y: 6pt),
      stroke: (left: 2.5pt + green),
      text(font: font-mono, size: 8pt, it))
  }

  show link: it => { set text(fill: green); it }

  show quote.where(block: true): it => {
    pad(left: 1.2em,
      block(
        stroke: (left: 2.5pt + green),
        inset: (left: 0.8em, top: 0.4em, bottom: 0.4em),
        text(style: "italic", fill: rgb("#333333"), it.body),
      )
    )
  }

  set list(marker: text(fill: green, weight: "bold")[ • ], indent: 1.4em, spacing: 0.3em)
  set enum(indent: 1.4em, spacing: 0.3em)

  set figure(gap: 0.5em)
  show figure.caption: it => {
    set text(size: 8pt, style: "italic", fill: faint)
    align(center, it)
  }

  set footnote.entry(gap: 0.4em, indent: 1em)
  show footnote.entry: it => { set text(size: 7.5pt, fill: faint); it }

  body
}

// ── Reusable block helpers ──────────────────────────────────────────────────

#let key-takeaways(scope-note: none, body) = block(
  width: 100%, fill: light-green,
  stroke: (top: 3pt + green, bottom: 3pt + green),
  inset: (x: 1em, top: 0.7em, bottom: 0.8em),
  above: 0.8em, below: 1.2em,
  {
    text(size: 10pt, weight: "bold", fill: green)[Key Takeaways]
    v(3pt)
    line(length: 100%, stroke: 0.7pt + green)
    v(5pt)
    if scope-note != none { text(style: "italic", scope-note); v(4pt) }
    body
  },
)

#let insights-box(heading: none, body) = block(
  width: 100%, fill: pale-green,
  stroke: (top: 3pt + green, bottom: 1.5pt + green),
  inset: (x: 1em, top: 0.8em, bottom: 0.8em),
  above: 0.9em, below: 1em,
  {
    if heading != none {
      text(size: 9.5pt, weight: "bold", fill: body-black, heading)
      v(2pt)
      line(length: 100%, stroke: 0.6pt + green)
      v(5pt)
    }
    body
  },
)

#let pull-quote(body, source: none) = pad(
  left: 1.2em,
  block(
    stroke: (left: 3pt + green),
    fill: stripe,
    inset: (left: 0.8em, top: 0.5em, bottom: 0.5em, right: 0.5em),
    above: 1em, below: 1em,
    {
      text(style: "italic", body)
      if source != none {
        v(3pt)
        line(length: 100%, stroke: 0.5pt + rule-light)
        v(2pt)
        text(size: 8pt, style: "normal", fill: faint, source)
      }
    },
  )
)

#let callout-note(label-text: "Note", body) = block(
  width: 100%, fill: light-green,
  stroke: (top: 3pt + green, bottom: 3pt + green),
  inset: (x: 0.9em, top: 0.6em, bottom: 0.5em),
  above: 1em, below: 1em,
  {
    text(size: 8pt, weight: "bold", fill: green, upper(label-text))
    linebreak()
    body
  },
)

#let callout-warning(label-text: "Warning", body) = block(
  width: 100%, fill: pale-green,
  stroke: (left: 4pt + green, top: 2pt + green),
  inset: (left: 0.8em, right: 0.9em, top: 0.6em, bottom: 0.5em),
  above: 1em, below: 1em,
  {
    text(size: 8pt, weight: "bold", fill: green, upper(label-text))
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
  width: 100%, fill: stripe,
  stroke: (paint: rule-light, thickness: 1pt, dash: "dashed"),
  inset: (x: 0.9em, y: 0.7em), above: 0.9em, below: 0.9em,
  align(center, text(size: 8pt, style: "italic", fill: faint,
    [Diagram #n — install mermaid-cli to render]))
)

#let intel-table(columns: auto, headers: (), rows: ()) = {
  let header-cells = headers.map(h =>
    table.cell(fill: green)[#text(fill: white, weight: "bold", h)])
  let all-cells = header-cells
  for (i, row) in rows.enumerate() {
    let bg = if calc.rem(i, 2) == 1 { stripe } else { white }
    for cell in row { all-cells.push(table.cell(fill: bg)[#cell]) }
  }
  set text(size: 8.5pt)
  table(columns: columns, stroke: none, inset: (x: 0.55em, y: 0.35em), ..all-cells)
}
