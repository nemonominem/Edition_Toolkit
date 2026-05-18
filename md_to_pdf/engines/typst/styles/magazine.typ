// magazine.typ — Long-form magazine style for md_to_typst
//
// Clean editorial layout: single wide column, generous margins, sans-serif
// headings over serif body. Warm off-white palette with rust/terracotta accent.

// ── Colour palette ──────────────────────────────────────────────────────────
#let rust        = rgb("#b94a2c")
#let dark-rust   = rgb("#7a2e18")
#let warm-grey   = rgb("#4a4a4a")
#let light-grey  = rgb("#e8e4df")
#let faint       = rgb("#777777")
#let body-black  = rgb("#1a1a1a")
#let bg-code     = rgb("#f2f2f2")
#let rule-light  = rgb("#cccccc")

// ── Font families ───────────────────────────────────────────────────────────
#let font-body    = ("Palatino", "Palatino Linotype", "Book Antiqua", "Georgia", "Times New Roman", "serif")
#let font-heading = ("Helvetica Neue", "Helvetica", "Arial", "sans-serif")
#let font-mono    = ("Source Code Pro", "Courier New", "monospace")

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
    paper:  "a4",
    margin: (top: 3cm, bottom: 2.5cm, left: 3cm, right: 3cm),
    header: context {
      if counter(page).get().first() == 1 { return }
      set text(font: font-heading, size: 8.5pt, fill: faint)
      grid(
        columns: (1fr, 1fr),
        align: (left, right),
        upper(pub-name),
        upper(doc-type),
      )
      v(3pt)
      line(length: 100%, stroke: 0.5pt + rule-light)
    },
    footer: context {
      if counter(page).get().first() == 1 { return }
      set text(font: font-heading, size: 7.5pt, fill: faint)
      let pg    = counter(page).display()
      let total = counter(page).final().first()
      grid(
        columns: (1fr, 1fr, 1fr),
        align: (left, center, right),
        author,
        pg + " / " + str(total),
        emph(title),
      )
    },
  )

  set text(font: font-body, size: 10.5pt, fill: body-black, lang: "en", hyphenate: true)
  set par(justify: justify, leading: 0.75em, spacing: 0.6em)

  show heading.where(level: 1): it => {
    set text(font: font-heading, size: 22pt, weight: "bold", fill: body-black)
    block(width: 100%, above: 0.5em, below: 0.4em)[
      #it.body
      #v(6pt)
      #line(length: 6cm, stroke: 3pt + rust)
    ]
  }

  show heading.where(level: 2): it => {
    set text(font: font-heading, size: 13pt, weight: "bold", fill: rust)
    block(width: 100%, above: 1.6em, below: 0.4em, it.body)
  }

  show heading.where(level: 3): it => {
    set text(font: font-heading, size: 10.5pt, weight: "bold", fill: warm-grey)
    block(above: 1.2em, below: 0.3em, upper(it.body))
  }

  show heading.where(level: 4): it => {
    set text(font: font-heading, size: 10pt, weight: "bold", style: "italic", fill: warm-grey)
    block(above: 0.9em, below: 0.2em, it.body)
  }

  show heading.where(level: 5): it => {
    set text(font: font-heading, size: 10pt, weight: "bold", style: "italic", fill: warm-grey)
    block(above: 0.9em, below: 0.2em, it.body)
  }

  show heading.where(level: 6): it => {
    set text(font: font-heading, size: 10pt, weight: "bold", style: "italic", fill: warm-grey)
    block(above: 0.9em, below: 0.2em, it.body)
  }

  show raw.where(block: false): it => {
    box(fill: bg-code, inset: (x: 2pt, y: 1pt), radius: 1.5pt,
      text(font: font-mono, size: 8.5pt, it))
  }
  show raw.where(block: true): it => {
    block(width: 100%, fill: bg-code, inset: (x: 8pt, y: 6pt),
      stroke: (left: 3pt + rust),
      text(font: font-mono, size: 8.5pt, it))
  }

  show link: it => { set text(fill: rust); it }

  show quote.where(block: true): it => {
    pad(left: 0em,
      block(
        stroke: (left: 4pt + rust),
        fill: light-grey,
        inset: (left: 1em, right: 1em, top: 0.6em, bottom: 0.6em),
        text(size: 11pt, style: "italic", fill: warm-grey, it.body),
      )
    )
  }

  set list(marker: text(fill: rust, weight: "bold")[ • ], indent: 1.4em, spacing: 0.3em)
  set enum(indent: 1.4em, spacing: 0.3em)

  set figure(gap: 0.5em)
  show figure.caption: it => {
    set text(font: font-heading, size: 8pt, style: "italic", fill: faint)
    align(center, it)
  }

  set footnote.entry(gap: 0.4em, indent: 1em)
  show footnote.entry: it => { set text(size: 8pt, fill: faint); it }

  body
}

// ── Reusable block helpers ──────────────────────────────────────────────────

#let key-takeaways(scope-note: none, body) = block(
  width: 100%, fill: light-grey,
  stroke: (top: 3pt + rust, bottom: 1pt + rust),
  inset: (x: 1.2em, top: 0.8em, bottom: 0.9em),
  above: 1em, below: 1.2em,
  {
    text(size: 10pt, weight: "bold", font: ("Helvetica Neue", "Helvetica", "Arial", "sans-serif"), fill: rust)[Key Takeaways]
    v(3pt)
    line(length: 100%, stroke: 0.6pt + rust)
    v(5pt)
    if scope-note != none { text(style: "italic", scope-note); v(4pt) }
    body
  },
)

#let insights-box(heading: none, body) = block(
  width: 100%, fill: rgb("#fdf6ee"),
  stroke: (top: 3pt + rust, bottom: 1.5pt + rust),
  inset: (x: 1.2em, top: 0.8em, bottom: 0.8em),
  above: 0.9em, below: 1em,
  {
    if heading != none {
      text(size: 10.5pt, weight: "bold", fill: body-black, heading)
      v(2pt)
      line(length: 100%, stroke: 0.6pt + rust)
      v(5pt)
    }
    body
  },
)

#let pull-quote(body, source: none) = pad(
  left: 0em,
  block(
    stroke: (left: 5pt + rust),
    fill: light-grey,
    inset: (left: 1em, right: 1em, top: 0.7em, bottom: 0.7em),
    above: 1.2em, below: 1.2em,
    {
      set text(size: 13pt, style: "italic", fill: warm-grey)
      body
      if source != none {
        v(4pt)
        line(length: 100%, stroke: 0.5pt + rule-light)
        v(2pt)
        text(size: 8.5pt, style: "normal", fill: faint, source)
      }
    },
  )
)

#let callout-note(label-text: "Note", body) = block(
  width: 100%, fill: light-grey,
  stroke: (left: 4pt + rust),
  inset: (left: 0.8em, right: 0.9em, top: 0.6em, bottom: 0.5em),
  above: 1em, below: 1em,
  {
    text(size: 8.5pt, weight: "bold", fill: rust, upper(label-text))
    linebreak()
    body
  },
)

#let callout-warning(label-text: "Warning", body) = block(
  width: 100%, fill: rgb("#fdf6ee"),
  stroke: (left: 4pt + dark-rust),
  inset: (left: 0.8em, right: 0.9em, top: 0.6em, bottom: 0.5em),
  above: 1em, below: 1em,
  {
    text(size: 8.5pt, weight: "bold", fill: dark-rust, upper(label-text))
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
  width: 100%, fill: light-grey,
  stroke: (paint: rule-light, thickness: 1pt, dash: "dashed"),
  inset: (x: 0.9em, y: 0.7em), above: 0.9em, below: 0.9em,
  align(center, text(size: 8pt, style: "italic", fill: faint,
    [Diagram #n — install mermaid-cli to render]))
)

#let intel-table(columns: auto, headers: (), rows: ()) = {
  let header-cells = headers.map(h =>
    table.cell(fill: rust)[#text(fill: white, weight: "bold", h)])
  let all-cells = header-cells
  for (i, row) in rows.enumerate() {
    let bg = if calc.rem(i, 2) == 1 { light-grey } else { white }
    for cell in row { all-cells.push(table.cell(fill: bg)[#cell]) }
  }
  set text(size: 9pt)
  table(columns: columns, stroke: none, inset: (x: 0.55em, y: 0.35em), ..all-cells)
}
