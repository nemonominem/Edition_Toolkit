---
name: foia-email-pdf
description: >
  Reference for parsing FOIA'd/released email correspondence out of a PDF into
  one structured entry per message (sender, timestamp, zone, subject, thread
  links, page map). Covers OCR vs. native-text-layer extraction, reading-order
  quirks (stray watermarks/stamps, glued words), redaction noise, long
  mailing-list header blocks, embedded attachments, and the header/body
  segmentation grammar. Load this before writing or debugging a parser for a
  released email/document PDF, or when OCR output on such a release looks
  wrong (pipes for "I", stray spaces mid-word, fields leaking into the body,
  an attachment's text glued onto a message, content under the wrong
  timestamp).
metadata:
  short-description: "FOIA'd email PDF -> structured entries: OCR, headers, zones, noise"
  domain: osint-document-parsing
---

# Parsing FOIA'd email PDFs

Lessons from building and repeatedly debugging parsers for several FOIA/FOI
email releases (Proximal Origin project: `po-emails.pdf`, a screenshot-scanned
Outlook export; `farrar-fauci-comms.pdf`, a plain-text-layer Outlook export
re-OCR'd from scratch; `sscp-drafts.pdf`, a native-text-layer manuscript with
repeating version watermarks). None of this is project-specific — it is the
set of failure modes this *kind* of document reliably produces, and the fixes
that reliably work. Read this before writing a new `parse_<release>.py`, and
re-read the relevant section when its OCR output looks wrong in a way you
haven't seen before.

## 0. First question: OCR, or extract the native text layer?

Check both before choosing, on one or two representative pages:

```bash
pdftotext -f 50 -l 50 release.pdf -                  # native layer, plain
pdftotext -layout -f 50 -l 50 release.pdf -           # native layer, layout-preserving
python3 -c "import pypdf; print(pypdf.PdfReader('release.pdf').pages[49].extract_text())"
```

- **Native layer reads as glued nonsense** (`sent:Fri,24Jul202010:37:4640000To:
  JeremyFarrar`) — words run together with no spaces, or glyphs are
  misread — the text layer is a bad OCR pass baked in at scan time, or a font
  encoding pypdf/pdftotext can't read. Re-OCR from scratch: render each page
  to PNG at 300dpi with `pdftoppm`, then `tesseract page.png stdout --oem 1
  --psm 6`. Verify first that the *rendered page image* is actually sharp
  (spot-check 2-3 pages) — if the scan itself is low-resolution, re-OCR won't
  help and you're stuck with the bad layer.
- **Native layer is mostly clean prose** with occasional stray spaces
  inside words (`re sidues`, `fo r interaction`) or a word's first letter
  stranded alone on its own line (`B` / `amHI site...`) — this is pypdf (or
  pdfminer-based tools) mis-segmenting runs of text by kerning/positioning,
  not a scan-quality problem. Don't re-OCR; fix the narrow, specific pattern
  instead (§5). Compare `pypdf.extract_text()`, `extract_text(extraction_mode=
  "layout")`, and `pdftotext`/`pdftotext -layout` against each other on a
  sample page before committing to one — they fail differently (layout mode
  can *introduce* new gaps, e.g. `duri ng`, while fixing others; `pdftotext`
  plain mode is often the cleanest for prose but may scatter a rotated
  watermark into fragments mid-document that `pypdf` keeps as one clean
  line — if the document has a watermark/stamp you need to detect reliably,
  that reliability can outweigh prose cleanliness; see §4).

## 1. Entry/segmentation grammar

One entry per **author at a single instant** — never a whole thread, never
quoted history folded into the message that quotes it.

Start a new entry at:
1. A `From:` header block.
2. A quoted header using `Sent:`/`Date:` with no `From:` immediately above it
   — the scan ate the `From:` line. Guard this strictly so it never fires
   inside a message's own header: require that the current message is
   already past its own header (`body_mode`) **and** far enough past its own
   `From:` (position-distance check, not just "any Date:/Sent: line") that
   this can't be its own stamp.
3. An inline quote marker: `On 8 Feb 2020, at 22:15, Kristian G. Andersen
   wrote:` / `On Sat, Feb 8, 2020 at 12:38 PM Drosten, Christian wrote:`.
   Recover it as its own entry: synthesize `From:`/`Sent:` lines from the
   marker's own name + date + time and feed them through the *same*
   header-parsing path (don't special-case the entry construction) — no
   Subject is invented for these, left empty rather than guessed.

Header fields continue across lines **only** for `From`/`To`/`Cc`/`Bcc`.
`Subject`/`Sent`/`Date`/`Importance` are terminal single-line fields in the
simple case — but see §3 for what happens when they're not (a long subject
can still wrap).

Multilingual and OCR-variant field names are common — fold them onto the
canonical name rather than special-casing each:
```python
FIELD_ALIASES = {
    "ce": "Cc", "bce": "Bcc", "gc": "Cc",                 # OCR: Cc: -> Ce:/Gc:
    "fe": "To", "pe": "To",                               # OCR: To: -> Fe:/Pe:
    "rom": "From", "fram": "From", "fo": "From",          # OCR: From: -> rom:/Fram:/Fo:
    "von": "From", "gesendet": "Sent", "an": "To", "betreff": "Subject",  # German
}
```

## 2. Time zones (ordering must never lie)

**A reply must never appear to answer a message from its own future.**

1. **An explicit UTC offset in the stamp always wins** — `Tue 2/4/2020
   9:10:35 AM (UTC-05:00)` or the bare RFC-2822 form `Fri, 24 Jul 2020
   10:37:46 +0000`. Extract and trust it; don't re-zone it against the
   institution table below.
   - Watch for a Python truthiness bug here: `timedelta(hours=0, minutes=0)`
     (a `+0000`/UTC offset) is **falsy**. `"offset" if off else "..."` silently
     mislabels every UTC-stamped message as if it had no offset. Always test
     `if off is not None`, never `if off`.
2. **Otherwise, the sender's own institution decides the zone** — every
   message in a release like this states it in the signature block or
   address line. Build a small table once, with the evidence in a comment
   (who/what justifies each zone), and a sane default (usually the release's
   convening organisation).
3. **Normalise to one zone (e.g. ET) for ordering and entry keys**; keep the
   local stamp for display (`stamp_line`: `"20:43 GMT -> 15:43 ET"`), and
   record *why* a zone was assumed (`zone_assumed`) so a reader can check the
   assumption rather than trust it blindly.
4. Use `zoneinfo`, not fixed offsets, so DST is handled.
5. **Never invent a date.** A stamp that doesn't parse stays `date: None`,
   flagged `date_note: "no usable timestamp; not plotted"` — don't guess a
   day from context. A locale you haven't handled (Dutch `donderdag 5 maart
   2020`, Spanish `martes, 28 de enero de 2020`) is a known, acceptable gap;
   don't silently misparse it as something else.
6. **Document order is not chronological order.** A release can print a
   conversation grouped by thread/subject rather than by time — sort by the
   stamps you parsed, never trust print order for chronology checks.

## 3. Redaction and OCR noise, specifically

These are the concrete, repeatedly-seen patterns, each cheap and safe to fix
with a narrow regex rather than a general dictionary de-gluer (which risks
inventing words it shouldn't touch):

- **A standalone `|` is a garbled capital "I"** when bounded by
  whitespace/punctuation (`| will:` -> `I will:`, `| believe` -> `I believe`).
  ```python
  STANDALONE_PIPE_RE = re.compile(r"(?<![^\s])\|(?![^\s.,!?;:'\")\]])")
  line = STANDALONE_PIPE_RE.sub("I", line)
  ```
- **A round bullet glyph is misread as the nearest Latin letter/symbol** —
  commonly `e` or `©` at the very start of a line, immediately before a
  capitalised word (English prose essentially never opens a line on a bare
  lower-case "e"):
  ```python
  RE_BULLET_MISREAD = re.compile(r"^[e©]\s+(?=[A-Z])")
  line = RE_BULLET_MISREAD.sub("• ", line)
  ```
- **Redaction/avatar brackets** on header values — `[E]`, `(€]`, `[EJ Oe`,
  trailing glyph-soup after a name — strip with a bracket/glyph regex, but
  keep the raw string alongside (`sender_raw`) so nothing is silently
  rewritten. A short letter-run glued right after a closing bracket is the
  redaction tail, not part of the address: `re.sub(r"([)\]])\s+[A-Za-z]{1,3}
  \s*$", r"\1", v)`.
  - Avatar glyphs and redaction boxes frequently read as random short
    letter-strings that then *fail* a shape test downstream (name-roster
    match, "looks like a recipient" check) — expect this, and make recovery
    logic (§6) robust to a single such failure rather than brittle against it.
- **Glued words at a line-wrap or bullet boundary** — verify each
  occurrence in context before adding it (`grep -n` the exact token across
  the whole corpus; if it's 1-10 occurrences and every one is the same
  glue-loss, it's safe to fix by name):
  ```python
  GLUED_WORDS = {"itis": "it is", "ina": "in a", "toa": "to a", "Bein": "Be in"}
  GLUED_WORDS_RE = re.compile(r"\b(%s)\b" % "|".join(map(re.escape, GLUED_WORDS)))
  ```
- **A word's first letter stranded alone on its own line** (native-text-layer
  extraction quirk, not OCR — see §0): a line that is *only* optional list
  numbering plus one bare capital letter, followed by a line starting
  lower-case, is that letter's word continuing:
  ```python
  RE_STRAY_INITIAL = re.compile(r"^\s*(?:\d+\.\s*)?[A-Z]\s*$")
  # if RE_STRAY_INITIAL.match(line) and next_line starts lower-case:
  #     merge = line.rstrip() + next_line   # no space -- it's the same word
  ```
  Keep this pattern *strict* (whole-line match, nothing else on it) — a line
  that merely *ends* in a capital (a real acronym like "ACE2" closing a
  wrapped sentence) must never trigger it.

## 4. Repeating stamps/watermarks on every page (version releases)

A document reprinted once per revision, each copy watermarked with a
version stamp, is a distinct failure mode from a single email: **check
whether the stamp text comes before or after its own page's body in
extraction order** — don't assume either. Dump full, unmodified per-page
text first:

```python
import pypdf
r = pypdf.PdfReader("release.pdf")
for i in range(0, 6):
    print("=== page", i+1, "==="); print(r.pages[i].extract_text())
```

A rotated/diagonal watermark is drawn in a different part of the PDF content
stream than the horizontal body text, so extraction order frequently puts it
**after** the body it visually sits in front of or above — even though the
visual, printed reading order has it first (a header-looking watermark) or
spans every page of that version (a running stamp, not a one-time footer).

Getting this backwards silently attributes each page's content to the
**next** stamp rather than its own — the symptom is a version's text not
matching its own watermark when you render the actual PDF page next to it.
The fix is almost always: **the stamp seals the content that precedes it in
extraction order, it does not open what follows**:

```python
# WRONG: "versions.append(new) on seeing a stamp, append subsequent lines to it"
#   -> attributes page N+1's content to page N's stamp.
# RIGHT: accumulate into a pending buffer; a stamp closes the buffer into a
#   version (merging into the previous version if its stamp is identical --
#   i.e. the same version simply ran onto another page), then the buffer
#   resets for whatever comes next.
versions, cur_lines = [], []
for pageno, text in pages:
    for line in text.split("\n"):
        stamp = parse_stamp(line)
        if stamp:
            if versions and versions[-1]["stamp"] == stamp:
                versions[-1]["lines"].extend(cur_lines)
            else:
                versions.append({"stamp": stamp, "lines": cur_lines})
            cur_lines = []
            continue
        if line.strip():
            cur_lines.append(line)
```

Verify the fix by rendering the page(s) a specific entry's page-map claims
and eyeballing the watermark against the entry's own text — don't just trust
that the version count still looks plausible.

## 5. Long / redacted mailing lists (don't hard-cap the header)

A FOIA release to a Board/committee can carry 20-40 redacted recipients
wrapped over as many visual lines. Two failure modes compound here:

1. **A hard header-line cap sized for the common case silently truncates the
   uncommon one.** If your header-continuation logic has a `MAX_HEADER_LINES`
   ceiling, and segmentation never re-enters header mode once it gives up
   (common architecture: a `body_mode` flag that only goes one way), a cap
   that's too low doesn't just lose a few names — it strands the
   **Subject/Importance lines that come after the list** in the body too,
   because the parser already switched to body mode before reaching them.
   Size the cap generously (the real gatekeeper should be a shape test, not
   the cap) and verify against the single longest list you can find in the
   corpus, with headroom.

2. **A recovery sweep that requires every line to positively "look like a
   recipient" is exactly as fragile as the list is garbled.** One OCR-mangled
   name anywhere in the list (a real case: "Teresa Miller de Vega" OCR'd as
   "niiller de Vega", which failed an all-tokens-recognised check) breaks the
   chain and strands everything after it — even though 16 more genuine
   recipient-shaped lines and the Subject line were sitting right there.
   **Invert the default**: don't give up when a line fails to look like a
   recipient; keep scanning until a line *positively* looks like real body
   prose (a greeting, or a long sentence with several ordinary lowercase
   words), and only give up then:
   ```python
   def looks_like_body_prose(line):
       s = line.strip()
       if re.match(r"^(Dear|Hi|Hello|Hey)\b", s, re.I):
           return True
       return len(s) > 40 and RE_SENTENCE_END.search(s) and \
           len(re.findall(r"[a-z]{3,}", s)) >= 5
   # while scanning forward for a stranded Subject/Importance line:
   #   if looks_like_body_prose(line): break      # NOT: if not looks_like_recipient(line): break
   ```
   This one inversion is worth more than any amount of tuning the positive
   "looks like a recipient" classifier — it's inherently a losing battle
   against arbitrarily-garbled redaction noise, so don't rely on it as the
   stopping condition.

3. **When a sweep reprocesses recovered lines one at a time** (e.g. feeding
   each stranded line back through a single-line field-parser to extract
   Subject/Importance individually), two things are easy to drop silently:
   a second non-recognised field found further along (make sure the
   recovery position actually advances onto it before stopping, not just
   that it's *detected*), and a long Subject that wraps onto its own line
   with no field keyword of its own (reattach a no-keyword line onto the
   last field actually set, when it doesn't look like body prose, rather
   than letting one-line-at-a-time reprocessing drop it).

4. **Don't let a header-length cap and a message-boundary distance check
   share one constant**, even though they look related. A `MAX_HEADER_LINES`
   sized for long recipient lists (point 1 above) is one thing; separately,
   a parser typically has a "a bare `Date:`/`Sent:` line reopens a new
   message once we're far enough past the current message's own `From:`"
   fallback (for when the scan eats a `From:` line entirely), gated on
   `distance > MAX_HEADER_LINES + slack`. If both reuse the same constant,
   raising it for point 1 silently makes the reopen fallback *also* far less
   sensitive — a short, ordinary message (a few lines long) no longer
   crosses the new, larger threshold before the *next* message's stamp line
   arrives, so that next message never reopens and is swallowed whole into
   the short one instead. This is not a hypothetical: it is exactly what
   happened fixing point 1 for one release — the very next message, which
   happened to have no `From:` line at all (see point 5), vanished entirely
   as a result. Keep two named constants (`MAX_HEADER_LINES` for the cap,
   something like `REOPEN_MIN_DISTANCE` for the boundary check, deliberately
   left at its original, smaller value) even though one was "obviously"
   derived from the other when the code was first written.

5. **A message can have no `From:` line at all — not OCR-eaten, never
   printed.** Distinguish this from the usual case (a scan that swallowed
   the line with page furniture): here the header genuinely opens
   `Message` / `Sent: <date>` / `To: ...` with nothing before `Sent:`. The
   same reopen-on-`Date:`/`Sent:` fallback (point 4) handles it once its
   distance threshold is sane; what it *can't* fix is sender attribution --
   `fields.get("From")` is simply absent, so sender resolution falls through
   to whatever signature-block recovery the parser has, and a casual
   one-word sign-off ("Regards, Mike") is usually too thin for that to find
   a roster match. Leaving the sender blank rather than guessing from a
   bare first name is correct, not a bug to chase further: the content is
   fully recovered and readable, which is what matters.

## 6. Embedded attachments printed straight into the release

A covering email with "Please find attached..." followed immediately, in the
same PDF print, by the attached document's own text (a Word doc with
track-changes comments is especially common in these releases) will — unless
you specifically guard against it — read as if it were the email author's
own prose. Two independent signals, used together:

- **A sign-off phrase** ends the author's own text — but make the phrase
  list tolerant of the OCR's own misspellings, not just the canonical form
  (`"Kind regards"` as literally printed can OCR to `"Kinds regards"`; widen
  to `Kinds?\s+regards`, and do this kind of tolerance check for every
  sign-off phrase, not just one). Cut everything from the first matched
  sign-off onward.
- **A document-review marker is a near-zero-false-positive signal that an
  attached document's text has started**, independent of whether the
  sign-off above was recognised. Word's own review comments —
  `Commented [A1]:`, `Commented [A4R4]:` — never occur in ordinary email
  prose:
  ```python
  RE_WORD_COMMENT_MARKER = re.compile(r"Commented\s*\[A\d+")
  def strip_embedded_attachment(body_lines):
      for i, line in enumerate(body_lines):
          if RE_WORD_COMMENT_MARKER.search(line):
              return body_lines[:i] + ["== ATTACHMENT: document with reviewer "
                                        "comments (not transcribed) =="]
      return body_lines
  ```
  Mark elided content explicitly rather than silently vanishing it — a
  reader needs to know something was dropped and why, not just get a
  shorter message than the source document actually contains.

## 7. Process: how to actually find and verify these bugs

1. **When OCR/extracted output looks wrong, go to the raw per-page text
   first**, not the cleaned JSON output. Split on the page-break character
   (`\x0c` for a `pdftoppm`+`tesseract` concatenation; page-by-page
   `extract_text()` for pypdf) and print the specific page(s) involved,
   unmodified by any of your own cleanup functions. Guessing at the fix from
   the already-cleaned output wastes time and usually gets the root cause
   wrong.
2. **Size the problem across the whole corpus before and after a fix** —
   `grep -c` the specific artifact (a regex for the OCR pattern, a check for
   a leaked field name at the top of a body, a specific glyph) over the raw
   text or the generated JSON. Confirms both that a fix is worth making and,
   after, that it actually worked (ideally to zero remaining).
3. **When a classifier/heuristic fails on one specific input, trace it
   function-by-function** against that exact input (a small script
   `import`ing the parser module and calling its internal functions
   directly on the problem lines) rather than guessing which of several
   candidate gatekeeper functions is the culprit — these parsers tend to
   layer several independent shape tests, and the failing one is rarely the
   one you'd guess first.
4. **Entry/sender/count deltas after a fix should be explicable.** A
   segmentation fix can legitimately change the total entry count (fixing a
   false split, or recovering a previously-swallowed stranded message) — but
   check the direction and size make sense, and spot-check a few affected
   entries by hand rather than trusting the count alone.
5. **Keep both the raw (`sender_raw`, `stamp`) and the cleaned/canonical
   value side by side in the entry schema.** Every fix here is "best effort"
   against genuinely degraded source material — showing the evidence next to
   the conclusion is what lets a reader (or your future self) trust or
   override it, rather than silently rewriting history.
6. **When a project has more than one release parsed by near-identical
   parsers (copy-pasted lineage, same function names), a bug found in one is
   a reason to check the others, not just fix the one in front of you.** Two
   unrelated-looking symptoms — a different release's citation pointing at a
   missing entry, a different release's email running to 18,000 characters —
   turned out to be the *exact same two bugs* (header-length cap, attachment
   bleed) independently present in a second parser that had simply never
   been exercised hard enough to surface them yet. Porting the fix is
   usually mechanical once it's understood once; grep the other parser for
   the same constant names and call sites before assuming it's fine.
